def create_book_instance(gutenberg_id):
    from apps.books.models import Book

    book = Book.objects.create(gutenberg_id=gutenberg_id)
    return book


def fetch_book_content(gutenberg_id, is_retry=False):
    import requests

    url = f"https://www.gutenberg.org/files/{gutenberg_id}/{gutenberg_id}.txt"
    if is_retry:
        url = url.replace(".txt", "-0.txt")

    response = requests.get(url)

    if response.status_code == 200:
        return response.text
    elif is_retry is False:
        return fetch_book_content(gutenberg_id, is_retry=True)

    return None


def fetch_book_metadata(gutenberg_id):
    import requests

    url = f"https://www.gutenberg.org/ebooks/{gutenberg_id}"

    response = requests.get(url)

    if response.status_code == 200:
        return response.text

    return None


def analyse_book(gutenberg_id):
    import json

    from django.conf import settings
    from django.template import Context, Template
    from groq import Groq

    from apps.books.models import Book, BookAnalysis
    from apps.books.utils import (FINAL_ANALYSIS_PROMPT_TEMPLATE,
                                  TEXT_ANALYSIS_PROMPT_TEMPLATE,
                                  split_text_evenly)

    # Get book content
    book_content = fetch_book_content(gutenberg_id)
    if book_content is None:
        return None

    # Split book content into chunks
    book_chunks = split_text_evenly(book_content)
    groq = Groq(api_key=settings.GROQ_API_KEY)
    chunk_analyses_data = []

    for chunk in book_chunks:
        # Render the user prompt and get data for each chunk
        user_prompt = Template(TEXT_ANALYSIS_PROMPT_TEMPLATE).render(
            Context({"content": chunk})
        )

        response = groq.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are an expert text analyst"},
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
            model=settings.GROQ_LLM_MODEL,
            stop=None,
            stream=False,
        )
        chunk_analyses_data.append(response.choices[0].message.content)

    # Merge the chunks into one result
    final_user_prompt = Template(FINAL_ANALYSIS_PROMPT_TEMPLATE).render(
        Context({"chunk_analyses_data": chunk_analyses_data})
    )

    response = groq.chat.completions.create(
        messages=[
            {"role": "system", "content": "You are an expert text analyst"},
            {
                "role": "user",
                "content": final_user_prompt,
            },
        ],
        model=settings.GROQ_LLM_MODEL,
        stop=None,
        stream=False,
    )

    analysis = json.loads(response.choices[0].message.content)
    book = Book.objects.get(gutenberg_id=gutenberg_id)

    book_analysis = BookAnalysis.objects.create(
        book=book,
        summary=analysis["final_summary"],
        key_characters=analysis["key_characters"],
        themes=analysis["main_themes"],
        topics=analysis["main_topics"],
        sentiment_and_emotion=analysis["overall_sentiment_and_emotion"],
        notable_quotes=analysis["notable_quotes"],
        character_relationships=analysis["character_relationships"],
    )
    return book_analysis


def scrap_metadata(gutenberg_id):
    from datetime import datetime

    from lxml import html

    from apps.books.models import Book, BookMetadata
    from apps.books.utils import METADATA_FIELD_PAGE_TITLES

    metadata_content = fetch_book_metadata(gutenberg_id)
    if metadata_content is None:
        return None

    # Convert html plain text to html
    html_content = html.fromstring(metadata_content)
    book, created = Book.objects.get_or_create(gutenberg_id=gutenberg_id)
    book_metadata = BookMetadata(book=book)

    for field, data in METADATA_FIELD_PAGE_TITLES.items():
        th_texts = [
            f"text()='{title}'" for title in data["page_titles"]
        ]  # Prepare the th tags value condition
        th_xpath = f"/html/body/div[1]/div[1]/div[2]/div[4]/div/div[3]/div/table/tr/th[{' or '.join(th_texts)}]"  # Select th tags in the table of metadata

        th_elements = html_content.xpath(th_xpath)
        if isinstance(data["value"], list):  # It has multiple values
            for element in th_elements:
                value = (
                    element.xpath("./parent::tr/td[1]")[0].text_content().strip()
                )  # Get the value of td tag
                data["value"].append(value)
        elif len(th_elements) > 0:  # It has only one value
            value = (
                th_elements[0].xpath("./parent::tr/td[1]")[0].text_content().strip()
            )  # Get the value of td tag
            data["value"] = (
                value
                if field != "issued_date"
                else datetime.strptime(value, "%b %d, %Y").date()
            )

        setattr(book_metadata, field, data["value"])  # Update the model instance

    book_metadata.save()
    return book_metadata


def fetch_gutenberg_catalog():
    import csv
    import io
    from datetime import datetime

    import requests
    from langcodes import Language

    from apps.books.models import Book, BookMetadata

    def split_list_field(field_value):
        if not field_value:
            return []

        # Split by semicolon and strip whitespace
        return [item.strip() for item in field_value.split(";") if item.strip()]

    url = "https://www.gutenberg.org/cache/epub/feeds/pg_catalog.csv"

    try:
        # Download the CSV file
        response = requests.get(url)
        response.raise_for_status()

        # Parse the CSV content
        csv_content = io.StringIO(response.text)
        reader = csv.DictReader(csv_content)

        # Process the data and create Book and BookMetadata instances
        for row in reader:
            # Skip rows without a Gutenberg ID
            gutenberg_id = int(row.get("Text#", 0))
            if gutenberg_id == 0:
                continue

            # Create or get the Book and BookMetadata instances
            book, created = Book.objects.get_or_create(gutenberg_id=gutenberg_id)
            book_metadata = BookMetadata.objects.filter(book=book).first()

            # Skip if the metadata is already filled by the script
            if book_metadata is None:
                book_metadata = BookMetadata(book=book)
            elif book_metadata.filled_by_script:
                continue

            # Fill the metadata fields
            book_metadata.title = row.get("Title", "")
            book_metadata.language = Language.make(
                language=row.get("Language", "")
            ).display_name()
            book_metadata.locc = row.get("LoCC", "")
            book_metadata.authors = split_list_field(row.get("Authors", ""))
            book_metadata.subjects = split_list_field(row.get("Subjects", ""))
            book_metadata.issued_date = datetime.strptime(
                row.get("Issued", ""), "%Y-%m-%d"
            ).date()
            book_metadata.bookshelves = split_list_field(row.get("Bookshelves", ""))
            book_metadata.filled_by_script = True
            book_metadata.save()

    except requests.exceptions.RequestException as e:
        print(f"Error fetching catalog: {e}")
