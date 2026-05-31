from django.conf import settings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from google import genai
from google.genai import types

from apps.books.tasks import embed_book_chunks_task

text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
    model_name=settings.CHUNKING_MODEL,
    chunk_size=600,
    chunk_overlap=60
)

def chunk_book_content(content: str, book_id: int):
    chunks = text_splitter.split_text(content)
    embed_book_chunks_task.delay(chunks, 0, book_id, False)
    return chunks


def encode_text(text: str) -> list[float] | None:
    try:
        genai_client = genai.Client(api_key=settings.GEMINI_API_KEY)
        result = genai_client.models.embed_content(
            model=settings.GEMINI_EMBEDDING_MODEL,
            contents=text,
            config=types.EmbedContentConfig(output_dimensionality=1536)
        )
        return result.embeddings[0].values
    except Exception as e:
        print(f"Error encoding text: {e}")
        return None


def extract_meaningful_query_terms(query: str) -> list[str]:
    import re

    STOPWORDS = {
        "and", "or", "the", "a", "an", "of", "to", "in", "on", "for", "with", "is", "are"
    }
    terms = [term for term in re.findall(r'\w+', query.lower()) if term not in STOPWORDS]

    if not terms: # Fallback if no meaningful terms are found (e.g. query="the or and are the")
        terms = re.findall(r'\w+', query.lower())
    
    return terms


METADATA_FIELD_PAGE_TITLES = {
    "authors": {
        "page_titles": ["Author", "Creator", "Compiler", "Illustrator"],
        "value": [],
    },
    "title": {"page_titles": ["Title"], "value": ""},
    "language": {"page_titles": ["Language"], "value": ""},
    "locc": {"page_titles": ["LoC Class"], "value": ""},
    "subjects": {"page_titles": ["Subject"], "value": []},
    "issued_date": {"page_titles": ["Release Date"], "value": ""},
}

TEXT_ANALYSIS_PROMPT_TEMPLATE = """
### Task
Given the following book excerpt, perform a detailed text analysis and provide structured insights in the following format:
1. Summary: A concise yet informative summary of the chunk.
2. Key Characters & Roles: Identify the main characters in this section and their significance.
3. Themes & Topics: Detect recurring themes or important topics.
4. Sentiment & Emotion Analysis: Analyze the emotional tone and sentiments conveyed.
5. Important Quotes: Extract any impactful or meaningful quotes from the section.
6. Writing Style & Complexity: Assess sentence structure, readability, and language sophistication.
7. Character Relationships: Analyze how characters interact in this excerpt.

### Output Format
Provide a JSON response structured as follows:
{
    "summary": "...",
    "characters": [
        {"name": "...", "role": "..."},
        {"name": "...", "role": "..."},
        ...
    ],
    "themes": ["theme1", "theme2", ...],
    "topics": ["topic1", "topic2", ...],
    "sentiment_and_emition": "...",
    "important_quotes": ["quote1", "quote2", ...],
    "character_relationships": ["relation_ship1", "relation_ship2", ...]
}

### Book excerpt
{{ content }}

### Response Requirements
- A single JSON object
- No extra words, markdown, or characters before or after the JSON
- 7 Keys: "summary", "characters", "themes", "topics", "sentiment_and_emition", "important_quotes", and "character_relationships"
- Must be valid, parseable JSON

### Guidelines
1. Preserve the original meaning and key details.
2. Maintain the original tone and style, whether formal or informal.
3. Retain specialized terms and proper names.
4. Ensure the response is under 32000 characters.
5. The response must be valid JSON, with no extra words, formatting, or text before or after the JSON. Every object property and array item must be separated by a comma where required by JSON syntax. Do not omit commas between properties. The response must parse successfully with json.loads(). Property names MUST use double quotes. Strings MUST use double quotes. No single quotes. No unquoted keys.
6. Do NOT add "json" or any text before the JSON output. The response must start and end with {} directly.
7. If the content is insufficient for any section, return an empty string "" or an empty array [] instead of omitting keys.
"""

FINAL_ANALYSIS_PROMPT_TEMPLATE = """
### Task
Your task is to generate a comprehensive final book analysis based on multiple section analyses. You will be given JSON responses containing summaries and insights from different parts of the book.

Your job is to:
1. Merge all provided section summaries into a single, coherent final summary.
2. Identify recurring and key characters across all sections and describe their significance.
3. Extract the most prominent themes and topics based on all analyses.
4. Analyze the overall sentiment and emotional tone of the book.
5. Extract the most impactful and representative quotes from the book.
6. Describe key character relationships, ensuring they remain consistent and meaningful.

### Input Format
You will receive an array of multiple JSON objects in the following structure:
[
    {
        "summary": "...",
        "characters": [
            {"name": "...", "role": "..."},
            {"name": "...", "role": "..."}
        ],
        "themes": ["theme1", "theme2"],
        "topics": ["topic1", "topic2"],
        "sentiment_and_emotion": "...",
        "important_quotes": ["quote1", "quote2"],
        "character_relationships": ["relationship1", "relationship2"]
    },
    ...
]

### Output Format
Provide a single JSON object structured as follows:
{
    "final_summary": "...",
    "key_characters": [
        {"name": "...", "role": "..."},
        {"name": "...", "role": "..."}
    ],
    "main_themes": ["theme1", "theme2"],
    "main_topics": ["topic1", "topic2"],
    "overall_sentiment_and_emotion": "...",
    "notable_quotes": ["quote1", "quote2"],
    "character_relationships": ["relationship1", "relationship2"]
}

### Input Data
{{ chunk_analyses_data }}

### Response Requirements
- Must return a single, valid JSON object.
_ Array values must be separated by a comma.
- No extra text, formatting, or explanations before/after the JSON.
- All keys must be present (if data is missing, return an empty string `""` or an empty array `[]`).
- Ensure the JSON is parseable and contains exactly 7 keys: "final_summary", "key_characters", "main_themes", "main_topics", "overall_sentiment_and_emotion", "notable_quotes", "character_relationships"

### Guidelines
1. Final Summary
   - Combine all section summaries into one well-structured summary that retains key details but removes redundancy.
   - Ensure smooth transitions and logical flow of events.
2. Key Characters & Roles
   - Identify all major characters from the provided sections.
   - Remove duplicates and merge similar character mentions.
   - Ensure character descriptions are accurate and consistent.
3. Themes & Topics
   - Extract recurring themes and topics from all section analyses.
   - Sort by importance, keeping only the most relevant ones.
4. Sentiment & Emotion Analysis
   - Identify the overall tone of the book (e.g., optimistic, tragic, suspenseful).
   - Consider shifts in emotion throughout the story.
5. Notable Quotes
   - Select the most powerful and meaningful quotes across all sections.
   - Ensure they represent the core ideas or style of the book.
6. Character Relationships
   - Merge character relationships from different sections into a cohesive relationship.
   - Each relationship should be a string describing the relationship between the characters.
   - The relationships should not be a list of strings of json objects.
   - Ensure relationships make sense within the full story context.
7. Ensure the response is under 32000 characters.
8. The response must be valid JSON, with no extra words, formatting, or text before or after the JSON. Every object property and array item must be separated by a comma where required by JSON syntax. Do not omit commas between properties. The response must parse successfully with json.loads(). Property names MUST use double quotes. Strings MUST use double quotes. No single quotes. No unquoted keys.
9. Do NOT add "json" or any text before the JSON output. The response must start and end with {} directly.
"""

CLASSIFICATION_LLM_PROMPT = """
### Task
Classify the user query into one of two categories:
- "narrow": The question can likely be answered using a small number of localized chunks.
- "broad": The question requires understanding large parts of the document, multiple sections, global themes, summaries, comparisons, or synthesis.

### Rules
- Return ONLY one word:
  - broad
  - narrow
- Do not explain.
- Do not output anything else.

### Examples
Query: "Who killed the king?"
Answer: narrow

Query: "Summarize the book"
Answer: broad

Query: "What is the hero's intent?"
Answer: narrow

Query: "Describe the evolution of the main character"
Answer: broad

Query: "What are the main themes of the book?"
Answer: broad

Query: "What happened in chapter 3?"
Answer: narrow

Now classify this query:
{{ user_query }}
"""

ASK_LLM_PROMPT_TEMPLATE = """
### Task
Your task is to answer the user's question ONLY using the provided book chunks or summaries.

Do not invent facts.
Do not use external knowledge.
If the answer cannot be determined from the provided content, return:
{
  "answer": ""
}

### INPUT FORMAT

{
  "question": "...",
  "content": [
    "...",
    "...",
    ...
  ],
  "chunks_or_summaries": "chunks | summaries"
}

- "chunks":
  Raw retrieved text chunks from the book.
- "summaries":
  Higher-level summaries of sections/chapters/books.

### INSTRUCTIONS
1. Use ONLY the provided content.
2. Do NOT hallucinate or infer unsupported facts.
3. If multiple content items are relevant, synthesize them into a coherent answer.
4. If the content contains conflicting information, prioritize:
   - the most repeated information
   - the most explicit statement
5. Keep the answer concise and directly relevant to the question.
6. The answer MUST be written in the same language as the question.
7. Maximum response length: 32000 characters.
8. Never mention:
   - "based on the provided content"
   - "the chunks say"
   - "the summaries mention"
9. Do not quote excessively unless necessary.
10. If "chunks_or_summaries" == "summaries":
    - produce a higher-level synthesized answer
    - avoid low-level details unless clearly important
11. If "chunks_or_summaries" == "chunks":
    - prefer precise factual answers
    - preserve important details

### OUTPUT REQUIREMENTS
You MUST return EXACTLY one valid JSON object.

Required format:
{
  "answer": "..."
}

Rules:
- Output ONLY JSON.
- Do NOT wrap in markdown.
- Do NOT add explanations.
- Do NOT add comments.
- Do NOT add trailing commas.
- The JSON must parse successfully with json.loads().
- The JSON object must contain exactly 1 key: "answer"

### INPUT DATA

{{ input_data }}
"""