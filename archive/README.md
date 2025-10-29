# Archive Directory

This directory contains legacy files, old scripts, and deprecated implementations that are no longer actively used in the project.

## Directory Structure

- **legacy_files/** - Old data files and source materials that have been replaced by the current pipeline
  - `Markdown Source Files/` - Original markdown source files (now processed through the pipeline from XML)
  - `markdown_source_files_rag/` - Duplicate markdown files from rag_implementations
  - `theological_chunks.jsonl` - Old chunk format (replaced by pipeline stages)
  - `theological_chunks_with_embeddings.jsonl` - Old chunks with embeddings (replaced by `04_complete/` stage)

- **old_scripts/** - Deprecated scripts replaced by the current pipeline system
  - `add_embeddings.py` - Old embedding script (now in `pipeline_manager.py` stage 4)
  - `markdown_to_jsonl.py` - Old conversion script (replaced by pipeline chunking)
  - `remove_structure_path.py` - Temporary fix script (no longer needed)

- **old_rag_implementations/** - Previous RAG implementations that have been superseded
  - `current_html_rag/` - Early HTML-based RAG tester
  - `llamagraph_rag/` - LlamaGraph-based implementation (not in active use)

## Current Active System

The project now uses:
- **Pipeline**: `pipeline_manager.py` with staged processing (`theological_processing/`)
- **RAG App**: `rag_implementations/ai_research_assistant/` (Flask app loading from `05_deployed/`)

## Note

Files in this archive are preserved for reference but are not used by the current system. They can be safely deleted if disk space is needed, but keeping them provides historical context.

