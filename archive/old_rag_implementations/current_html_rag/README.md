# Current HTML RAG Tester

This is the preserved version of the HTML-based RAG tester that was built and refined.

## Features
- Pure vector search vs Enhanced metadata search comparison
- Comprehensive filtering system (Topics, Concepts, Themes, Function, Scripture References, Proper Nouns, Structure Path, Author)
- Real OpenAI embeddings integration
- Minimal, professional UI design
- Pre-search filtering capabilities
- Auto-loading dataset with localStorage persistence

## Files
- `rag_tester.html` - Main RAG tester interface
- `theological_chunks.jsonl` - Original parsed chunks
- `theological_chunks_with_embeddings.jsonl` - Chunks with OpenAI embeddings

## Usage
1. Open `rag_tester.html` in a browser
2. Click "Load Default Dataset" to load the theological chunks
3. Use filters to narrow down results
4. Enter queries or search with filters only
5. Compare pure vector vs enhanced search results

## Technical Details
- Uses OpenAI text-embedding-3-small model
- Cosine similarity for vector search
- Metadata boosting for enhanced search
- Comprehensive filter system with autocomplete
- Minimal gray-based color palette
