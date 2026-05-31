from celery import shared_task
from google import genai
from google.genai import types
from google.genai.errors import ClientError
from django.conf import settings

from config.celery import app


genai_client = genai.Client(api_key=settings.GEMINI_API_KEY)


@shared_task
def analyse_book_task(gutenberg_id):
    # Import models or other dependencies inside the function to avoid circular imports
    import asyncio
    from apps.books.services import analyse_book

    analyse_book(gutenberg_id)


@shared_task
def embed_book_chunks_task(chunks: list[str], chunk_index: int, book_id: int, is_genai_exhausted: bool):
    import tiktoken
    import redis

    from apps.books.models import BookChunk

    instances = []
    encoder = tiktoken.encoding_for_model(settings.CHUNKING_MODEL)
    r = redis.Redis()

    try:
        for chunk in chunks:
            # Embed the chunk
            result = genai_client.models.embed_content(
                model=settings.GEMINI_EMBEDDING_MODEL,
                contents=chunk,
                config=types.EmbedContentConfig(output_dimensionality=1536)
            )

            # Get encoded summary from redis queue & Create a BookChunk instance
            _, b_summary = r.blpop(f"book_{book_id}_chunk_{chunk_index}")
            instances.append(
                BookChunk(
                    book_id=book_id,
                    content=chunk,
                    summary=b_summary.decode("utf-8"),
                    chunk_index=chunk_index,
                    embedding=result.embeddings[0].values,
                    token_count=len(encoder.encode(chunk))
                )
            )
            chunk_index += 1

    except ClientError as e:
        if e.code == 409:
            # If we hit the RPD Limit, call the task again with the remaining chunks
            embed_book_chunks_task.apply_async(
                args=[chunks[chunk_index:], chunk_index, book_id, True],
                countdown=86400 if (len(chunks)==0 and is_genai_exhausted) else 60 # 1 day if we hit the RPD Limit, 1 minute otherwise
            )
    finally:
        # Create the BookChunk instances
        if len(instances) > 0:
            BookChunk.objects.bulk_create(instances)