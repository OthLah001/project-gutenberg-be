from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.contrib.auth import get_user_model


User = get_user_model()


class Book(models.Model):
    gutenberg_id = models.IntegerField(db_index=True, unique=True)
    content = models.TextField(null=True, blank=True)
    added_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)


class BookMetadata(models.Model):
    book = models.OneToOneField(
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
    book = models.OneToOneField(
        "books.Book", on_delete=models.PROTECT, related_name="analysis"
    )
    summary = models.TextField()
    key_characters = models.JSONField()
    themes = ArrayField(models.CharField(max_length=255))
    topics = ArrayField(models.CharField(max_length=255))
    sentiment_and_emotion = models.TextField()
    notable_quotes = ArrayField(models.CharField(max_length=255))
    character_relationships = ArrayField(models.CharField(max_length=255))


class BookSearchHistory(models.Model):
    book = models.ForeignKey(
        "books.Book", on_delete=models.PROTECT, related_name="search_history"
    )
    user = models.ForeignKey(User, on_delete=models.PROTECT)
    searched_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["book", "searched_at"]),
            models.Index(fields=["user", "searched_at"]),
        ]
        unique_together = [["book", "user"]]
