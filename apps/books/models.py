from django.contrib.auth import get_user_model
from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.search import SearchVector, SearchVectorField, SearchQuery, SearchRank
from django.contrib.postgres.indexes import GinIndex
from pgvector.django import HnswIndex
from django.db import models
from pgvector.django import VectorField, CosineDistance


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

class BookChunk(models.Model):
    book = models.ForeignKey(
        "books.Book", on_delete=models.CASCADE, related_name="chunks"
    )
    content = models.TextField()
    summary = models.TextField(null=True)
    chunk_index = models.IntegerField()
    search_vector = models.GeneratedField(
        db_persist=True,
        expression=SearchVector("content", config="english"),
        output_field=SearchVectorField(),
    )
    embedding = VectorField(dimensions=1536)
    token_count = models.IntegerField()
    
    added_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["book", "chunk_index"],
                name="unique_book_chunk_index",
            )
        ]

        indexes = [
            GinIndex(fields=["search_vector"], name="search_vector_gin_index"),
            HnswIndex(
                fields=["embedding"],
                opclasses=["vector_cosine_ops"],
                name="embedding_hnsw_index",
            ),
            models.Index(fields=["book", "chunk_index"], name="book_chunk_index_index"),
        ]

    @classmethod
    def search(
        cls,
        query: str,
        dmax: float = 0.35,
        semantic_limit: int = 50,
        fts_limit: int = 50,
        rrf_k: int = 60,
    ):
        from collections import defaultdict
        from django.db.models import Case, When
        from apps.books.utils import encode_text
        from apps.books.utils import extract_meaningful_query_terms

        # Semantic search
        encoded_query = encode_text(query)
        semantic_distance = CosineDistance("embedding", encoded_query)
        semantic_results = cls.objects.alias(semantic_distance=semantic_distance)\
            .filter(semantic_distance__lte=dmax)\
            .order_by("semantic_distance")\
            .values_list("id", flat=True)[:semantic_limit]

        # FTS search
        query_terms = extract_meaningful_query_terms(query)
        fts_query = None
        for term in query_terms:
            q = SearchQuery(term, search_type="plain", config="english")
            if fts_query is None:
                fts_query = q
            else:
                fts_query = fts_query | q

        fts_results = cls.objects.filter(search_vector=fts_query)\
            .annotate(fts_rank=SearchRank("search_vector", fts_query, normalization=32))\
            .filter(fts_rank__gt=0)\
            .order_by("-fts_rank")\
            .values_list("id", flat=True)[:fts_limit]

        # RRF (Reciprocal Rank Fusion)
        rrf_scores = defaultdict(float)
        for ranking in [semantic_results, fts_results]:
            for rank, record_id in enumerate(ranking, start=1):
                rrf_scores[record_id] += 1.0 / (rrf_k + rank)

        sorted_records = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
        fused_ids = [record_id for record_id, _score in sorted_records]

        if not fused_ids:
            return cls.objects.none()

        preserved_order = Case(*[When(pk=pk, then=pos) for pos, pk in enumerate(fused_ids)])
        return cls.objects.filter(pk__in=fused_ids).select_related(
            "book", "book__metadata"
        ).order_by(preserved_order)

class BookConversation(models.Model):
    user = models.ForeignKey(User, on_delete=models.PROTECT)
    book = models.ForeignKey(Book, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "created_at"]),
        ]
    
    def __str__(self):
        return f"Conversation #{self.id}"

class BookConversationMessage(models.Model):
    class Role(models.TextChoices):
        USER = "user"
        ASSISTANT = "assistant"

    conversation = models.ForeignKey(BookConversation, on_delete=models.CASCADE, related_name="messages")
    role = models.CharField(max_length=25, choices=Role.choices)
    content = models.TextField()
    chunks = models.ManyToManyField(BookChunk, related_name="messages")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["conversation", "created_at"]),
        ]