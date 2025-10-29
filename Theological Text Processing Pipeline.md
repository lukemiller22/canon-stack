# Staged Theological Text Processing Pipeline

A cost-efficient, quality-controlled pipeline for processing theological texts with human review checkpoints.

## Folder Structure

```
theological_processing/
├── 01_sources/              # Raw uploaded files (XML, PDF, DOCX)
├── 02_chunked/             # Text chunks only (NO METADATA) ← HUMAN REVIEW
├── 03_annotated/           # Chunks + metadata (NO VECTORS) ← HUMAN REVIEW  
├── 04_complete/            # Chunks + metadata + vectors
├── 05_deployed/            # Production-ready files
├── metadata/               # Source metadata (YAML files)
├── logs/                   # Processing logs
├── templates/              # Custom processing templates
└── rejected/               # Failed processing attempts
```

## Processing Stages

### Stage 1: Sources → Chunked
**Input**: Raw files (XML, PDF, DOCX, etc.)  
**Output**: Basic JSONL with chunks only  
**Cost**: Minimal (no AI calls)  
**Human Review**: ✅ **REQUIRED** - Verify chunk quality before proceeding

```bash
# Process source file
python pipeline_manager.py --stage chunk --source orthodoxy.xml

# Review generated chunks in 02_chunked/
# When satisfied with chunking:
touch 02_chunked/ORTHODOXY_CHEST_chunks.jsonl.approved
```

**Sample Chunked Output**:
```json
{
  "id": "ORTHODOXY_CHEST_0",
  "text": "THIS book is meant to be a companion to \"Heretics,\" and to put...",
  "source": "Orthodoxy", 
  "author": "Gilbert K. Chesterton",
  "structure_path": ["Preface"],
  "chunk_index": 0,
  "processing_stage": "chunked"
}
```

### Stage 2: Chunked → Annotated  
**Input**: Approved chunks  
**Output**: Chunks + theological metadata  
**Cost**: High (AI annotation) or Medium (manual template)  
**Human Review**: ✅ **REQUIRED** - Verify metadata quality

```bash
# Option A: AI annotation (costs tokens)
python pipeline_manager.py --stage annotate --source ORTHODOXY_CHEST_chunks.jsonl --annotation-method ai

# Option B: Manual annotation template (no tokens)
python pipeline_manager.py --stage annotate --source ORTHODOXY_CHEST_chunks.jsonl --annotation-method manual

# Review annotations in 03_annotated/
# When satisfied with metadata:
touch 03_annotated/ORTHODOXY_CHEST_annotated.jsonl.approved
```

**Sample Annotated Output**:
```json
{
  "id": "ORTHODOXY_CHEST_0",
  "text": "THIS book is meant to be a companion to \"Heretics,\" and to put...",
  "source": "Orthodoxy",
  "author": "Gilbert K. Chesterton", 
  "structure_path": ["Preface"],
  "metadata": {
    "concepts": ["Faith", "Theology", "Authority"],
    "topics": ["Faith/Personal vs Systematic", "Theology/Apologetic Method"],
    "terms": ["Christian Faith", "apologetics", "autobiography"],
    "discourse_elements": ["Logical/Claim: This book is an attempt to answer the challenge"],
    "scripture_references": [],
    "named_entities": ["Person/John Henry Newman", "Work/Heretics"]
  },
  "processing_stage": "annotated"
}
```

### Stage 3: Annotated → Complete
**Input**: Approved annotations  
**Output**: Chunks + metadata + vectors  
**Cost**: Medium (embedding generation)  
**Human Review**: ❌ Not required (automated)

```bash
# Generate embeddings
python pipeline_manager.py --stage vectorize --source ORTHODOXY_CHEST_annotated.jsonl

# Result ready for RAG deployment!
```

**Sample Complete Output**:
```json
{
  "id": "ORTHODOXY_CHEST_0",
  "text": "THIS book is meant to be a companion to \"Heretics,\" and to put...",
  "source": "Orthodoxy",
  "author": "Gilbert K. Chesterton",
  "metadata": {
    "concepts": ["Faith", "Theology", "Authority"],
    "topics": ["Faith/Personal vs Systematic"],
    "terms": ["Christian Faith", "apologetics"],
    "discourse_elements": ["Logical/Claim: This book is an attempt to answer the challenge"],
    "scripture_references": [],
    "named_entities": ["Person/John Henry Newman"]
  },
  "embedding": [0.1234, -0.5678, 0.9012, ...],  // 1536 dimensions
  "processing_stage": "complete"
}
```

## Human Review Checkpoints

### Checkpoint 1: Chunk Quality Review
**Location**: `02_chunked/`  
**Purpose**: Verify chunks before expensive AI processing  
**Questions to Ask**:
- Are chunks the right size (1000-1500 chars)?
- Do chunks respect argument/paragraph boundaries?
- Is structure_path correct?
- Are any chunks obviously wrong/corrupted?

**Approval Process**:
```bash
# Review file
cat 02_chunked/ORTHODOXY_CHEST_chunks.jsonl | jq .

# If satisfied, approve for annotation
touch 02_chunked/ORTHODOXY_CHEST_chunks.jsonl.approved
```

### Checkpoint 2: Metadata Quality Review  
**Location**: `03_annotated/`  
**Purpose**: Verify theological metadata accuracy  
**Questions to Ask**:
- Are concepts from the fixed Concepts Index?
- Are topics in correct `[[Concept/Topic]]` format?
- Are discourse elements properly categorized?
- Are named entities in correct `[[Class/Entity]]` format?

**Approval Process**:
```bash
# Review annotations
cat 03_annotated/ORTHODOXY_CHEST_annotated.jsonl | jq '.metadata'

# If satisfied, approve for vectorization
touch 03_annotated/ORTHODOXY_CHEST_annotated.jsonl.approved
```

## Workflow Commands

### Check Pipeline Status
```bash
python pipeline_manager.py --stage status
```

**Output**:
```
=== PROCESSING PIPELINE STATUS ===
SOURCES: 12 files (0 approved, 12 pending)
CHUNKED: 8 files (6 approved, 2 pending) 
ANNOTATED: 6 files (4 approved, 2 pending)
COMPLETE: 4 files (4 approved, 0 pending)

=== FILES PENDING HUMAN REVIEW ===
📝 CHUNK REVIEW: ORTHODOXY_CHEST_chunks.jsonl
   → Review chunks and run: touch 02_chunked/ORTHODOXY_CHEST_chunks.jsonl.approved
🏷️ ANNOTATION REVIEW: CONFESSIONS_AUG_annotated.jsonl  
   → Review annotations and run: touch 03_annotated/CONFESSIONS_AUG_annotated.jsonl.approved
```

### Complete Processing Workflow
```bash
# 1. Add source file
cp orthodoxy.xml theological_processing/01_sources/

# 2. Create chunks
python pipeline_manager.py --stage chunk --source orthodoxy.xml

# 3. Review chunks (manually check file)
cat 02_chunked/ORTHODOXY_CHEST_chunks.jsonl | head -5

# 4. Approve chunks
touch 02_chunked/ORTHODOXY_CHEST_chunks.jsonl.approved

# 5. Generate annotations (AI method)
python pipeline_manager.py --stage annotate --source ORTHODOXY_CHEST_chunks.jsonl

# 6. Review annotations (manually check metadata)
cat 03_annotated/ORTHODOXY_CHEST_annotated.jsonl | jq '.metadata' | head -20

# 7. Approve annotations
touch 03_annotated/ORTHODOXY_CHEST_annotated.jsonl.approved

# 8. Generate vectors
python pipeline_manager.py --stage vectorize --source ORTHODOXY_CHEST_annotated.jsonl

# 9. Ready for deployment!
ls 04_complete/ORTHODOXY_CHEST_complete.jsonl
```

## Cost Optimization Benefits

### Token Cost Savings
- **No wasted tokens on bad chunks** - Review chunks before AI annotation
- **No re-annotation costs** - Fix chunks once, annotate once
- **Batch processing efficiency** - Process multiple approved files together

### Quality Control Benefits
- **Consistent chunking** - Human oversight ensures quality standards
- **Theological accuracy** - Expert review of metadata assignments
- **Error prevention** - Catch issues early in pipeline

### Processing Flexibility
- **Custom templates** - Different processing for different source types
- **Manual annotation option** - Skip AI costs for sensitive/complex texts
- **Selective processing** - Only process approved content

## Integration with Existing Tools

### Connects to Your Current System
- **Uses your XML converter** - Leverages existing CCEL processing
- **Uses your metadata schema** - Integrates with source metadata manager
- **Uses your annotation prompt** - AI annotation follows your guidelines

### Extensible Architecture
- **Custom templates** - Add new source type processors
- **Pluggable annotators** - Swap AI models or use manual annotation
- **Multiple embedding models** - OpenAI, Cohere, local models

## For 500-Source Library

### Batch Processing
```bash
# Process all files in sources folder
for file in 01_sources/*.xml; do
    python pipeline_manager.py --stage chunk --source "$(basename "$file")"
done

# Check what needs review
python pipeline_manager.py --stage status
```

### Quality Metrics Tracking
- Processing logs track success rates
- Human approval rates indicate template quality
- Error patterns help improve automation

This pipeline ensures you **never waste money on bad chunks** while maintaining the **highest theological accuracy** for your library.