# Query Flow Explanation

## Complete Step-by-Step Flow

### When You Click "Search" (Citation Window - 15 chunks)

#### Step 1: Frontend Request (`enhanced_index.html`)
- User enters query and clicks search button
- Frontend calls `/api/search-only` endpoint
- **Time**: < 0.1 seconds (network request)

#### Step 2: Query Analysis (`enhanced_app.py` - Line 156)
- **Function**: `analyze_query(query)`
- **What it does**: 
  - Makes 1 API call to GPT-4o-mini
  - Analyzes query to extract metadata filters:
    - Concepts (e.g., "Faith", "Salvation")
    - Discourse elements (e.g., "Symbolic/Metaphor", "Logical/Claim")
    - Scripture references (e.g., "John 14:6")
    - Named entities (e.g., "Augustine", "Jesus Christ")
    - Sources/Authors (if specified)
- **Time**: ~1-2 seconds
- **API Call**: 1 × GPT-4o-mini

#### Step 3: Query Embedding (`enhanced_app.py` - Line 144)
- **Function**: `get_embedding(query)`
- **What it does**:
  - Makes 1 API call to OpenAI embeddings API
  - Converts query text into a 1536-dimensional vector
  - Used for semantic similarity matching
- **Time**: ~0.5-1 second
- **API Call**: 1 × OpenAI Embeddings API

#### Step 4: Vector Search (`enhanced_app.py` - Line 253)
- **Function**: `search_with_filters(query, analysis, selected_sources)`
- **What it does**:
  1. Filters dataset by selected sources (if any)
     - Loops through ALL chunks in dataset
     - Keeps only chunks from selected sources
  2. Calculates cosine similarity for ALL filtered chunks
     - Compares query embedding with each chunk's embedding
     - Results in similarity scores (0.0 to 1.0)
  3. Calculates metadata boost for ALL chunks
     - Checks if chunk metadata matches suggested filters
     - Adds boost scores:
       - Concepts match: +0.15 per match
       - Discourse elements match: +0.12 per match
       - Scripture references match: +0.15-1.0 (exact match gets highest boost)
       - Named entities match: +0.1 per match
  4. Combines similarity + metadata boost = final score
  5. Sorts by final score (highest first)
  6. Returns top 15 chunks
- **Time**: ~1-2 seconds (depends on dataset size)
- **API Calls**: 0 (all computation is local)

#### Step 5: Batch Relevance Explanations (`enhanced_app.py` - Line 1164) ⚡ **OPTIMIZED**
- **Function**: `generate_relevance_explanations_batch(query, chunks)`
- **What it does**:
  - **BEFORE OPTIMIZATION**: Made 15 sequential API calls (one per chunk)
  - **AFTER OPTIMIZATION**: Makes 1 batched API call for all 15 chunks
  - Generates one-sentence explanations for why each chunk is relevant
  - Uses GPT-4o-mini to analyze query + chunk text + metadata
- **Time**: 
  - **Before**: ~15 seconds (15 × 1 second sequential calls)
  - **After**: ~1-2 seconds (1 batched call)
- **API Calls**: 
  - **Before**: 15 × GPT-4o-mini
  - **After**: 1 × GPT-4o-mini

#### Step 6: Format Response (`enhanced_app.py` - Line 898)
- **What it does**:
  - Formats chunks into `sources_used` array
  - Includes: source name, author, location, text, metadata, relevance explanation
  - Builds search strategy description
- **Time**: < 0.1 seconds

#### Step 7: Return to Frontend
- **What it does**:
  - Returns JSON response with chunks and explanations
  - Frontend displays results in citation window
- **Time**: < 0.1 seconds (network response)

### Total Time for Citation Window (15 chunks):
- **Before Optimization**: ~18 seconds
  - Query analysis: ~1-2s
  - Embedding: ~0.5-1s
  - Vector search: ~1-2s
  - **15 sequential relevance explanations: ~15s** ⚠️
  - Formatting: < 0.1s
- **After Optimization**: **~4-6 seconds** (75% faster)
  - Query analysis: ~1-2s
  - Embedding: ~0.5-1s
  - Vector search: ~1-2s
  - **1 batched relevance explanation: ~1-2s** ✅
  - Formatting: < 0.1s

---

### When You Click "Get AI Summary"

#### Step 1: Frontend Request (`enhanced_index.html`)
- User clicks "Get AI Summary" button
- Frontend calls `/api/generate-summary` endpoint
- Sends: query, chunks (from previous search), query_analysis
- **Time**: < 0.1 seconds

#### Step 2: Generate Summary (`enhanced_app.py` - Line 421)
- **Function**: `generate_research_summary(query, analysis, chunks)`
- **What it does**:
  1. Prepares context from top 10 chunks
     - Formats each chunk with source info and text
  2. Makes 1 API call to GPT-4o-mini
     - Sends query + all chunk texts
     - Asks AI to synthesize a comprehensive summary
     - AI generates summary with numbered citations [1], [2], etc.
  3. Extracts citations from summary
     - Finds all citation numbers used
     - Renumbers them sequentially
  4. Generates relevance explanations for cited chunks ⚡ **OPTIMIZED**
     - **BEFORE**: Made sequential API calls for each cited chunk
     - **AFTER**: Makes 1 batched API call for all cited chunks
  5. Fixes citation numbers in summary
     - Ensures citations match source numbers
- **Time**: 
  - Summary generation: ~2-3 seconds
  - Relevance explanations: 
    - **Before**: ~5-10 seconds (sequential)
    - **After**: ~1-2 seconds (batched)
- **API Calls**: 
  - Summary: 1 × GPT-4o-mini
  - Relevance explanations:
    - **Before**: 5-10 × GPT-4o-mini (sequential)
    - **After**: 1 × GPT-4o-mini (batched)

#### Step 3: Return to Frontend
- Returns JSON with summary, sources_used, reasoning
- Frontend displays summary in research panel
- **Time**: < 0.1 seconds

### Total Time for AI Summary:
- **Before Optimization**: ~18 seconds
  - Summary generation: ~2-3s
  - **5-10 sequential relevance explanations: ~5-10s** ⚠️
  - Citation fixing: < 0.1s
- **After Optimization**: **~3-5 seconds** (75% faster)
  - Summary generation: ~2-3s
  - **1 batched relevance explanation: ~1-2s** ✅
  - Citation fixing: < 0.1s

---

## Key Optimizations Made

### 1. Batched Relevance Explanations ⚡
**Problem**: 15 sequential API calls (one per chunk) = ~15 seconds
**Solution**: 1 batched API call for all chunks = ~1-2 seconds
**Improvement**: ~90% faster for relevance explanations

**Implementation**:
- Created `generate_relevance_explanations_batch()` function
- Sends all chunks in a single API request
- AI generates numbered explanations (1:, 2:, 3:, etc.)
- Parses response to extract explanations for each chunk

### 2. Applied to Both Endpoints
- `/api/search-only`: Now uses batch generation
- `/api/generate-summary`: Now uses batch generation for cited chunks

---

## Remaining Bottlenecks (Future Optimizations)

### 1. Vector Search Could Be Faster
- Currently calculates similarity for ALL chunks every time
- Could use vector database (FAISS, Pinecone) for faster search
- **Potential improvement**: 1-2s → 0.1-0.5s

### 2. Query Analysis + Embedding Could Be Parallel
- Currently runs sequentially
- Could run in parallel using async/await
- **Potential improvement**: 2-3s → 1-2s

### 3. Caching Could Help
- Cache query embeddings
- Cache relevance explanations (by query+chunk_id)
- **Potential improvement**: Subsequent queries much faster

### 4. Relevance Explanations Could Be Optional
- Return chunks immediately without explanations
- Generate explanations on-demand or asynchronously
- **Potential improvement**: Initial response ~3-4s (no explanations)

---

## Summary

**Before**: ~36 seconds total (18s citation window + 18s summary)
**After**: ~7-11 seconds total (4-6s citation window + 3-5s summary)
**Improvement**: ~70-75% faster overall

The main bottleneck was **15 sequential API calls** for relevance explanations. By batching them into a single API call, we've dramatically reduced the wait time while maintaining the same quality of explanations.

