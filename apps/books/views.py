from django.utils import timezone
from ninja import NinjaAPI

from apps.books.models import (Book, BookAnalysis, BookMetadata,
                               BookSearchHistory)
from apps.books.schemas import (BookAnalysisOutSchema, BookContentOutSchema,
                                BookMetadataOutSchema,
                                BookSearchHistoryOutSchema)
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

        books_qs.update(content=content)

    book = books_qs.first()

    return {"content": book.content}


@books_api.get("{gutenberg_id}/metadata/", response=BookMetadataOutSchema)
def get_book_content(request, gutenberg_id: int):
    from django.db import transaction

    from apps.books.services import scrap_metadata

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

    history, created = BookSearchHistory.objects.get_or_create(
        book=book, user=request.user
    )
    if not created:
        history.searched_at = timezone.now()
        history.save()

    return {
        "title": metadata.title,
        "issued_date": metadata.issued_date,
        "language": metadata.language,
        "authors": metadata.authors,
        "subjects": metadata.subjects,
        "locc": metadata.locc,
        "bookshelves": metadata.bookshelves,
    }


@books_api.get("{gutenberg_id}/analysis/", response=BookAnalysisOutSchema)
def get_book_content(request, gutenberg_id: int):
    pass

    from apps.books.services import analyse_book

    book_analysis_qs = BookAnalysis.objects.filter(book__gutenberg_id=gutenberg_id)
    if book_analysis_qs.count() == 0:
        analyse_book(gutenberg_id)

    book_analysis = book_analysis_qs.first()
    if book_analysis is None:
        raise NinjaError(
            error_name="invalid_gutenberg_id",
            message=f"Book with id {gutenberg_id} does not exist.",
            status_code=404,
        )

    return {
        "summary": book_analysis.summary,
        "key_characters": book_analysis.key_characters,
        "sentiment_and_emotion": book_analysis.sentiment_and_emotion,
        "themes": book_analysis.themes,
        "topics": book_analysis.topics,
        "character_relationships": book_analysis.character_relationships,
        "notable_quotes": book_analysis.notable_quotes,
    }


@books_api.get("history/", response=list[BookSearchHistoryOutSchema])
def get_book_content(request):
    history_qs = (
        BookSearchHistory.objects.filter(user=request.user)
        .select_related("book")
        .order_by("-searched_at")
    )

    return [
        {
            "title": h.book.metadata.title,
            "gutenberg_id": h.book.gutenberg_id,
            "searched_at": h.searched_at,
        }
        for h in history_qs
    ]
