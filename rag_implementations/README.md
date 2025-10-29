# RAG Implementations

This directory contains different implementations of the RAG (Retrieval Augmented Generation) system for theological text analysis.

## Implementations

### 1. Current HTML RAG (`current_html_rag/`)
- **Status**: ✅ Complete and preserved
- **Type**: HTML/JavaScript frontend with OpenAI embeddings
- **Features**: Vector search, metadata filtering, comparison interface
- **Use Case**: Quick testing, comparison, and reference implementation

### 2. LlamaGraph RAG (`llamagraph_rag/`)
- **Status**: 🚧 In Development
- **Type**: LlamaGraph-based advanced RAG system
- **Features**: Graph-based knowledge representation, multi-hop reasoning
- **Use Case**: Production-ready advanced RAG capabilities

## Quick Start

### Current HTML RAG
```bash
cd current_html_rag
python3 -m http.server 8000
open http://localhost:8000/rag_tester.html
```

### LlamaGraph RAG
```bash
cd llamagraph_rag
# Setup instructions coming soon
```

## Migration Notes
- The current HTML implementation is fully preserved and functional
- LlamaGraph implementation will build upon the same theological dataset
- Both implementations can be used simultaneously for comparison
