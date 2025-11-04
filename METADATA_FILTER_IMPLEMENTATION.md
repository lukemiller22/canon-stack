# Metadata Filter Implementation Guide

## Overview
The RAG system uses a **hybrid search approach** that combines:
1. **Exact phrase matching** (weight: 2.0)
2. **Vector similarity** (weight: 1.5) 
3. **Metadata filters** (weight: 0.5)

## Code Location

All metadata filter code is in: `rag_implementations/ai_research_assistant/app.py`

### Key Functions:

1. **`analyze_query()`** - Lines 84-200
   - Analyzes the user query using AI
   - Returns `recommended_filters` dictionary
   - Location: Lines 84-200

2. **`search_with_filters()`** - Lines 202-361
   - Main search function that applies filters
   - Location: Lines 202-361

## How It Works

### Step 1: Query Analysis (Lines 84-200)

The `analyze_query()` function uses GPT-4o-mini to analyze queries and extract metadata filters:

```python
def analyze_query(query: str) -> Dict[str, Any]:
    # Sends a prompt to GPT-4o-mini asking it to:
    # 1. Identify query type (doctrinal, exegetical, etc.)
    # 2. Extract theological concepts
    # 3. Determine search strategy
    # 4. Generate recommended_filters dictionary
    # 5. Provide reasoning
    
    # Returns:
    # {
    #   "query_type": "exegetical",
    #   "theological_concepts": ["Jesus Christ", "Scripture"],
    #   "search_strategy": "...",
    #   "recommended_filters": {
    #     "authors": ["St. Augustine", "Augustine"],
    #     "scripture_references": ["John 14:6"],
    #     "topics": [...],
    #     "concepts": [...]
    #   },
    #   "reasoning": "..."
    # }
```

**Example for "What passages from Augustine's Confessions talk about John 14:6?":**
The AI should return:
```json
{
  "recommended_filters": {
    "authors": ["St. Augustine", "Augustine"],
    "scripture_references": ["John 14:6"],
    "topics": ["Jesus Christ/Mediator", "Incarnation/Word Made Flesh"],
    "concepts": ["Jesus Christ", "Scripture"]
  }
}
```

### Step 2: Filter Application (Lines 202-361)

The `search_with_filters()` function applies filters to each chunk:

#### Filter Score Calculation (Lines 236-343)

For each chunk, the system calculates a `filter_match_score`:

1. **Author Filter** (Lines 252-258)
   ```python
   if filter_type == 'authors':
       chunk_author = chunk.get("author", "")
       for filter_val in filter_values:
           if filter_val.lower() in chunk_author.lower():
               filter_match_score += 1
   ```

2. **Scripture References Filter** (Lines 295-327)
   ```python
   elif metadata_field == 'scripture_references':
       # Normalizes both filter and chunk values
       # Exact match preferred
       # Also matches chapter-level (e.g., "John 14" matches "John 14:6")
   ```

3. **Discourse Elements Filter** (Lines 266-294)
   - Uses `discourse_tags` if available (faster)
   - Falls back to parsing `discourse_elements` strings

4. **Other Metadata Filters** (Lines 328-340)
   - Topics, concepts, terms, named_entities, structure_path
   - Uses substring matching

#### Combined Score (Lines 345-355)

```python
combined_score = (exact_match_score * 2.0) + 
                 (vector_similarity_score * 1.5) + 
                 (filter_match_score * 0.5)
```

**Important:** Filter matches only contribute 0.5 to the score, so chunks with high vector similarity can still rank higher than chunks with perfect filter matches but lower vector similarity.

### Step 3: Ranking (Lines 357-361)

Chunks are sorted by `combined_score` in descending order, and the top 15 are returned.

## Current Implementation Details

### Scripture Reference Matching Logic (Lines 295-327)

The scripture reference matching works as follows:

1. **Normalization**: Removes extra spaces
   ```python
   filter_normalized = re.sub(r'\s+', ' ', filter_val.lower().strip())
   chunk_normalized = re.sub(r'\s+', ' ', str(chunk_val).lower().strip())
   ```

2. **Exact Match** (Line 307-310)
   ```python
   if filter_normalized == chunk_normalized:
       filter_match_score += 1  # Perfect match
   ```

3. **Verse Matching** (Lines 311-318)
   - If filter is a verse (has `:`), matches chunks with same chapter
   - Example: Filter "John 14:6" matches chunk "John 14" or "John 14:5-7"

4. **Chapter Matching** (Lines 319-325)
   - If filter is a chapter (no `:`), matches any verse in that chapter
   - Example: Filter "John 14" matches chunk "John 14:6"

### Filter Weight Issue

**Potential Problem:** The `filter_match_score` is weighted at only **0.5**, which means:
- A chunk with perfect filter match (score = 1) gets 0.5 points
- A chunk with vector similarity 0.4 gets 0.6 points (0.4 * 1.5)
- A chunk with both filter match (1) + vector similarity (0.4) gets 1.1 points (0.5 + 0.6)

This means chunks with high vector similarity but no filter match can still outrank chunks with perfect filter matches but lower vector similarity.

## Debugging Steps

To debug why a chunk isn't being retrieved:

1. **Check if query analysis is detecting scripture references:**
   - Look at the `query_analysis` in the response
   - Verify `recommended_filters` contains `scripture_references: ["John 14:6"]`

2. **Check filter matching logic:**
   - The chunk has `"scripture_references": ["John 14:6"]`
   - The filter should match exactly: `"John 14:6".lower().strip() == "John 14:6".lower().strip()`

3. **Check the combined score:**
   - Look at `filter_score`, `vector_score`, and `exact_match_score` in results
   - Chunk might match filters but rank low due to vector similarity

4. **Check if chunk is in top 15:**
   - Only top 15 chunks are returned (line 360)
   - Even if a chunk matches filters, it might be excluded if 15 other chunks scored higher

## Recommendations

1. **Increase filter weight** (if filters are important):
   ```python
   combined_score = (exact_match_score * 2.0) + 
                    (vector_similarity_score * 1.5) + 
                    (filter_match_score * 1.0)  # Increase from 0.5
   ```

2. **Add mandatory filter matching:**
   - Only include chunks that match at least one filter if filters are specified
   - Currently, chunks are included if `combined_score > 0.1` regardless of filter matches

3. **Debug logging:**
   - Add print statements to see what filters are being applied
   - Log filter_match_score for each chunk

