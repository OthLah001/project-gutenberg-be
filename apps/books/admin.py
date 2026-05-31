from django.contrib import admin

from apps.books.models import Book, BookAnalysis, BookConversation, BookConversationMessage, BookMetadata, BookSearchHistory


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ["id", "gutenberg_id", "added_at", "modified_at"]


@admin.register(BookMetadata)
class BookMetadataAdmin(admin.ModelAdmin):
    list_display = ["id", "title", "language", "issued_date"]


@admin.register(BookAnalysis)
class BookAnalysisAdmin(admin.ModelAdmin):
    list_display = ["id", "book", "analyse_status"]


@admin.register(BookSearchHistory)
class BookSearchHistoryAdmin(admin.ModelAdmin):
    list_display = ["id", "book", "user", "searched_at"]


@admin.register(BookConversation)
class BookConversationAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "book", "created_at", "updated_at"]


@admin.register(BookConversationMessage)
class BookConversationMessageAdmin(admin.ModelAdmin):
    list_display = ["id", "conversation", "role", "content", "created_at", "updated_at"]