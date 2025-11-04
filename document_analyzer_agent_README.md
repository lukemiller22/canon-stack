# Document Analyzer Agent

An AI-powered agent that analyzes documents in any format and generates optimized chunking strategies for your theological text processing pipeline.

## Features

✨ **Multi-Format Support**
- PDF documents
- Word documents (DOCX)
- ePub files
- HTML/XML files
- Plain text and Markdown
- Web URLs (articles, blog posts)

🧠 **AI-Powered Analysis**
- Automatically detects document structure
- Identifies hierarchy (chapters, sections, subsections)
- Recognizes special features (footnotes, citations, scripture references)
- Recommends optimal chunking strategy

💰 **Cost Transparency**
- Estimates processing costs before you commit
- Breaks down costs by stage (analysis, annotation, embedding)
- Helps you budget for large document collections

🔧 **Three Usage Modes**
1. **Analyze**: Get a detailed analysis and recommendations
2. **Generate Script**: Create a custom chunking script
3. **Process**: End-to-end automated chunking with pipeline integration

## Installation

### 1. Basic Installation

```bash
# Install required packages
pip install anthropic

# Optional: Install format-specific parsers as needed
pip install pypdf              # For PDF support
pip install python-docx        # For DOCX support
pip install ebooklib beautifulsoup4  # For ePub and HTML
pip install requests           # For URL support
```

### 2. Set Up API Key

```bash
# Set your Anthropic API key
export ANTHROPIC_API_KEY="your-api-key-here"

# Or create a .env file
echo "ANTHROPIC_API_KEY=your-api-key-here" > .env
```

### 3. Make Executable (Optional)

```bash
chmod +x document_analyzer_agent.py
```

## Quick Start

### Analyze a Document

Get a detailed analysis without processing:

```bash
python document_analyzer_agent.py analyze path/to/book.pdf
```

**Output:**
```
🔍 Analyzing document: path/to/book.pdf
✅ Analysis complete!

============================================================
DOCUMENT ANALYSIS SUMMARY
============================================================
File: path/to/book.pdf
Type: pdf
Size: 245,832 characters (~61,458 tokens)

Structure:
  Has hierarchy: True
  Levels: Chapter, Section, Subsection
  Sections: 15

Features:
  Footnotes: True
  Citations: True
  Images: False
  Special: scripture references, extended quotes

Recommended Strategy:
  Method: structural
  Chunk size: 1200 characters
  Overlap: 200 characters

Cost Estimate:
  Analysis Cost: $0.0060
  Annotation Cost: $0.2250
  Embedding Cost: $0.0098
  Total Cost: $0.2408
  Estimated Chunks: 75
============================================================
```

### Generate a Custom Chunking Script

Create a Python script tailored to your document:

```bash
python document_analyzer_agent.py generate-script path/to/book.pdf
```

This creates `chunk_book.py` that you can:
- Review and customize
- Run independently: `python chunk_book.py`
- Share with your team

### Process End-to-End

Analyze, chunk, and integrate with your pipeline in one command:

```bash
# With manual review (recommended)
python document_analyzer_agent.py process path/to/book.pdf

# Skip review (if you're confident)
python document_analyzer_agent.py process path/to/book.pdf --auto-approve
```

**Output:**
```
🚀 Processing document: path/to/book.pdf
🔍 Analyzing document: path/to/book.pdf
✅ Analysis complete!
✅ Saved 75 chunks to: theological_processing/02_chunked/BOOK_chunks.jsonl
⚠️  Review required: Check theological_processing/02_chunked/BOOK_chunks.jsonl
   Approve with: touch theological_processing/02_chunked/BOOK_chunks.jsonl.approved
```

## Usage Examples

### Example 1: Process a PDF Book

```bash
# Analyze first to see costs
python document_analyzer_agent.py analyze books/systematic_theology.pdf

# If costs look good, process it
python document_analyzer_agent.py process books/systematic_theology.pdf
```

### Example 2: Process a Web Article

```bash
python document_analyzer_agent.py process https://example.com/article/theology-post
```

### Example 3: Batch Process Multiple Files

```bash
# Create a simple batch script
for file in documents/*.pdf; do
    echo "Processing: $file"
    python document_analyzer_agent.py process "$file"
done
```

### Example 4: Custom Pipeline Directory

```bash
python document_analyzer_agent.py process book.pdf \
    --pipeline-dir /path/to/custom/pipeline
```

### Example 5: Generate Scripts for Team Review

```bash
# Generate scripts for your team to review before processing
for file in documents/*.pdf; do
    python document_analyzer_agent.py generate-script "$file" \
        --output "scripts/chunk_$(basename $file .pdf).py"
done
```

## Integration with Existing Pipeline

The agent integrates seamlessly with your theological processing pipeline:

```
theological_processing/
├── 01_sources/              # Upload your files here
├── 02_chunked/             # Agent outputs here ← YOU REVIEW
├── 03_annotated/           # Continue with existing pipeline
├── 04_complete/
└── 05_deployed/
```

### Workflow

1. **Upload** your document to `01_sources/` (optional)
2. **Run** the analyzer agent: `python document_analyzer_agent.py process path/to/doc.pdf`
3. **Review** chunks in `02_chunked/`
4. **Approve**: `touch 02_chunked/DOCNAME_chunks.jsonl.approved`
5. **Continue** with your existing pipeline:
   ```bash
   python pipeline_manager.py --stage annotate --source DOCNAME_chunks.jsonl
   ```

## File Format Support

### PDF Documents
✅ Text extraction
✅ Table of contents detection
✅ Multi-page handling
❌ Image-only PDFs (OCR not included)

```bash
python document_analyzer_agent.py analyze paper.pdf
```

### Word Documents (DOCX)
✅ Paragraph extraction
✅ Heading detection
✅ Style preservation
✅ Footnote handling

```bash
python document_analyzer_agent.py analyze thesis.docx
```

### ePub Files
✅ Chapter extraction
✅ Table of contents
✅ HTML content parsing
✅ Multi-chapter books

```bash
python document_analyzer_agent.py analyze ebook.epub
```

### HTML/XML Files
✅ Tag stripping
✅ Structure preservation
✅ Encoding handling

```bash
python document_analyzer_agent.py analyze document.html
python document_analyzer_agent.py analyze export.xml
```

### Web URLs
✅ Article extraction
✅ Clean text extraction
✅ Automatic header removal

```bash
python document_analyzer_agent.py analyze https://blog.example.com/post
```

### Plain Text / Markdown
✅ Direct text handling
✅ Markdown header detection
✅ UTF-8 support (Greek, Hebrew)

```bash
python document_analyzer_agent.py analyze notes.txt
python document_analyzer_agent.py analyze readme.md
```

## Cost Breakdown

The agent provides transparent cost estimates:

| Stage | What It Does | Cost per Document* |
|-------|--------------|-------------------|
| **Analysis** | AI analyzes structure | ~$0.006 |
| **Annotation** | AI extracts metadata | ~$0.015/chunk |
| **Embedding** | Creates vectors | ~$0.0002/chunk |

\* Costs are estimates based on Claude Sonnet and OpenAI embeddings

### Example Costs for Different Documents

**Small Article** (10 chunks):
- Analysis: $0.006
- Annotation: $0.15
- Embedding: $0.002
- **Total: ~$0.16**

**Medium Book** (100 chunks):
- Analysis: $0.006
- Annotation: $1.50
- Embedding: $0.02
- **Total: ~$1.53**

**Large Text** (500 chunks):
- Analysis: $0.006
- Annotation: $7.50
- Embedding: $0.10
- **Total: ~$7.61**

## Advanced Features

### Custom Chunking Strategies

The agent recommends one of four strategies:

1. **Semantic**: Chunks by meaning and topic (best for essays)
2. **Fixed-size**: Equal-sized chunks (best for unstructured text)
3. **Structural**: Chunks by document hierarchy (best for books)
4. **Hybrid**: Combines semantic and structural (best for complex docs)

### Special Feature Detection

The agent automatically detects and handles:

- **Scripture references**: Keeps citations with context
- **Footnotes**: Preserves or separates based on document type
- **Greek/Hebrew text**: Ensures UTF-8 encoding
- **Extended quotes**: Prevents mid-quote splitting
- **Citations**: Maintains academic integrity

### Output Format

All chunks use the standard theological processing format:

```json
{
    "id": "DOCNAME_0",
    "text": "This is the text of the first chunk...",
    "source": "Document Title",
    "author": "Author Name",
    "structure_path": ["Chapter 1", "Section 1.1"],
    "chunk_index": 0,
    "processing_stage": "chunked",
    "processing_timestamp": "2025-01-15T10:30:00"
}
```

## Troubleshooting

### Import Errors

**Problem**: `ModuleNotFoundError: No module named 'pypdf'`

**Solution**:
```bash
pip install pypdf  # For PDFs
pip install python-docx  # For DOCX
pip install ebooklib beautifulsoup4  # For ePub/HTML
```

### API Key Not Found

**Problem**: `ValueError: ANTHROPIC_API_KEY not found`

**Solution**:
```bash
export ANTHROPIC_API_KEY="your-key-here"
# Or add to .env file
```

### Permission Errors

**Problem**: Cannot write to `theological_processing/`

**Solution**:
```bash
# Create directories manually
mkdir -p theological_processing/{01_sources,02_chunked,03_annotated,04_complete,05_deployed}

# Or specify custom directory
python document_analyzer_agent.py process doc.pdf --pipeline-dir /custom/path
```

### Large Files Timeout

**Problem**: File too large, agent times out

**Solution**:
```bash
# Use generate-script to create custom script
python document_analyzer_agent.py generate-script large_book.pdf

# Edit the script to process in batches
nano chunk_large_book.py

# Run the customized script
python chunk_large_book.py
```

## Tips for Best Results

### 1. Start Small
Begin with 5-10 documents to calibrate the agent's performance before processing your entire library.

### 2. Review First Batch Closely
The first few documents help you understand the agent's behavior and refine your approval criteria.

### 3. Use Analysis Mode
Always run `analyze` first for expensive or important documents to see cost estimates.

### 4. Keep Manual Review
Don't skip the review step! The agent is smart, but human oversight ensures quality.

### 5. Customize Generated Scripts
The generated scripts are starting points—feel free to modify them for special cases.

### 6. Batch Similar Documents
Process similar document types together for consistency (all PDFs, then all DOCXs, etc.).

## Python API Usage

You can also use the agent programmatically:

```python
from document_analyzer_agent import DocumentAnalyzerAgent

# Initialize agent
agent = DocumentAnalyzerAgent(api_key="your-key")

# Analyze a document
structure = agent.analyze_file("book.pdf")
print(f"Recommended chunk size: {structure.recommended_chunk_size}")
print(f"Estimated cost: ${structure.cost_estimate['total_cost_usd']}")

# Generate chunking script
script_path = agent.generate_chunking_script("book.pdf")

# Process end-to-end
result = agent.process_document(
    "book.pdf",
    pipeline_base_dir="theological_processing",
    auto_approve=False
)
print(f"Created {result['chunk_count']} chunks")
```

## Future Enhancements

Planned features:
- [ ] OCR support for image-based PDFs
- [ ] Multi-language detection
- [ ] Custom chunking rules via config file
- [ ] Parallel processing for large batches
- [ ] Quality scoring for generated chunks
- [ ] Integration with more LLM providers

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review the generated logs in `theological_processing/logs/`
3. Examine the generated chunks manually
4. Adjust the analysis prompt if needed

## License

This tool integrates with your existing theological processing pipeline and uses the same licensing.

---

**Ready to automate your document processing?** Start with `analyze` mode and go from there! 🚀