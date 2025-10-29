#!/usr/bin/env python3
"""
Theological Source Metadata Manager

Integrates with the CCEL XML converter to create and manage comprehensive
source metadata for theological texts.

Usage:
    from source_metadata_manager import SourceMetadataManager
    
    manager = SourceMetadataManager()
    metadata = manager.extract_and_enrich(source_file, format_type)
"""

import json
import yaml
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any
from datetime import datetime
import re


@dataclass
class SourceIdentification:
    source_id: str
    title: str
    subtitle: str = ""
    original_title: str = ""
    author_primary: str = ""
    author_additional: List[str] = None
    translator: str = ""
    editor: str = ""
    
    def __post_init__(self):
        if self.author_additional is None:
            self.author_additional = []


@dataclass 
class PublicationInfo:
    original_publication_year: Optional[int] = None
    original_publisher: str = ""
    original_place: str = ""
    edition_notes: str = ""
    source_format: str = ""
    source_url: str = ""
    public_domain_status: bool = True
    copyright_notes: str = ""


@dataclass
class TheologicalClassification:
    primary_genre: str = ""
    secondary_genre: str = ""
    theological_tradition: str = ""
    denominational_affiliation: str = ""
    historical_period: str = ""
    century: str = ""
    theological_movement: str = ""


@dataclass
class ContentCharacteristics:
    language: str = "English"
    original_language: str = "English"
    length_words: Optional[int] = None
    length_pages: Optional[int] = None
    structure_type: str = "monograph"
    chapter_count: Optional[int] = None
    has_preface: bool = False
    has_introduction: bool = False
    has_appendices: bool = False
    has_bibliography: bool = False
    has_index: bool = False


@dataclass
class TheologicalScope:
    primary_concepts: List[str] = None
    theological_topics: List[str] = None
    target_audience: str = ""
    reading_level: str = ""
    
    def __post_init__(self):
        if self.primary_concepts is None:
            self.primary_concepts = []
        if self.theological_topics is None:
            self.theological_topics = []


@dataclass
class ProcessingMetadata:
    processor_version: str = "1.0"
    processing_date: str = ""
    chunk_count: Optional[int] = None
    structure_confidence: float = 0.0
    quality_score: float = 0.0
    manual_review_required: bool = False
    processing_notes: str = ""
    
    def __post_init__(self):
        if not self.processing_date:
            self.processing_date = datetime.now().isoformat()


@dataclass
class SourceMetadata:
    identification: SourceIdentification
    publication: PublicationInfo = None
    theological_classification: TheologicalClassification = None
    content: ContentCharacteristics = None
    theological_scope: TheologicalScope = None
    processing: ProcessingMetadata = None
    
    def __post_init__(self):
        if self.publication is None:
            self.publication = PublicationInfo()
        if self.theological_classification is None:
            self.theological_classification = TheologicalClassification()
        if self.content is None:
            self.content = ContentCharacteristics()
        if self.theological_scope is None:
            self.theological_scope = TheologicalScope()
        if self.processing is None:
            self.processing = ProcessingMetadata()


class SourceMetadataManager:
    """Manages comprehensive source metadata for theological texts."""
    
    def __init__(self):
        self.theological_traditions = self._load_theological_traditions()
        self.genres = self._load_theological_genres()
        self.historical_periods = self._load_historical_periods()
        
    def _load_theological_traditions(self) -> Dict[str, List[str]]:
        """Load theological tradition classification data."""
        return {
            'Protestant': ['Lutheran', 'Reformed', 'Anglican', 'Baptist', 'Methodist', 'Presbyterian'],
            'Catholic': ['Roman Catholic', 'Eastern Catholic'],
            'Orthodox': ['Eastern Orthodox', 'Oriental Orthodox'],
            'Patristic': ['Early Church Fathers', 'Apostolic Fathers'],
            'Other': ['Anabaptist', 'Quaker', 'Pentecostal']
        }
    
    def _load_theological_genres(self) -> List[str]:
        """Load theological genre classifications."""
        return [
            'Systematic Theology', 'Biblical Commentary', 'Christian Apologetics',
            'Devotional Literature', 'Sermon Collections', 'Spiritual Autobiography',
            'Church History', 'Theological Ethics', 'Practical Theology',
            'Biblical Theology', 'Historical Theology', 'Liturgical Texts',
            'Confessional Documents', 'Theological Biography', 'Missionary Accounts'
        ]
    
    def _load_historical_periods(self) -> Dict[str, tuple]:
        """Load historical period classifications with date ranges."""
        return {
            'Apostolic': (30, 100),
            'Patristic': (100, 800),
            'Medieval': (800, 1500),
            'Reformation': (1500, 1650),
            'Post-Reformation': (1650, 1800),
            'Modern': (1800, 1950),
            'Contemporary': (1950, 2030)
        }
    
    def extract_from_ccel_xml(self, xml_root) -> SourceMetadata:
        """Extract metadata from CCEL XML structure."""
        
        # Extract basic identification
        identification = self._extract_identification_from_xml(xml_root)
        
        # Extract publication info
        publication = self._extract_publication_from_xml(xml_root)
        
        # Infer theological classification
        theological = self._infer_theological_classification(identification, publication)
        
        # Analyze content characteristics
        content = self._analyze_content_from_xml(xml_root)
        
        # Create processing metadata
        processing = ProcessingMetadata(
            processor_version="1.0",
            processing_notes="Extracted from CCEL XML"
        )
        
        return SourceMetadata(
            identification=identification,
            publication=publication,
            theological_classification=theological,
            content=content,
            processing=processing
        )
    
    def _extract_identification_from_xml(self, xml_root) -> SourceIdentification:
        """Extract identification metadata from XML."""
        
        # Extract title
        title_elem = xml_root.find('.//DC.Title')
        title = title_elem.text.strip() if title_elem is not None and title_elem.text else "Unknown Title"
        
        # Extract author
        author_elem = xml_root.find('.//DC.Creator[@sub="Author"][@scheme="short-form"]')
        if author_elem is None:
            author_elem = xml_root.find('.//DC.Creator[@sub="Author"]')
        author = author_elem.text.strip() if author_elem is not None and author_elem.text else "Unknown Author"
        
        # Generate source ID
        source_id = self._generate_source_id(title, author)
        
        return SourceIdentification(
            source_id=source_id,
            title=title,
            author_primary=author
        )
    
    def _extract_publication_from_xml(self, xml_root) -> PublicationInfo:
        """Extract publication metadata from XML."""
        
        # Extract publication year
        date_elem = xml_root.find('.//DC.Date')
        pub_year = None
        if date_elem is not None and date_elem.text:
            year_match = re.search(r'\b(19|20)\d{2}\b', date_elem.text)
            if year_match:
                pub_year = int(year_match.group(0))
        
        # Extract publisher
        publisher_elem = xml_root.find('.//DC.Publisher')
        publisher = publisher_elem.text.strip() if publisher_elem is not None and publisher_elem.text else ""
        
        return PublicationInfo(
            original_publication_year=pub_year,
            original_publisher=publisher,
            source_format="ccel_xml",
            public_domain_status=True
        )
    
    def _generate_source_id(self, title: str, author: str) -> str:
        """Generate a unique source identifier."""
        # Clean title and author for ID
        clean_title = re.sub(r'[^a-zA-Z]', '', title)[:8].upper()
        clean_author = re.sub(r'[^a-zA-Z]', '', author.split()[-1])[:6].upper()
        
        return f"{clean_title}_{clean_author}"
    
    def _infer_theological_classification(self, identification: SourceIdentification, 
                                        publication: PublicationInfo) -> TheologicalClassification:
        """Infer theological classification from available data."""
        
        # Determine historical period from publication year
        historical_period = ""
        century = ""
        if publication.original_publication_year:
            for period, (start, end) in self.historical_periods.items():
                if start <= publication.original_publication_year <= end:
                    historical_period = period
                    break
            century = f"{((publication.original_publication_year - 1) // 100) + 1}"
            if century == "21":
                century = "21st"
            elif century == "20":
                century = "20th"
            elif century == "19":
                century = "19th"
            else:
                century = f"{century}th"
        
        # Basic classification (could be enhanced with NLP)
        classification = TheologicalClassification(
            historical_period=historical_period,
            century=century
        )
        
        # Genre inference based on title patterns
        title_lower = identification.title.lower()
        if any(word in title_lower for word in ['confessions', 'autobiography', 'life']):
            classification.primary_genre = 'Spiritual Autobiography'
        elif any(word in title_lower for word in ['apology', 'apologetics', 'defense', 'orthodoxy']):
            classification.primary_genre = 'Christian Apologetics'
        elif any(word in title_lower for word in ['sermons', 'homilies', 'preaching']):
            classification.primary_genre = 'Sermon Collections'
        elif any(word in title_lower for word in ['commentary', 'exposition']):
            classification.primary_genre = 'Biblical Commentary'
        
        return classification
    
    def _analyze_content_from_xml(self, xml_root) -> ContentCharacteristics:
        """Analyze content characteristics from XML structure."""
        
        # Count chapters/divisions
        div1_elements = xml_root.findall('.//div1')
        chapter_count = len([div for div in div1_elements 
                           if div.get('title', '').lower() not in ['title page', 'toc']])
        
        # Check for structural elements
        has_preface = any(div.get('title', '').lower() == 'preface' for div in div1_elements)
        has_introduction = any('introduction' in div.get('title', '').lower() for div in div1_elements)
        
        return ContentCharacteristics(
            chapter_count=chapter_count,
            has_preface=has_preface,
            has_introduction=has_introduction,
            structure_type="monograph"
        )
    
    def enrich_after_processing(self, metadata: SourceMetadata, 
                               processing_results: Dict[str, Any]) -> SourceMetadata:
        """Enrich metadata after text processing is complete."""
        
        # Update processing metadata
        metadata.processing.chunk_count = processing_results.get('chunk_count', 0)
        metadata.processing.structure_confidence = processing_results.get('structure_confidence', 0.0)
        metadata.processing.quality_score = processing_results.get('quality_score', 0.0)
        
        # Update content characteristics
        if 'word_count' in processing_results:
            metadata.content.length_words = processing_results['word_count']
        
        # Extract theological scope from chunk metadata
        if 'extracted_concepts' in processing_results:
            metadata.theological_scope.primary_concepts = processing_results['extracted_concepts']
        
        if 'extracted_topics' in processing_results:
            metadata.theological_scope.theological_topics = processing_results['extracted_topics']
        
        return metadata
    
    def save_metadata(self, metadata: SourceMetadata, format: str = 'yaml') -> str:
        """Save metadata in specified format."""
        
        if format == 'yaml':
            return yaml.dump(asdict(metadata), default_flow_style=False, sort_keys=False)
        elif format == 'json':
            return json.dumps(asdict(metadata), indent=2)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def load_metadata(self, metadata_str: str, format: str = 'yaml') -> SourceMetadata:
        """Load metadata from string representation."""
        
        if format == 'yaml':
            data = yaml.safe_load(metadata_str)
        elif format == 'json':
            data = json.loads(metadata_str)
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        # Reconstruct dataclass objects
        identification = SourceIdentification(**data['identification'])
        publication = PublicationInfo(**data['publication'])
        theological_classification = TheologicalClassification(**data['theological_classification'])
        content = ContentCharacteristics(**data['content'])
        theological_scope = TheologicalScope(**data['theological_scope'])
        processing = ProcessingMetadata(**data['processing'])
        
        return SourceMetadata(
            identification=identification,
            publication=publication,
            theological_classification=theological_classification,
            content=content,
            theological_scope=theological_scope,
            processing=processing
        )


# Integration example
def integrate_with_xml_converter():
    """Example of how to integrate with existing XML converter."""
    
    from ccel_xml_to_markdown import CCELThMLProcessor
    
    class EnhancedCCELProcessor(CCELThMLProcessor):
        def __init__(self):
            super().__init__()
            self.metadata_manager = SourceMetadataManager()
        
        def convert_to_markdown_with_metadata(self, source_file: str) -> tuple[str, SourceMetadata]:
            """Convert to markdown and extract comprehensive metadata."""
            
            # Parse XML as before
            if source_file.startswith('http'):
                response = requests.get(source_file)
                xml_content = response.text
            else:
                with open(source_file, 'r', encoding='utf-8') as f:
                    xml_content = f.read()
            
            # Clean and parse XML
            xml_content = self._clean_xml_content(xml_content)
            root = ET.fromstring(xml_content)
            
            # Extract comprehensive metadata
            source_metadata = self.metadata_manager.extract_from_ccel_xml(root)
            
            # Process content as before
            sections = self.process_div1_sections(root)
            markdown_content = self._generate_markdown(sections, source_metadata)
            
            # Enrich metadata with processing results
            processing_results = {
                'chunk_count': len([chunk for section in sections 
                                  for chunk in self.chunk_text(section['full_text'])]),
                'structure_confidence': 0.95,  # Based on processing success
                'quality_score': 0.90
            }
            
            enriched_metadata = self.metadata_manager.enrich_after_processing(
                source_metadata, processing_results
            )
            
            return markdown_content, enriched_metadata


if __name__ == '__main__':
    # Example usage
    manager = SourceMetadataManager()
    
    # Create sample metadata
    identification = SourceIdentification(
        source_id="ORTH_CHEST",
        title="Orthodoxy",
        author_primary="Gilbert K. Chesterton"
    )
    
    metadata = SourceMetadata(identification=identification)
    
    # Save as YAML
    yaml_output = manager.save_metadata(metadata, 'yaml')
    print("Source metadata schema created successfully!")
    print("\nSample YAML output:")
    print(yaml_output[:500] + "...")