from django.contrib import admin

from apps.books.models import Book, BookAnalysis, BookMetadata


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ["id", "gutenberg_id", "added_at", "modified_at"]


@admin.register(BookMetadata)
class BookMetadataAdmin(admin.ModelAdmin):
    list_display = ["id", "title", "language", "issued_date"]


@admin.register(BookAnalysis)
class BookAnalysisAdmin(admin.ModelAdmin):
    list_display = ["id", "book"]
