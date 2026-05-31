from datetime import date
from apps.books.models import BookConversationMessage
from pydantic import AwareDatetime
from ninja import Schema


class BookContentOutSchema(Schema):
    content: str


class BookMetadataOutSchema(Schema):
    title: str
    issued_date: date
    language: str
    authors: list[str]
    subjects: list[str]
    locc: str
    bookshelves: list[str]


class BookAnalysisOutSchema(Schema):
    status: str
    summary: str
    key_characters: list[dict]
    sentiment_and_emotion: str
    themes: list[str]
    topics: list[str]
    character_relationships: list[str]
    notable_quotes: list[str]


class InProgressBookAnalysisOutSchema(Schema):
    status: str


class BookSearchHistoryOutSchema(Schema):
    title: str
    gutenberg_id: int
    author: str
    searched_at: AwareDatetime


class BookSearchQueryOutSchema(Schema):
    chunk_id: int
    content: str
    gutenberg_id: int
    book_id: int
    book_title: str

    @staticmethod
    def resolve_chunk_id(obj):
        return obj.id

    @staticmethod
    def resolve_gutenberg_id(obj):
        return obj.book.gutenberg_id

    @staticmethod
    def resolve_book_id(obj):
        return obj.book.id

    @staticmethod
    def resolve_book_title(obj):
        return obj.book.metadata.title


class BookConversationInSchema(Schema):
    conversation_id: int | None = None
    gutenberg_id: int
    query: str


class BookConversationOutSchema(Schema):
    conversation_id: int
    message_id: int
    content: str
    role: BookConversationMessage.Role
    chunks: list[int]

    @staticmethod
    def resolve_conversation_id(obj):
        return obj.conversation.id

    @staticmethod
    def resolve_message_id(obj):
        return obj.id

    @staticmethod
    def resolve_chunks(obj):
        return [chunk.id for chunk in obj.chunks.all()]