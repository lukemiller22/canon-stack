# CCEL XML to Markdown Converter

This script converts theological XML files from CCEL (Christian Classics Ethereal Library) into the markdown format expected by your theological text metadata annotation prompt.

## Features

- **ThML Format Support**: Handles CCEL's ThML (Theological Markup Language) format
- **Robust XML Parsing**: Automatically fixes common XML issues like unescaped ampersands
- **Intelligent Chunking**: Respects paragraph boundaries while keeping chunks ~1500 characters
- **Metadata Extraction**: Pulls title, author, and publication info from Dublin Core metadata
- **Structure Preservation**: Maintains hierarchical document structure (chapters, sections)
- **URL Support**: Can process files directly from CCEL URLs

## Usage

### Basic Usage
```bash
python ccel_xml_to_markdown.py input.xml output.md
```

### Process from CCEL URL
```bash
python ccel_xml_to_markdown.py https://ccel.org/ccel/c/chesterton/orthodoxy.xml orthodoxy.md
```

### Custom chunk length
```bash
python ccel_xml_to_markdown.py input.xml output.md --max-chunk-length 1200
```

### Include administrative front matter (acknowledgments, dedications, etc.)
```bash
python ccel_xml_to_markdown.py input.xml output.md --include-front-matter
```

### Include back matter (appendices, indexes)
```bash
python ccel_xml_to_markdown.py input.xml output.md --include-back-matter
```

### Verbose processing (see what's being filtered)
```bash
python ccel_xml_to_markdown.py input.xml output.md --verbose
```

## Content Filtering

**By default, the script includes all substantial theological content and filters out only administrative/publisher material:**

### Always Skipped
- Title pages
- Table of contents  
- Copyright pages

### Administrative Front Matter (skipped by default, use `--include-front-matter` to include)
- Acknowledgments and dedications
- Publisher information
- Biographical sketches (about the author)
- Translator/editor notes
- Very short Roman numeral sections (likely administrative)

### Theological Content (ALWAYS included by default)
- **Prefaces** - often contain theological rationale
- **Forewords** - frequently theological in nature  
- **Introductions** - usually substantial theological content
- **Main chapters and sections**
- **Substantial Roman numeral sections**

### Back Matter (skipped by default, use `--include-back-matter` to include)
- Appendices
- Bibliographies  
- Indexes and glossaries
- Endnotes and footnotes sections
- Publisher advertisements

## Structure Path Generation

The script automatically generates hierarchical structure paths for each chunk based on the XML structure:

### Examples from Chesterton's Orthodoxy:
- `[[Preface]]` - Content from the preface section
- `[[Chapter I > I. INTRODUCTION IN DEFENCE OF EVERYTHING ELSE]]` - Content from Chapter I, section "Introduction in Defence of Everything Else"
- `[[Chapter 3 > The Problem of Pain]]` - Chapter with subsection
- `[[Foreword > Historical Context]]` - Foreword with subsection

### Structure Path Rules:
- Uses div1 titles and heading elements (h1, h2) from the XML
- Automatically converts numbers to "Chapter X" format
- Includes prefaces, forewords, and introductions as meaningful sections
- Skips redundant headings (like book title repetitions)
- Uses breadcrumb format: `Section > Subsection > Sub-subsection`
- Empty if no meaningful hierarchical structure is found

This ensures each chunk can be located within the document's logical structure for annotation and retrieval.

## Output Format

The script generates markdown files in the exact format expected by your annotation prompt:

```markdown
- # Source Metadata
    - Core-Identification
        - Source-ID:: 
        - Title:: [[Title]]
        - Author-Primary:: [[Author]]
        - Publication-Year:: [[Year]]
    # ... more metadata

- # Chunks
    - ## Chapter/Section
        - Chunk:: [Text content here...]
            - concepts::
            - topics::
            - terms::
            - discourse-elements::
            - scripture-references::
            - structure-path::
            - named-entities::
```

## How It Works

1. **XML Parsing**: Downloads or reads the ThML file and cleans up common formatting issues
2. **Metadata Extraction**: Pulls bibliographic information from Dublin Core fields
3. **Structure Analysis**: Identifies div1 sections, headings, and paragraphs
4. **Text Chunking**: Splits content into ~1500 character chunks respecting paragraph boundaries
5. **Markdown Generation**: Outputs in the format expected by your annotation prompt

## Error Handling

The script includes robust error handling for common CCEL XML issues:
- Unescaped ampersands (e.g., "Dodd, Mead & Co.")
- Unclosed tags
- Processing instructions and comments
- Style elements that may contain invalid content

## Dependencies

```bash
pip install requests
```

Standard library modules used: xml.etree.ElementTree, re, sys, pathlib, argparse, typing, urllib.parse

## Examples

### Process Chesterton's Orthodoxy
```bash
python ccel_xml_to_markdown.py https://ccel.org/ccel/c/chesterton/orthodoxy.xml orthodoxy.md
```

### Process Augustine's Confessions
```bash
python ccel_xml_to_markdown.py https://ccel.org/ccel/a/augustine/confessions.xml confessions.md
```

### Process Lewis's Mere Christianity
```bash
python ccel_xml_to_markdown.py https://ccel.org/ccel/l/lewis/mere.xml mere_christianity.md
```

## Next Steps

After conversion, use the generated markdown files with your theological annotation prompt to:

1. **Annotate Chunks**: Apply concepts, topics, terms, and discourse elements
2. **Generate JSONL**: Convert annotated markdown to JSONL format
3. **Create Embeddings**: Generate vector embeddings for RAG applications

The converted files are ready for immediate use with Sonnet for theological text annotation following your established methodology.