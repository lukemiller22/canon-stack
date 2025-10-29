# Theological Source Metadata Schema

This schema captures the rich bibliographic and theological metadata needed for a comprehensive theological library suitable for agentic search and research.

## Core Source Metadata Structure

```yaml
source_metadata:
  # ===== IDENTIFICATION =====
  identification:
    source_id: "ORTH_1908_CHEST"          # Unique identifier
    title: "Orthodoxy"                     # Primary title
    subtitle: ""                           # Subtitle if any
    original_title: ""                     # If translated
    author_primary: "Gilbert K. Chesterton"
    author_additional: []                  # Co-authors, editors
    translator: ""                         # If translated work
    editor: ""                            # If edited collection
    
  # ===== PUBLICATION INFO =====
  publication:
    original_publication_year: 1908
    original_publisher: "Dodd, Mead & Company"
    original_place: "New York"
    edition_notes: "First edition"
    source_format: "ccel_xml"             # ccel_xml, pdf, epub, etc.
    source_url: "https://ccel.org/ccel/c/chesterton/orthodoxy.xml"
    public_domain_status: true
    copyright_notes: "Public domain in US"
    
  # ===== THEOLOGICAL CLASSIFICATION =====
  theological_classification:
    primary_genre: "Christian Apologetics"
    secondary_genre: "Spiritual Autobiography"
    theological_tradition: "Anglican"      # Protestant, Catholic, Orthodox, etc.
    denominational_affiliation: "Church of England"
    historical_period: "Modern"           # Patristic, Medieval, Reformation, Modern
    century: "20th"
    theological_movement: "Distributism"   # Optional: specific movements
    
  # ===== CONTENT CHARACTERISTICS =====
  content:
    language: "English"
    original_language: "English"
    length_words: 50000                   # Approximate
    length_pages: 180                     # If available
    structure_type: "monograph"           # monograph, collection, series
    chapter_count: 8
    has_preface: true
    has_introduction: true
    has_appendices: false
    has_bibliography: false
    has_index: false
    
  # ===== THEOLOGICAL SCOPE =====
  theological_scope:
    primary_concepts:                     # From your fixed Concepts Index
      - "Faith"
      - "Authority" 
      - "Revelation"
      - "Philosophy"
      - "Truth"
    theological_topics:                   # Flexible theological coverage
      - "General Apologetics"
      - "Christian Worldview"
      - "Faith and Reason"
      - "Religious Experience"
      - "Orthodoxy vs Heresy"
    target_audience: "General Christian"  # Academic, Pastoral, General Christian, etc.
    reading_level: "Advanced"             # Elementary, Intermediate, Advanced
    
  # ===== HISTORICAL CONTEXT =====
  historical_context:
    writing_context: "Response to modernist theology and secular philosophy"
    historical_events: ["Industrial Revolution", "Darwin's Origin of Species"]
    theological_controversies: ["Modernism", "Higher Criticism"]
    influenced_by: ["Thomas Aquinas", "Francis of Assisi"]
    contemporary_with: ["William James", "G.E. Moore"]
    
  # ===== RELATIONSHIPS =====
  relationships:
    companion_works: ["Heretics"]         # Explicitly related works
    series_info: 
      series_title: ""
      volume_number: ""
      total_volumes: ""
    referenced_works: []                  # Major works cited/discussed
    influences: []                        # Authors/works that influenced this
    influenced: []                        # Later works influenced by this
    
  # ===== PROCESSING METADATA =====
  processing:
    processor_version: "1.0"
    processing_date: "2024-01-15"
    chunk_count: 45
    structure_confidence: 0.95            # How confident in structure detection
    quality_score: 0.92                   # Overall processing quality
    manual_review_required: false
    processing_notes: "Clean CCEL XML, excellent structure detection"
    
  # ===== SEARCH/DISCOVERY =====
  discovery:
    keywords: ["apologetics", "orthodox", "Christianity", "philosophy", "worldview"]
    subjects_lcsh: ["Christianity", "Apologetics", "Philosophy, Religious"]
    dewey_classification: "239"           # Dewey Decimal if available
    search_tags: ["beginner-friendly", "classic", "foundational"]
```

## Implementation Components

### 1. Source Metadata Database Schema

```sql
-- Core source information
CREATE TABLE sources (
    source_id VARCHAR(50) PRIMARY KEY,
    title TEXT NOT NULL,
    subtitle TEXT,
    author_primary VARCHAR(255) NOT NULL,
    publication_year INTEGER,
    theological_tradition VARCHAR(100),
    primary_genre VARCHAR(100),
    language VARCHAR(50),
    public_domain BOOLEAN DEFAULT TRUE,
    processing_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Theological classification
CREATE TABLE source_concepts (
    source_id VARCHAR(50) REFERENCES sources(source_id),
    concept VARCHAR(100),
    PRIMARY KEY (source_id, concept)
);

-- Source relationships
CREATE TABLE source_relationships (
    source_id VARCHAR(50) REFERENCES sources(source_id),
    related_source_id VARCHAR(50) REFERENCES sources(source_id),
    relationship_type VARCHAR(50), -- 'companion', 'series', 'influenced_by'
    PRIMARY KEY (source_id, related_source_id, relationship_type)
);
```

### 2. Source Metadata Extraction Pipeline

```python
class TheologicalSourceMetadataExtractor:
    def __init__(self):
        self.theological_traditions = self.load_traditions()
        self.genres = self.load_genres()
        self.historical_periods = self.load_periods()
    
    def extract_metadata(self, source_file, format_type):
        """Extract comprehensive source metadata."""
        
        # Basic bibliographic data
        basic = self.extract_bibliographic(source_file, format_type)
        
        # Theological classification
        theological = self.classify_theological_content(source_file)
        
        # Historical context
        historical = self.infer_historical_context(basic, theological)
        
        # Content analysis
        content = self.analyze_content_characteristics(source_file)
        
        return SourceMetadata(
            identification=basic,
            theological_classification=theological,
            historical_context=historical,
            content=content
        )
    
    def classify_theological_content(self, source_file):
        """Classify theological tradition, genre, period."""
        
        # NLP-based classification using patterns learned from 500 sources
        content = self.extract_sample_content(source_file)
        
        tradition = self.classify_tradition(content)
        genre = self.classify_genre(content)
        period = self.classify_period(content)
        
        return {
            'theological_tradition': tradition,
            'primary_genre': genre,
            'historical_period': period
        }
```

### 3. Source Metadata UI/Management

```python
class SourceMetadataManager:
    """Manage source metadata throughout processing pipeline."""
    
    def create_source_record(self, uploaded_file):
        """Create initial source metadata record."""
        # Auto-extract what's possible
        # Present form for human completion
        pass
    
    def enrich_metadata(self, source_id, processing_results):
        """Enrich metadata based on processing results."""
        # Update chunk count, quality scores
        # Add inferred theological classifications
        pass
    
    def validate_metadata(self, source_metadata):
        """Validate theological metadata consistency."""
        # Check tradition/genre consistency
        # Validate concept assignments
        # Flag potential issues
        pass
```