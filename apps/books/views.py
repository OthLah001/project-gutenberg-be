from django.utils import timezone
from ninja import NinjaAPI
from ninja.pagination import paginate, PageNumberPagination

from apps.books.models import Book, BookAnalysis, BookMetadata, BookSearchHistory
from apps.books.schemas import (
    BookAnalysisOutSchema,
    BookContentOutSchema,
    BookMetadataOutSchema,
    BookSearchHistoryOutSchema,
    InProgressBookAnalysisOutSchema,
    BookSearchQueryOutSchema,
    BookConversationOutSchema,
    BookConversationInSchema,
)
from config.ninja_utils.authentication import auth_bearer
from config.ninja_utils.errors import NinjaError

books_api = NinjaAPI(auth=auth_bearer, urls_namespace="books")


# Set custom exception handler
@books_api.exception_handler(NinjaError)
def handle_elham_error(request, exc: NinjaError):
    return books_api.create_response(
        request,
        {"error_name": exc.error_name, "message": exc.message},
        status=exc.status_code,
    )


@books_api.get("{gutenberg_id}/content/", response=BookContentOutSchema)
def get_book_content(request, gutenberg_id: int):
    from apps.books.services import fetch_book_content

    books_qs = Book.objects.filter(gutenberg_id=gutenberg_id)
    if (count := books_qs.count()) == 0 or not books_qs.first().content:
        content = fetch_book_content(gutenberg_id)

        if content is None:
            raise NinjaError(
                error_name="invalid_gutenberg_id",
                message=f"Book with id {gutenberg_id} does not exist.",
                status_code=404,
            )
    book = books_qs.first()

    return {
        "content": book.content,
        "embedding_status": book.embedding_status
    }


@books_api.get("{gutenberg_id}/metadata/", response=BookMetadataOutSchema)
def get_book_metadata(request, gutenberg_id: int):
    from django.db import transaction

    from apps.books.services import scrap_metadata

    # Get metadata from db or scrapping
    book, created = Book.objects.get_or_create(gutenberg_id=gutenberg_id)
    metadata_qs = BookMetadata.objects.filter(book=book)
    if metadata_qs.count() == 0:
        transaction.on_commit(lambda: scrap_metadata(gutenberg_id))

    metadata = metadata_qs.first()
    if metadata is None:
        raise NinjaError(
            error_name="invalid_gutenberg_id",
            message=f"Book with id {gutenberg_id} does not exist.",
            status_code=404,
        )

    # Save search history
    history, created = BookSearchHistory.objects.get_or_create(
        book=book, user=request.user
    )
    if not created:
        history.searched_at = timezone.now()
        history.save()

    # Analyse book in background
    book_analysis, created = BookAnalysis.objects.get_or_create(book=book)
    if created or book_analysis.analyse_status == BookAnalysis.AnalyseChoice.FAILED:
        from apps.books.tasks import analyse_book_task

        book_analysis.analyse_status = BookAnalysis.AnalyseChoice.PENDING
        book_analysis.save()

        analyse_book_task.delay(gutenberg_id)

    return {
        "title": metadata.title,
        "issued_date": metadata.issued_date,
        "language": metadata.language,
        "authors": metadata.authors,
        "subjects": metadata.subjects,
        "locc": metadata.locc,
        "bookshelves": metadata.bookshelves,
    }


@books_api.get(
    "{gutenberg_id}/analysis/",
    response=BookAnalysisOutSchema | InProgressBookAnalysisOutSchema,
)
def analyse_book(request, gutenberg_id: int):
    book_analysis = BookAnalysis.objects.get(book__gutenberg_id=gutenberg_id)
    if book_analysis.analyse_status in (
        BookAnalysis.AnalyseChoice.PENDING,
        BookAnalysis.AnalyseChoice.IN_PROGRESS,
    ):
        return {"status": BookAnalysis.AnalyseChoice.IN_PROGRESS}

    if book_analysis.analyse_status == BookAnalysis.AnalyseChoice.FAILED:
        raise NinjaError(
            error_name="analyse_failed",
            message=f"Book with id {gutenberg_id} analysis failed.",
            status_code=500,
        )

    return {
        "status": BookAnalysis.AnalyseChoice.COMPLETED,
        "summary": book_analysis.summary,
        "key_characters": book_analysis.key_characters,
        "sentiment_and_emotion": book_analysis.sentiment_and_emotion,
        "themes": book_analysis.themes,
        "topics": book_analysis.topics,
        "character_relationships": book_analysis.character_relationships,
        "notable_quotes": book_analysis.notable_quotes,
    }


@books_api.get("history/", response=list[BookSearchHistoryOutSchema])
def get_books_searching_history(request):
    history_qs = (
        BookSearchHistory.objects.filter(user=request.user)
        .select_related("book")
        .order_by("-searched_at")
    )

    return [
        {
            "title": h.book.metadata.title,
            "gutenberg_id": h.book.gutenberg_id,
            "author": h.book.metadata.authors[0] if h.book.metadata.authors else "Unknown",
            "searched_at": h.searched_at,
        }
        for h in history_qs
    ]

@books_api.get("search/", response=list[BookSearchQueryOutSchema])
@paginate(PageNumberPagination, page_size=5)
def search_books(request, query: str):
    from apps.books.models import BookChunk
    
    return BookChunk.search(query)

@books_api.post("ask/", response=BookConversationOutSchema)
def ask_book(request, data: BookConversationInSchema):
    from apps.books.models import BookConversation, BookConversationMessage, BookChunk
    from apps.books.services import ask_llm, classify_user_query

    # Check if book has been chunked or not yet
    book = Book.objects.get(gutenberg_id=data.gutenberg_id)
    if book.chunks.count() == 0:
        raise NinjaError(
            error_name="book_not_chunked",
            message=f"Book with id {data.book_id} has not been chunked yet. Try later.",
            status_code=400,
        )

    # Create conversation & message
    conversation_id = data.conversation_id
    if not conversation_id:
        conversation = BookConversation.objects.create(user=request.user, book=book)
        conversation_id = conversation.id

    user_message = BookConversationMessage.objects.create(conversation_id=conversation_id, role=BookConversationMessage.Role.USER, content=data.query)

    # Check if query is broad or narrow & get the right content for each one
    is_query_broad = classify_user_query(data.query) == "broad"
    relevant_chunks =  BookChunk.objects.filter(book_id=book.id) if is_query_broad else BookChunk.search(data.query)
    user_message.chunks.set(relevant_chunks)

    # Ask the LLM to answer the question
    answer = ask_llm(data.query, [(chunk.summary if is_query_broad else chunk.content) for chunk in relevant_chunks], is_query_broad)
    assistant_message = BookConversationMessage.objects.create(conversation_id=conversation_id, role=BookConversationMessage.Role.ASSISTANT, content=answer)

    # Return conversation
    return assistant_message

