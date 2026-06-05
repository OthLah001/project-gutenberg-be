def create_book_instance(gutenberg_id):
    # Create a book instance in the database
    from apps.books.models import Book

    book = Book.objects.create(gutenberg_id=gutenberg_id)
    return book


def fetch_book_content(gutenberg_id):
    '''
    Fetch the book content from the Gutenberg project.
    If the book content is not found, return None
    If the book content is found, update the book instance in the database and return the content.
    '''
    import requests
    from apps.books.models import Book

    url_variations = [
        f"https://www.gutenberg.org/files/{gutenberg_id}/{gutenberg_id}.txt",
        f"https://www.gutenberg.org/files/{gutenberg_id}/{gutenberg_id}-0.txt",
    ]

    for url in url_variations:
        try:
            response = requests.get(url)
            response.raise_for_status()  # Raises an HTTPError for bad responses
            Book.objects.filter(gutenberg_id=gutenberg_id).update(content=response.text)

            return response.text
        except Exception as e:
            pass

    return None


def fetch_book_metadata(gutenberg_id):
    '''
    Fetch the book metadata from the Gutenberg project.
    If the book metadata is not found, return None
    If the book metadata is found, return the metadata
    '''
    import requests

    url = f"https://www.gutenberg.org/ebooks/{gutenberg_id}"

    response = requests.get(url)

    if response.status_code == 200:
        return response.text

    return None


def analyse_book(gutenberg_id):
    '''
    Analyze the book content using Groq API.
    If the book content couldn't be fetched or an error occurred, return None.
    If not, we split the content of the book into chunks, then we analyze each chunk, so at the end
    we get the final analyze.
    '''
    import json

    from django.conf import settings
    from django.template import Context, Template
    from groq import Groq
    import redis

    from apps.books.models import BookAnalysis
    from apps.books.utils import (
        FINAL_ANALYSIS_PROMPT_TEMPLATE,
        TEXT_ANALYSIS_PROMPT_TEMPLATE,
        chunk_book_content,
    )

    # Get book and book analysis instance
    book_analysis = BookAnalysis.objects.get(book__gutenberg_id=gutenberg_id)
    book = book_analysis.book

    # Get book content
    book_content = book.content or fetch_book_content(gutenberg_id)
    if book_content is None:
        book_analysis.analyse_status = BookAnalysis.AnalyseChoice.FAILED
        book_analysis.save()

        return None

    # Update book analysis status
    book_analysis.analyse_status = BookAnalysis.AnalyseChoice.IN_PROGRESS
    book_analysis.save()

    # Split book content into chunks & analyze each chunk
    book_chunks = chunk_book_content(book_content, book.id)
    groq = Groq(api_key=settings.GROQ_API_KEY)
    r = redis.from_url(settings.REDIS_URL)
    chunk_analyses_data = []

    for index, chunk in enumerate(book_chunks):
        # Render the user prompt and get data for each chunk
        user_prompt = Template(TEXT_ANALYSIS_PROMPT_TEMPLATE).render(
            Context({"content": chunk})
        )

        # The LLM returns invalid json even the instructions are correct
        # For that reason, I repeat the LLM call until I get a valid json
        # IMPROVEMENT: set a max_retry = 5 to not overwhelm the LLM
        while True:
            try:
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

                # Push the summary to redis queue
                summary = json.loads(response.choices[0].message.content)["summary"]
                r.rpush(f"book_{book.id}_chunk_{index}", summary)
                break
            except json.decoder.JSONDecodeError:
                continue

    # Merge the chunks into one result
    final_user_prompt = Template(FINAL_ANALYSIS_PROMPT_TEMPLATE).render(
        Context({"chunk_analyses_data": chunk_analyses_data})
    )

    # The LLM returns invalid json even the instructions are correct
    # For that reason, I repeat the LLM call until I get a valid json
    # IMPROVEMENT: set a max_retry = 5 to not overwhelm the LLM
    analysis = None
    while True:
        try:
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
            break
        except json.decoder.JSONDecodeError:
            continue

    book_analysis.analyse_status = BookAnalysis.AnalyseChoice.COMPLETED
    book_analysis.summary = analysis["final_summary"]
    book_analysis.key_characters = analysis["key_characters"]
    book_analysis.themes = analysis["main_themes"]
    book_analysis.topics = analysis["main_topics"]
    book_analysis.sentiment_and_emotion = analysis["overall_sentiment_and_emotion"]
    book_analysis.notable_quotes = analysis["notable_quotes"]
    book_analysis.character_relationships = analysis["character_relationships"]
    book_analysis.save()

    return book_analysis


def scrap_metadata(gutenberg_id):
    '''
    Scrap the book metadata.
    '''
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


def classify_user_query(query: str):
    from django.conf import settings
    from groq import Groq
    from django.template import Template, Context

    from apps.books.utils import CLASSIFICATION_LLM_PROMPT

    groq = Groq(api_key=settings.GROQ_API_KEY)
    classification_prompt = Template(CLASSIFICATION_LLM_PROMPT).render(
        Context({"user_query": query})
    )
    response = groq.chat.completions.create(
        messages=[
            {"role": "system", "content": "You are a query classifier for a RAG system."},
            {"role": "user", "content": classification_prompt},
        ],
        model=settings.GROQ_LLM_MODEL,
        stop=None,
        stream=False,
    )
    print("=> broad/narrow? ", response.choices[0].message.content)
    return response.choices[0].message.content


def rewrite_followup_query(query: str, conversation_history: list[dict[str, str]]):
    import json
    from django.conf import settings
    from groq import Groq
    from django.template import Template, Context
    from apps.books.utils import REWRITE_FOLLOWUP_QUERY_PROMPT

    input_data = {
        "query": query,
        "conversation_history": conversation_history,
    }
    prompt = Template(REWRITE_FOLLOWUP_QUERY_PROMPT).render(Context({"input_data": input_data}))

    groq = Groq(api_key=settings.GROQ_API_KEY)
    response = groq.chat.completions.create(
        messages=[
            {"role": "system", "content": "You rewrite conversational questions for retrieval systems."},
            {"role": "user", "content": prompt},
        ],
        model=settings.GROQ_LLM_MODEL,
        stop=None,
        stream=False,
    )

    response_content = response.choices[0].message.content or ""
    try:
        rewritten_query = json.loads(response_content).get("standalone_query", "")
    except json.decoder.JSONDecodeError:
        rewritten_query = response_content

    return (rewritten_query or query).strip()


def ask_llm(query, content: list[str], is_query_broad: bool, conversation_history: list[dict[str, str]] | None = None):
    from django.conf import settings
    from groq import Groq
    import json
    from django.template import Template, Context

    from apps.books.utils import ASK_LLM_PROMPT_TEMPLATE

    groq = Groq(api_key=settings.GROQ_API_KEY)
    user_prompt = Template(ASK_LLM_PROMPT_TEMPLATE).render(
        Context({"input_data": {
            "question": query,
            "content": content,
            "chunks_or_summaries": "summaries" if is_query_broad else "chunks",
            "conversation_history": conversation_history or [],
        }})
    )
    response = groq.chat.completions.create(
        messages=[
            {"role": "system", "content": "You are a high-precision RAG answer generator."},
            {"role": "user", "content": user_prompt},
        ],
        model=settings.GROQ_LLM_MODEL,
        stop=None,
        stream=False,
    )
    response_content = response.choices[0].message.content or ""
    try:
        answer = json.loads(response_content).get("answer", "")
    except json.decoder.JSONDecodeError:
        answer = response_content

    return answer or "I couldn't generate an answer right now. Please try again."