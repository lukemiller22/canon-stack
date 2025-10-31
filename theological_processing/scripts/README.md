# Processing Scripts

This folder contains versioned scripts used for processing different sources. Each script is tailored to handle the specific structure of the source document.

## Scripts

- `chunk_orthodoxy.py` - Reference for simple flat structure (div1 chapters only)
- `chunk_confessions.py` - Enhanced processor for nested structure (div1 Books containing div2 Chapters)

## Script Details

### chunk_confessions.py

**Purpose**: Handles Augustine's Confessions which has a nested structure:
- `div1` = Books (Book I, Book II, etc.)
- `div2` = Chapters within each Book (Chapter I, Chapter II, etc.)

**Features**:
- Processes each Book separately
- Extracts Chapters from within each Book
- Builds structure paths like "Book I > Chapter I"
- Automatically skips the table of contents ("Contents" section)
- Handles verse elements within chapters

**Usage**: The pipeline_manager.py automatically detects confessions.xml and uses this processor.

### chunk_orthodoxy.py

**Purpose**: Reference/placeholder for sources with flat structure.

**Features**:
- Uses the standard `CCELThMLProcessor` from `ccel_xml_to_markdown.py`
- No special handling needed for flat structures

## Script Naming Convention

Scripts are named: `chunk_{source_name}.py`

This allows us to:
1. Keep a record of how each source was processed
2. Reuse processing logic for similar sources
3. Automate future processing steps
4. Track which processor was used for each source type

## Integration

The `pipeline_manager.py` automatically detects sources and uses the appropriate processor:
- Detects "confessions" in filename or title → uses `ConfessionsProcessor`
- Other sources → uses standard `CCELThMLProcessor`

