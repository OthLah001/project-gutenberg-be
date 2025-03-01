def split_text_evenly(text: str, max_length: int = 126000):
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    if not text:
        return []

    if len(text) <= max_length:
        return [text]

    # Calculate optimal chunk size
    total_length = len(text)
    nbre_chunks = (total_length + max_length - 1) // max_length
    optimal_chunk_size = total_length // nbre_chunks

    # Split the text
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=optimal_chunk_size)
    return text_splitter.split_text(text)


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

### Guidelines
1. Preserve the original meaning and key details.
2. Maintain the original tone and style, whether formal or informal.
3. Retain specialized terms and proper names.
4. Ensure the response is under 32000 characters.
5. The response must be valid JSON, with no extra words, formatting, or text before or after the JSON.
6. Do NOT add "json" or any text before the JSON output. The response must start and end with {} directly.
7. If the content is insufficient for any section, return an empty string "" or an empty array [] instead of omitting keys.

### Book excerpt
{{ content }}

### Response Requirements
- A single JSON object
- No extra words, markdown, or characters before or after the JSON
- 7 Keys: "summary", "characters", "themes", "topics", "sentiment_and_emition", "important_quotes", and "character_relationships"
- Must be valid, parseable JSON
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
   - Merge character relationships from different sections into a cohesive relationship map.
   - Ensure relationships make sense within the full story context.
7. Ensure the response is under 32000 characters.
8. The response must be valid JSON, with no extra words, formatting, or text before or after the JSON.
9. Do NOT add "json" or any text before the JSON output. The response must start and end with {} directly.

### Input Data
{{ chunk_analyses_data }}

### Response Requirements
- Must return a single, valid JSON object.
- No extra text, formatting, or explanations before/after the JSON.
- All keys must be present (if data is missing, return an empty string `""` or an empty array `[]`).
- Ensure the JSON is parseable and contains exactly 7 keys: "final_summary", "key_characters", "main_themes", "main_topics", "overall_sentiment_and_emotion", "notable_quotes", "character_relationships"
"""
