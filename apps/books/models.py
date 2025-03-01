from django.contrib.postgres.fields import ArrayField
from django.db import models


class Book(models.Model):
    gutenberg_id = models.IntegerField(db_index=True, unique=True)
    added_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)


class BookMetadata(models.Model):
    book = models.ForeignKey(
        "books.Book", on_delete=models.PROTECT, related_name="metadata"
    )
    title = models.CharField(max_length=500, db_index=True)
    issued_date = models.DateField()
    language = models.CharField(max_length=100, db_index=True)
    authors = ArrayField(models.CharField(max_length=255), default=[])
    subjects = ArrayField(models.CharField(max_length=255), default=[])
    locc = models.CharField(max_length=255)
    bookshelves = ArrayField(models.CharField(max_length=255), default=[])
    filled_by_script = models.BooleanField(default=False)


class BookAnalysis(models.Model):
    book = models.ForeignKey(
        "books.Book", on_delete=models.PROTECT, related_name="analysis"
    )
    summary = models.TextField()
    key_characters = models.JSONField()
    themes = ArrayField(models.CharField(max_length=255))
    topics = ArrayField(models.CharField(max_length=255))
    sentiment_and_emotion = models.TextField()
    notable_quotes = ArrayField(models.CharField(max_length=255))
    character_relationships = ArrayField(models.CharField(max_length=255))
