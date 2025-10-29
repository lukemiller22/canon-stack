# Theological Processing Pipeline Directory

This directory contains the staged processing pipeline for theological texts.

## Directory Structure

- **01_sources/** - Raw uploaded files (XML, PDF, DOCX, etc.)
- **02_chunked/** - Text chunks only (NO METADATA) ← HUMAN REVIEW REQUIRED
- **03_annotated/** - Chunks + metadata (NO VECTORS) ← HUMAN REVIEW REQUIRED  
- **04_complete/** - Chunks + metadata + vectors
- **05_deployed/** - Production-ready files
- **metadata/** - Source metadata (YAML files)
- **logs/** - Processing logs
- **templates/** - Custom processing templates for different source types
- **rejected/** - Files that failed processing

## Usage

```bash
# Check pipeline status
python pipeline_manager.py --stage status

# Process a source file
python pipeline_manager.py --stage chunk --source filename.xml

# Review and approve chunks
touch 02_chunked/FILENAME_chunks.jsonl.approved

# Generate annotations
python pipeline_manager.py --stage annotate --source FILENAME_chunks.jsonl

# Review and approve annotations
touch 03_annotated/FILENAME_annotated.jsonl.approved

# Generate vectors
python pipeline_manager.py --stage vectorize --source FILENAME_annotated.jsonl
```

## Human Review Process

1. **Chunk Review**: Check chunks in `02_chunked/` for quality and structure
2. **Annotation Review**: Verify metadata accuracy in `03_annotated/`
3. **Approval**: Create `.approved` files to proceed to next stage

See `Theological Text Processing Pipeline.md` for detailed documentation.
