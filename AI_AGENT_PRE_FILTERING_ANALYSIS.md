# AI Agent Pre-Filtering Analysis

## Current State: NO Pre-Filtering by AI Agent

### What the AI Agent Does:
The AI agent (`analyze_query` / `analyze_query_async`) analyzes the query and returns:
- `suggested_filters` dictionary containing:
  - `concepts`: ["Faith", "Salvation", etc.]
  - `discourse_elements`: ["Symbolic/Metaphor", "Logical/Claim", etc.]
  - `scripture_references`: ["John 14:6", "Genesis 1", etc.]
  - `named_entities`: ["Augustine", "Jesus Christ", etc.]
  - `sources`: ["Mere Christianity", etc.] (if user asks for specific source)
  - `authors`: ["C.S. Lewis", etc.] (if user asks for specific author)

### Where AI Suggestions Are Used:

**❌ NOT Used for Pre-Filtering:**
- The `suggested_filters` are **NOT** used to filter chunks before vector search
- ChromaDB query only filters by `selected_sources` (user-selected sources from UI)
- The `where_clause` in ChromaDB query (line 435-444) only includes user-selected sources

**✅ Used for Post-Search Re-Ranking:**
- The `suggested_filters` are ONLY used in `calculate_metadata_boost()` (line 529)
- This happens AFTER vector search, during Stage 2 re-ranking
- Metadata boost increases scores but doesn't remove chunks

### Current Flow:

```
1. AI Agent analyzes query → returns suggested_filters
2. Query embedding generated
3. STAGE 1: ChromaDB vector search
   - Pre-filter: ONLY user-selected sources (if any)
   - Returns: Top 100 by similarity
   - AI suggestions: NOT USED HERE
4. STAGE 2: Re-ranking
   - Applies metadata boost based on suggested_filters
   - Returns: Top 15 after re-ranking
```

### What Gets Pre-Filtered:

**✅ User-Selected Sources:**
- If user selects specific sources in UI, chunks are filtered BEFORE vector search
- This is a HARD FILTER (removes chunks entirely)
- Implemented in ChromaDB `where_clause` (line 435-444)

**❌ AI-Suggested Filters:**
- Concepts, discourse elements, scripture references, named entities
- These are NOT used for pre-filtering
- Only used for post-search boost scoring

### Code Evidence:

**ChromaDB Query (Line 447-451):**
```python
where_clause = None
if selected_sources and len(selected_sources) > 0:
    # Only user-selected sources, NOT AI suggestions
    where_clause = {"source": {"$in": source_names}}

results = chroma_collection.query(
    query_embeddings=[query_embedding],
    n_results=100,
    where=where_clause  # Only source filtering, no metadata filtering
)
```

**Metadata Boost (Line 529+):**
```python
def calculate_metadata_boost(chunk, analysis):
    suggested = analysis.get('suggested_filters', {})
    # Uses suggested_filters to boost scores AFTER search
    # Does NOT filter chunks before search
```

## Answer: NO Pre-Filtering by AI Agent

The AI agent's suggested filters are **NOT** used to pre-filter chunks before vector search. They are only used for post-search re-ranking via metadata boost scoring.

The only pre-filtering that happens is:
- **User-selected sources** (hard filter before vector search)

All other AI suggestions (concepts, discourse, scripture, entities) are only used for boosting scores after vector search.

