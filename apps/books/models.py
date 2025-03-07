from django.contrib.auth import get_user_model
from django.contrib.postgres.fields import ArrayField
from django.db import models

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
    title = models.CharField(max_length=1024, db_index=True)
    issued_date = models.DateField()
    language = models.CharField(max_length=100, db_index=True)
    authors = ArrayField(models.CharField(max_length=255), default=[])
    subjects = ArrayField(models.CharField(max_length=255), default=[])
    locc = models.CharField(max_length=255)
    bookshelves = ArrayField(models.CharField(max_length=255), default=[])
    filled_by_script = models.BooleanField(default=False)


class BookAnalysis(models.Model):
    class AnalyseChoice(models.TextChoices):
        PENDING = "pending"
        IN_PROGRESS = "in_progress"
        COMPLETED = "completed"
        FAILED = "failed"

    book = models.OneToOneField(
        "books.Book", on_delete=models.PROTECT, related_name="analysis"
    )
    summary = models.TextField(null=True, blank=True)
    key_characters = models.JSONField(default=dict)
    themes = ArrayField(models.CharField(max_length=255), default=[])
    topics = ArrayField(models.CharField(max_length=255), default=[])
    sentiment_and_emotion = models.TextField(null=True, blank=True)
    notable_quotes = ArrayField(models.CharField(max_length=255), default=[])
    character_relationships = ArrayField(models.CharField(max_length=255), default=[])
    analyse_status = models.CharField(
        max_length=20, choices=AnalyseChoice.choices, default=AnalyseChoice.PENDING
    )


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
