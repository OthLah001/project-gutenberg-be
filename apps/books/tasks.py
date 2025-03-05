from celery import shared_task


@shared_task
def analyse_book_task(gutenberg_id):
    # Import models or other dependencies inside the function to avoid circular imports
    from apps.books.services import analyse_book

    book_analysis = analyse_book(gutenberg_id)

    return book_analysis.id
