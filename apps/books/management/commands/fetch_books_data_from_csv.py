import csv
import io
from datetime import datetime
from django.core.management import BaseCommand
from django.db import transaction
import requests
from langcodes import Language

from apps.books.models import Book, BookMetadata


class Command(BaseCommand):
    def handle(self, *args, **options):
        self.fetch_gutenberg_catalog()

    def split_list_field(self, field_value):
        if not field_value:
            return []

        # Split by semicolon and strip whitespace
        return [item.strip() for item in field_value.split(";") if item.strip()]

    def fetch_gutenberg_catalog(self):
        url = "https://www.gutenberg.org/cache/epub/feeds/pg_catalog.csv"

        try:
            # Download the CSV file
            print("Fetching catalog...")
            response = requests.get(url)
            response.raise_for_status()

            # Parse the CSV content
            print("Parsing catalog...")
            csv_content = io.StringIO(response.text)
            reader = csv.DictReader(csv_content)

            # Process the data and create Book and BookMetadata instances
            print("Processing...")
            for row in reader:
                # Skip rows without a Gutenberg ID
                gutenberg_id = int(row.get("Text#", 0))
                if gutenberg_id == 0:
                    continue

                try:
                    print(f"\t=> ID #{gutenberg_id} ... ", end="")
                    with transaction.atomic(durable=False, savepoint=True):
                        # Create or get the Book and BookMetadata instances
                        book, created = Book.objects.get_or_create(
                            gutenberg_id=gutenberg_id
                        )
                        book_metadata = BookMetadata.objects.filter(book=book).first()

                        # Skip if the metadata is already filled by the script
                        if book_metadata is None:
                            book_metadata = BookMetadata(book=book)
                        elif book_metadata.filled_by_script:
                            print("Skipped")
                            continue

                        # Fill the metadata fields
                        book_metadata.title = row.get("Title", "")
                        book_metadata.language = Language.make(
                            language=row.get("Language", "")
                        ).display_name()
                        book_metadata.locc = row.get("LoCC", "")
                        book_metadata.authors = self.split_list_field(
                            row.get("Authors", "")
                        )
                        book_metadata.subjects = self.split_list_field(
                            row.get("Subjects", "")
                        )
                        book_metadata.issued_date = datetime.strptime(
                            row.get("Issued", ""), "%Y-%m-%d"
                        ).date()
                        book_metadata.bookshelves = self.split_list_field(
                            row.get("Bookshelves", "")
                        )
                        book_metadata.filled_by_script = True
                        book_metadata.save()
                        print("Done")
                except Exception as e:
                    print(f"Error ({e})")

        except requests.exceptions.RequestException as e:
            print(f"Error fetching catalog: {e}")
