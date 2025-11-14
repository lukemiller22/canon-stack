# Query Performance Analysis

## Current Flow Breakdown

### Step 1: `/api/search-only` Endpoint (18 seconds for 15 chunks)

**What happens:**

1. **Query Analysis** (`analyze_query()` - Line 156)
   - Makes 1 API call to GPT-4o-mini
   - Analyzes query to extract metadata filters (concepts, discourse elements, scripture references, etc.)
   - **Time: ~1-2 seconds**

2. **Query Embedding** (`get_embedding()` - Line 144)
   - Makes 1 API call to OpenAI embeddings API
   - Generates vector embedding for the query
   - **Time: ~0.5-1 second**

3. **Vector Search** (`search_with_filters()` - Line 253)
   - Filters dataset by selected sources (if any) - O(n) where n = total chunks
   - Calculates cosine similarity for ALL chunks in filtered dataset
   - Calculates metadata boost for ALL chunks
   - Sorts by final score and returns top 15
   - **Time: ~1-2 seconds** (depends on dataset size)

4. **Relevance Explanations** (`generate_relevance_explanation()` - Line 1086)
   - **MAJOR BOTTLENECK**: Called 15 times sequentially (once per chunk)
   - Each call makes a separate API call to GPT-4o-mini
   - **Time: ~15 × 1 second = 15 seconds** (sequential API calls)

**Total for `/api/search-only`: ~18 seconds**

### Step 2: `/api/generate-summary` Endpoint (18 seconds for summary)

**What happens:**

1. **Summary Generation** (`generate_research_summary()` - Line 421)
   - Makes 1 API call to GPT-4o-mini
   - Generates comprehensive research summary from top 10 chunks
   - **Time: ~2-3 seconds** (should be faster, but might be slow due to context size)

2. **Relevance Explanations** (Line 505)
   - Called again for each cited chunk in the summary
   - **Time: Variable, but potentially another 5-10 seconds**

**Total for `/api/generate-summary`: ~18 seconds**

## Identified Bottlenecks

### Critical Issues:

1. **Sequential API Calls for Relevance Explanations** ⚠️ **MAJOR BOTTLENECK**
   - 15 sequential API calls in `search_only` endpoint
   - Each call waits for the previous one to complete
   - Should be batched or made optional/async

2. **Redundant Relevance Explanations**
   - Generated in `search_only` endpoint
   - Generated again in `generate_summary` endpoint
   - Could be cached or generated only once

3. **No Caching**
   - Query embeddings recalculated every time
   - Relevance explanations recalculated even for same query/chunk pairs

4. **Inefficient Vector Search**
   - Calculates similarity for ALL chunks every time
   - No indexing or pre-filtering optimization

### Moderate Issues:

5. **Large Context in Summary Generation**
   - Sends full chunk text for top 10 chunks
   - Could be optimized with better chunking or summarization

## Optimization Strategies

### ✅ Priority 1: Batch Relevance Explanations (IMPLEMENTED)
- **Status**: ✅ Completed
- **Change**: Created `generate_relevance_explanations_batch()` function
- **Implementation**: Instead of 15 sequential API calls, now makes 1 batched API call
- **Expected improvement: 15 seconds → 2-3 seconds**
- **Files modified**: `enhanced_app.py`
  - Added `generate_relevance_explanations_batch()` function (Line 1164)
  - Updated `/api/search-only` endpoint to use batch generation (Line 895)
  - Updated `generate_research_summary()` to use batch generation (Line 505)

### Priority 2: Make Relevance Explanations Optional/Async
- Return chunks immediately without relevance explanations
- Generate explanations asynchronously or on-demand
- **Expected improvement: 18 seconds → 3-4 seconds**
- **Status**: Not implemented (can be added as future enhancement)

### Priority 3: Cache Relevance Explanations
- Cache explanations by query+chunk_id
- Only regenerate if query changes significantly
- **Expected improvement: Subsequent queries much faster**
- **Status**: Not implemented (can be added as future enhancement)

### Priority 4: Optimize Vector Search
- Pre-compute and cache embeddings
- Use vector database (e.g., FAISS, Pinecone) for faster similarity search
- **Expected improvement: 1-2 seconds → 0.1-0.5 seconds**
- **Status**: Not implemented (requires more significant refactoring)

### Priority 5: Parallelize API Calls
- Run query analysis and embedding generation in parallel
- Use async/await for concurrent API calls
- **Expected improvement: 2-3 seconds → 1-2 seconds**
- **Status**: Not implemented (can be added as future enhancement)

## Performance Improvements Summary

### Before Optimization:
- `/api/search-only`: ~18 seconds
  - Query analysis: ~1-2s
  - Embedding: ~0.5-1s
  - Vector search: ~1-2s
  - **15 sequential relevance explanations: ~15s** ⚠️

- `/api/generate-summary`: ~18 seconds
  - Summary generation: ~2-3s
  - Relevance explanations: ~5-10s (sequential)

### After Optimization:
- `/api/search-only`: **Expected ~4-6 seconds** (75% faster)
  - Query analysis: ~1-2s
  - Embedding: ~0.5-1s
  - Vector search: ~1-2s
  - **1 batched relevance explanation: ~1-2s** ✅

- `/api/generate-summary`: **Expected ~3-5 seconds** (75% faster)
  - Summary generation: ~2-3s
  - **1 batched relevance explanation: ~1-2s** ✅

### Total Expected Improvement:
- **Before**: ~36 seconds total (18s + 18s)
- **After**: ~7-11 seconds total (4-6s + 3-5s)
- **Improvement**: ~70-75% faster overall

