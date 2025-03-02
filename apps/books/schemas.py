from datetime import date
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
    summary: str
    key_characters: list[dict]
    sentiment_and_emotion: str
    themes: list[str]
    topics: list[str]
    character_relationships: list[str]
    notable_quotes: list[str]


class BookSearchHistoryOutSchema(Schema):
    title: str
    gutenberg_id: int
    searched_at: AwareDatetime
