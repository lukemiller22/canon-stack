#!/usr/bin/env python3
"""
Staged Theological Text Processing Pipeline

A multi-stage pipeline that allows human review and approval at each stage
before proceeding to expensive AI processing.

Pipeline Stages:
1. Sources (raw uploads)
2. Chunked (chunks only, no metadata)  
3. Annotated (chunks + metadata, no vectors)
4. Complete (chunks + metadata + vectors)

Usage:
    python pipeline_manager.py --stage chunk --source orthodoxy.xml
    python pipeline_manager.py --stage annotate --source orthodoxy_chunks.jsonl
    python pipeline_manager.py --stage vectorize --source orthodoxy_annotated.jsonl
"""

import json
import os
import sys
import shutil
import xml.etree.ElementTree as ET
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import argparse

from source_metadata_manager import SourceMetadataManager
from ccel_xml_to_markdown import CCELThMLProcessor

# Import enhanced processor for sources with nested structures
try:
    # Import with path adjustment for scripts folder
    from pathlib import Path
    scripts_path = Path(__file__).parent / 'theological_processing' / 'scripts'
    if str(scripts_path) not in sys.path:
        sys.path.insert(0, str(scripts_path))
    from chunk_confessions import ConfessionsProcessor
    CONFESSIONS_PROCESSOR_AVAILABLE = True
except ImportError:
    CONFESSIONS_PROCESSOR_AVAILABLE = False
    ConfessionsProcessor = None


@dataclass
class ProcessingStage:
    stage_name: str
    input_folder: str
    output_folder: str
    description: str
    requires_human_review: bool


class TheologicalProcessingPipeline:
    """Manages staged processing of theological texts with human review checkpoints."""
    
    def __init__(self, base_dir: str = "./theological_processing"):
        self.base_dir = Path(base_dir)
        self.stages = self._define_stages()
        
        # Initialize components with validation
        try:
            self.metadata_manager = SourceMetadataManager()
        except Exception as e:
            raise RuntimeError(f"Failed to initialize SourceMetadataManager: {e}")
        
        try:
            self.xml_processor = CCELThMLProcessor()
        except Exception as e:
            raise RuntimeError(f"Failed to initialize CCELThMLProcessor: {e}")
        
        # Create directory structure
        self._setup_directories()
    
    def _define_stages(self) -> Dict[str, ProcessingStage]:
        """Define the processing stages."""
        return {
            'sources': ProcessingStage(
                stage_name='sources',
                input_folder='01_sources',
                output_folder='02_chunked',
                description='Raw source files (XML, PDF, DOCX, etc.)',
                requires_human_review=False
            ),
            'chunked': ProcessingStage(
                stage_name='chunked',
                input_folder='02_chunked',
                output_folder='03_annotated',
                description='Text chunks without metadata (human review required)',
                requires_human_review=True
            ),
            'annotated': ProcessingStage(
                stage_name='annotated',
                input_folder='03_annotated',
                output_folder='04_complete',
                description='Chunks with metadata, no vectors',
                requires_human_review=True
            ),
            'complete': ProcessingStage(
                stage_name='complete',
                input_folder='04_complete',
                output_folder='05_deployed',
                description='Final JSONL with chunks + metadata + vectors',
                requires_human_review=False
            )
        }
    
    def _setup_directories(self):
        """Create the directory structure."""
        folders = [
            '01_sources',           # Raw uploads
            '02_chunked',          # Chunks only (human review)
            '03_annotated',        # Chunks + metadata (human review)  
            '04_complete',         # Chunks + metadata + vectors
            '05_deployed',         # Ready for production
            'metadata',            # Source metadata files
            'logs',               # Processing logs
            'templates',          # Processing templates for different source types
            'rejected'            # Files that failed processing
        ]
        
        try:
            for folder in folders:
                folder_path = self.base_dir / folder
                folder_path.mkdir(parents=True, exist_ok=True)
                
                # Test write permissions
                test_file = folder_path / '.test_write'
                try:
                    test_file.write_text('test')
                    test_file.unlink()
                except Exception as e:
                    raise PermissionError(f"Cannot write to directory {folder_path}: {e}")
                    
        except Exception as e:
            raise RuntimeError(f"Failed to setup directory structure: {e}")
    
    def process_stage_1_to_chunks(self, source_file: str, custom_template: Optional[str] = None) -> str:
        """
        Stage 1→2: Convert source file to chunks (no metadata yet).
        
        Returns: Path to chunked JSONL file
        """
        source_path = Path(source_file)
        
        if not source_path.exists():
            # Try in sources folder
            source_path = self.base_dir / '01_sources' / source_file
            if not source_path.exists():
                raise FileNotFoundError(f"Source file not found: {source_file}")
        
        print(f"Processing {source_path.name} → chunks...")
        
        # Determine source type and process accordingly
        if source_path.suffix.lower() == '.xml':
            chunks, source_metadata = self._process_xml_source(source_path, custom_template)
        elif source_path.suffix.lower() == '.pdf':
            chunks, source_metadata = self._process_pdf_source(source_path, custom_template)
        elif source_path.suffix.lower() in ['.docx', '.doc']:
            chunks, source_metadata = self._process_docx_source(source_path, custom_template)
        else:
            raise ValueError(f"Unsupported file type: {source_path.suffix}")
        
        # Create basic chunks (no metadata yet)
        basic_chunks = []
        for i, chunk in enumerate(chunks):
            basic_chunk = {
                'id': f"{source_metadata.identification.source_id}_{i}",
                'text': chunk['text'],
                'source': source_metadata.identification.title,
                'author': source_metadata.identification.author_primary,
                'structure_path': chunk.get('structure_path', []),
                'chunk_index': i,
                'processing_stage': 'chunked',
                'processing_timestamp': datetime.now().isoformat()
            }
            basic_chunks.append(basic_chunk)
        
        # Save chunks-only JSONL
        output_file = self.base_dir / '02_chunked' / f"{source_metadata.identification.source_id}_chunks.jsonl"
        self._save_jsonl(basic_chunks, output_file)
        
        # Save source metadata separately
        metadata_file = self.base_dir / 'metadata' / f"{source_metadata.identification.source_id}_metadata.yaml"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            f.write(self.metadata_manager.save_metadata(source_metadata, 'yaml'))
        
        # Log processing
        self._log_processing(source_path.name, 'chunked', len(basic_chunks), output_file)
        
        print(f"✓ Created {len(basic_chunks)} chunks → {output_file}")
        print(f"✓ Saved metadata → {metadata_file}")
        print(f"⚠️  HUMAN REVIEW REQUIRED: Check chunks in {output_file}")
        
        return str(output_file)
    
    def process_stage_2_to_annotated(self, chunks_file: str, annotation_method: str = 'ai') -> str:
        """
        Stage 2→3: Add metadata to approved chunks.
        
        annotation_method: 'ai' (use LLM) or 'manual' (human annotation)
        """
        chunks_path = Path(chunks_file)
        if not chunks_path.exists():
            chunks_path = self.base_dir / '02_chunked' / chunks_file
        
        # Load chunks
        chunks = self._load_jsonl(chunks_path)
        
        # Check if human has approved these chunks
        if not self._is_human_approved(chunks_path):
            print(f"⚠️  Chunks not yet approved for annotation: {chunks_path}")
            print("   Create a .approved file to proceed:")
            print(f"   touch {chunks_path}.approved")
            return ""
        
        print(f"Processing {chunks_path.name} → annotated chunks...")
        
        # Load source metadata
        source_id = chunks[0]['id'].rsplit('_', 1)[0]  # Extract source ID
        metadata_file = self.base_dir / 'metadata' / f"{source_id}_metadata.yaml"
        
        if annotation_method == 'ai':
            annotated_chunks = self._annotate_chunks_with_ai(chunks, metadata_file)
        else:
            annotated_chunks = self._create_annotation_template(chunks, metadata_file)
        
        # Save annotated JSONL
        output_file = self.base_dir / '03_annotated' / f"{source_id}_annotated.jsonl"
        self._save_jsonl(annotated_chunks, output_file)
        
        # Log processing
        self._log_processing(chunks_path.name, 'annotated', len(annotated_chunks), output_file)
        
        print(f"✓ Created annotated chunks → {output_file}")
        if annotation_method == 'manual':
            print(f"⚠️  HUMAN ANNOTATION REQUIRED: Complete metadata in {output_file}")
        else:
            print(f"⚠️  HUMAN REVIEW REQUIRED: Verify AI annotations in {output_file}")
        
        return str(output_file)
    
    def process_stage_3_to_complete(self, annotated_file: str, embedding_model: str = 'openai') -> str:
        """
        Stage 3→4: Add vectors to annotated chunks.
        """
        annotated_path = Path(annotated_file)
        if not annotated_path.exists():
            annotated_path = self.base_dir / '03_annotated' / annotated_file
        
        # Check if human has approved annotations
        if not self._is_human_approved(annotated_path):
            print(f"⚠️  Annotations not yet approved for vectorization: {annotated_path}")
            print("   Create a .approved file to proceed:")
            print(f"   touch {annotated_path}.approved")
            return ""
        
        print(f"Processing {annotated_path.name} → complete chunks with vectors...")
        
        # Load annotated chunks
        chunks = self._load_jsonl(annotated_path)
        
        # Add embeddings
        complete_chunks = self._add_embeddings(chunks, embedding_model)
        
        # Save complete JSONL
        source_id = chunks[0]['id'].rsplit('_', 1)[0]
        output_file = self.base_dir / '04_complete' / f"{source_id}_complete.jsonl"
        self._save_jsonl(complete_chunks, output_file)
        
        # Log processing
        self._log_processing(annotated_path.name, 'complete', len(complete_chunks), output_file)
        
        print(f"✓ Created complete chunks with vectors → {output_file}")
        print(f"✓ Ready for deployment!")
        
        return str(output_file)
    
    def process_stage_4_to_deployed(self, complete_file: str) -> str:
        """
        Stage 4→5: Deploy complete chunks to production-ready folder.
        
        This is a simple copy operation - the file is ready for deployment.
        """
        complete_path = Path(complete_file)
        if not complete_path.exists():
            complete_path = self.base_dir / '04_complete' / complete_file
        
        if not complete_path.exists():
            print(f"Error: Complete file not found: {complete_file}")
            return ""
        
        print(f"Deploying {complete_path.name} → production...")
        
        # Copy to deployed folder
        deployed_file = self.base_dir / '05_deployed' / complete_path.name
        shutil.copy2(complete_path, deployed_file)
        
        # Log deployment
        self._log_processing(complete_path.name, 'deployed', 0, deployed_file)
        
        print(f"✓ Deployed to production → {deployed_file}")
        
        return str(deployed_file)
    
    def _process_xml_source(self, source_path: Path, custom_template: Optional[str]) -> tuple:
        """Process XML source file using CCELThMLProcessor's robust XML handling."""
        
        # Use custom template if provided
        if custom_template and Path(custom_template).exists():
            # Load and apply custom processing template
            pass
        
        # Standard XML processing using robust XML cleaning
        processor = CCELThMLProcessor()
        
        
        # Read XML file
        try:
            with open(source_path, 'r', encoding='utf-8') as f:
                xml_content = f.read()
        except Exception as e:
            raise ValueError(f"Failed to read XML file {source_path}: {e}")
        
        # Extract body and head BEFORE cleaning to avoid issues with malformed head section
        import re
        body_match = re.search(r'<ThML\.body>(.*?)</ThML\.body>', xml_content, re.DOTALL)
        head_match = re.search(r'<ThML\.head>(.*?)</ThML\.head>', xml_content, re.DOTALL)
        
        if body_match and head_match:
            # Extract and clean head content
            head_content = head_match.group(1)
            body_content = body_match.group(1)
            
            # Clean head content - remove problematic tags
            head_content = re.sub(r'<style[^>]*>.*?</style>', '', head_content, flags=re.DOTALL)
            head_content = re.sub(r'<style[^>]*>', '', head_content)
            head_content = re.sub(r'</style>', '', head_content)
            head_content = re.sub(r'<script[^>]*>.*?</script>', '', head_content, flags=re.DOTALL)
            
            # Clean body content
            body_content = re.sub(r'<pb[^>]*/?>', '', body_content)
            body_content = re.sub(r'<br\s*/?>', '<br/>', body_content)
            
            # Fix ampersands in both
            head_content = re.sub(r'&(amp|lt|gt|quot|apos|nbsp);', '___ENTITY_\1___', head_content)
            head_content = head_content.replace('&', '&amp;')
            head_content = re.sub(r'___ENTITY_(\w+)___', r'&\1;', head_content)
            head_content = head_content.replace('&nbsp;', ' ')
            
            body_content = re.sub(r'&(amp|lt|gt|quot|apos|nbsp);', '___ENTITY_\1___', body_content)
            body_content = body_content.replace('&', '&amp;')
            body_content = re.sub(r'___ENTITY_(\w+)___', r'&\1;', body_content)
            body_content = body_content.replace('&nbsp;', ' ')
            
            # Reconstruct clean XML
            xml_content = f"""<ThML>
<ThML.head>
{head_content}
</ThML.head>
<ThML.body>
{body_content}
</ThML.body>
</ThML>"""
        else:
            # Fallback: clean the whole XML as before
            xml_content = re.sub(r'<\?xml[^>]*\?>', '', xml_content)
            xml_content = re.sub(r'<!DOCTYPE[^>]*>', '', xml_content)
            xml_content = re.sub(r'<!--.*?-->', '', xml_content, flags=re.DOTALL)
            xml_content = re.sub(r'<style[^>]*>.*?</style>', '', xml_content, flags=re.DOTALL)
            xml_content = re.sub(r'<style[^>]*>', '', xml_content)
            xml_content = re.sub(r'</style>', '', xml_content)
            xml_content = re.sub(r'<pb[^>]*/?>', '', xml_content)
            xml_content = re.sub(r'<br\s*/?>', '<br/>', xml_content)
            xml_content = re.sub(r'&(amp|lt|gt|quot|apos|nbsp);', '___ENTITY_\1___', xml_content)
            xml_content = xml_content.replace('&', '&amp;')
            xml_content = re.sub(r'___ENTITY_(\w+)___', r'&\1;', xml_content)
            xml_content = xml_content.replace('&nbsp;', ' ')
        
        # Parse the cleaned XML
        try:
            root = ET.fromstring(xml_content)
        except ET.ParseError as e:
            raise ValueError(f"Failed to parse XML file {source_path} after cleaning: {e}")
        
        # Extract metadata
        try:
            source_metadata = self.metadata_manager.extract_from_ccel_xml(root)
        except Exception as e:
            raise ValueError(f"Failed to extract metadata from XML: {e}")
        
        # Detect if we need the enhanced processor for nested structures (e.g., Confessions)
        # Check by source title or filename
        source_title = source_metadata.identification.title.lower()
        filename_lower = source_path.name.lower()
        needs_enhanced_processor = (
            'confession' in source_title or 
            'confession' in filename_lower or
            source_path.stem.lower() == 'confessions'
        )
        
        # Use enhanced processor if available and needed
        if needs_enhanced_processor and CONFESSIONS_PROCESSOR_AVAILABLE:
            print(f"Detected nested structure (Books > Chapters), using enhanced processor...")
            processor = ConfessionsProcessor()
        else:
            processor = CCELThMLProcessor()
        
        # Process sections and create chunks
        try:
            sections = processor.process_div1_sections(root)
            chunks = []
            
            for section in sections:
                section_chunks = processor.chunk_text(section['full_text'])
                structure_path = processor.build_structure_path(section['title'], section['headings'])
                
                for chunk_text in section_chunks:
                    if len(chunk_text.strip()) > 100:
                        chunks.append({
                            'text': chunk_text,
                            'structure_path': [structure_path] if structure_path else []
                        })
        except Exception as e:
            raise ValueError(f"Failed to process XML sections: {e}")
        
        return chunks, source_metadata
    
    def _clean_xml_content(self, xml_content: str) -> str:
        """Clean XML content similar to CCELThMLProcessor with robust error handling."""
        import re
        
        # Remove XML processing instructions and DOCTYPE
        xml_content = re.sub(r'<\?xml[^>]*\?>', '', xml_content)
        xml_content = re.sub(r'<!DOCTYPE[^>]*>', '', xml_content)
        xml_content = re.sub(r'<!--.*?-->', '', xml_content, flags=re.DOTALL)
        
        # Remove style elements which often contain problematic content
        xml_content = re.sub(r'<style[^>]*>.*?</style>', '', xml_content, flags=re.DOTALL)
        
        # Handle problematic elements
        xml_content = re.sub(r'<pb[^>]*/?>', '', xml_content)  # Remove page breaks
        xml_content = re.sub(r'<br\s*/?>', '<br/>', xml_content)  # Fix br tags
        
        # Fix ampersands that aren't part of entities
        # First, protect existing entities
        xml_content = re.sub(r'&(amp|lt|gt|quot|apos|nbsp);', '___ENTITY_\1___', xml_content)
        # Then escape remaining ampersands
        xml_content = xml_content.replace('&', '&amp;')
        # Restore protected entities
        xml_content = re.sub(r'___ENTITY_(\w+)___', r'&\1;', xml_content)
        
        # Handle common HTML entities that might not be defined
        xml_content = xml_content.replace('&nbsp;', ' ')
        
        return xml_content
    
    def _process_pdf_source(self, source_path: Path, custom_template: Optional[str]) -> tuple:
        """Process PDF source file.
        
        Note: This feature is not yet implemented. 
        Consider using external tools like PyPDF2 or pdfplumber for PDF processing.
        """
        raise NotImplementedError("PDF processing not yet implemented. Use external PDF tools first.")
    
    def _process_docx_source(self, source_path: Path, custom_template: Optional[str]) -> tuple:
        """Process DOCX source file.
        
        Note: This feature is not yet implemented.
        Consider using python-docx library for DOCX processing.
        """
        raise NotImplementedError("DOCX processing not yet implemented. Use python-docx library first.")
    
    def _load_indexes(self) -> Dict[str, Any]:
        """Load all index files needed for annotation."""
        indexes = {
            'concepts': [],
            'discourse_elements': [],
            'topics': [],
            'terms': []
        }
        
        base_dir = Path(__file__).parent
        
        # Load Concepts Index
        concepts_file = base_dir / 'Index: Concepts.md'
        if concepts_file.exists():
            with open(concepts_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('- [[') and 'Concept/' in line:
                        # Extract concept name
                        match = re.search(r'\[\[Concept/([^\]]+)\]\]', line)
                        if match:
                            indexes['concepts'].append(match.group(1))
        
        # Store as set for quick lookup during validation
        indexes['concepts_set'] = set(indexes['concepts']) if indexes['concepts'] else set()
        
        # Load Discourse Elements (Function index)
        function_file = base_dir / 'Index: Function.md'
        if function_file.exists():
            with open(function_file, 'r', encoding='utf-8') as f:
                content = f.read()
                # Extract all discourse elements in [[Category/Element]] format
                pattern = r'\[\[([^/]+)/([^\]]+)\]\]'
                matches = re.findall(pattern, content)
                for category, element in matches:
                    full_name = f"{category}/{element}"
                    indexes['discourse_elements'].append(full_name)
        
        # Store as set for quick lookup during validation (always initialize even if file missing)
        indexes['discourse_elements_set'] = set(indexes['discourse_elements']) if indexes['discourse_elements'] else set()
        
        # Load Topics and Terms (if they exist and have content)
        topics_file = base_dir / 'Index: Topics.md'
        if topics_file.exists():
            with open(topics_file, 'r', encoding='utf-8') as f:
                content = f.read()
                if len(content.strip()) > 10:  # Has meaningful content
                    indexes['topics'] = content
        
        terms_file = base_dir / 'Index: Terms.md'
        if terms_file.exists():
            with open(terms_file, 'r', encoding='utf-8') as f:
                content = f.read()
                if len(content.strip()) > 10:  # Has meaningful content
                    indexes['terms'] = content
        
        return indexes
    
    def _build_annotation_prompt(self, chunk_text: str, chunk_structure_path: List[str], indexes: Dict[str, Any], source_metadata: Optional[Dict] = None) -> str:
        """Build the annotation prompt for a single chunk."""
        
        # Convert structure_path from array to breadcrumb format
        structure_path_str = ""
        if chunk_structure_path and len(chunk_structure_path) > 0:
            # Join array elements into breadcrumb format
            path_text = chunk_structure_path[0] if isinstance(chunk_structure_path, list) else str(chunk_structure_path)
            structure_path_str = f"[[{path_text}]]" if path_text else ""
        
        # Get ALL concepts for prompt (they are fixed, so AI needs to see them all)
        concepts_list = ', '.join([f'[[Concept/{c}]]' for c in indexes['concepts']])
        
        # Get all discourse elements for prompt (grouped by category)
        discourse_elements_by_category = {}
        for de in indexes['discourse_elements']:
            category, element = de.split('/', 1)
            if category not in discourse_elements_by_category:
                discourse_elements_by_category[category] = []
            discourse_elements_by_category[category].append(element)
        
        discourse_elements_list = ""
        for category in ['Semantic', 'Logical', 'Narrative', 'Personal', 'Practical', 'Symbolic', 'Reference', 'Structural']:
            if category in discourse_elements_by_category:
                elements = [f'[[{category}/{e}]]' for e in discourse_elements_by_category[category]]
                discourse_elements_list += f"\n{category}: {', '.join(elements)}"
        
        prompt = f"""You are helping to create high-quality metadata for theological text chunks to improve RAG (Retrieval Augmented Generation) performance. Your task is to analyze a text chunk and provide structured metadata following specific guidelines.

## Text Chunk
{chunk_text}

## Current Structure Path
{structure_path_str if structure_path_str else "(to be determined)"}

## Metadata Structure
For this chunk, provide metadata in this exact format:
* concepts:: [[Concept/Concept1]], [[Concept/Concept2]]
* topics:: [[Concept1/Topic1]], [[Concept2/Topic2]]
* terms:: [[Concept1/Term1]], [[Concept2/Term2]]
* discourse-elements::
  * [[Category/Element]] Description or quote
  * [[Category/Element]] Description or quote
* scripture-references:: [Bible references if any, standardized format]
* structure-path:: {structure_path_str if structure_path_str else "Breadcrumb format (e.g. [[Section > Subsection]])"}
* named-entities:: [[Person/Entity]], [[Place/Entity]], [[Event/Entity]], [[Ideology/Entity]], [[Period/Entity]], [[Work/Entity]], [[Group/Entity]]

## Critical Constraints

### Concepts Index (Fixed)
Use ONLY concepts from this EXACT list (NO additions allowed, NO substitutions):
{concepts_list}

**CRITICAL**: You must use concepts from the list above. If a concept is not in the list, do NOT use it. Better to leave blank than use an invalid concept.

Usually 1-3 concepts per chunk.

### Topics Index (Flexible)
When assigning topics under selected concepts, focus on **questions, issues, aspects, or debates** rather than simple subtopics. Topics must use namespaced format: `[[Concept/Topic]]`

Examples:
- Under "Authority": `[[Authority/Scripture vs Tradition]]`, `[[Authority/Papal Infallibility]]`
- Under "Salvation": `[[Salvation/Faith vs Works]]`, `[[Salvation/Universal vs Particular]]`

### Term Index (Flexible)
Select 3-5 terms that relate to the concepts assigned to this chunk. **Terms MUST use namespaced format: `[[Concept/Term]]`** and must be related to one of the concepts you've assigned above.

**CRITICAL**: Terms must use namespaced format `[[Concept/Term]]` where "Concept" is one of the concepts you assigned above. If you assign concepts like "Faith" and "Salvation", your terms must be formatted as `[[Faith/term]]` or `[[Salvation/term]]`, NOT as unnamespaced terms.

Terms should represent how readers would search for this content and include:
- Synonyms and variant expressions
- Familiar and colloquial expressions
- Poetic and literary language
- Technical and scholarly terms
- Memorable phrases

Examples:
- If you assigned "Faith" and "Salvation" as concepts:
  - `[[Faith/christian faith]]`, `[[Faith/personal conviction]]`, `[[Salvation/grace]]`, `[[Faith/belief]]`
  - NOT: `faith`, `christian faith`, `personal conviction` (unnamespaced)

**IMPORTANT**: 
- Only create terms that relate to the concepts you've assigned to this chunk
- Terms MUST follow the `[[Concept/Term]]` format - this is required, not optional
- Every term must be namespaced with one of your assigned concepts

### Discourse Elements (Fixed)
Use ONLY elements from this EXACT list (NO additions allowed, NO substitutions):
{discourse_elements_list}

Format each as: `[[Category/Element]]` followed by a description or quote.

**CRITICAL**: If none of these elements fit, use the closest match. Do NOT create new discourse elements like "Narrative/Hypothetical Scenario" or "Personal/Emotional Response" - use the fixed elements from the list above.

Every chunk must have at least one discourse element. Typically 3-5 per chunk.

### Scripture References (Fixed)
Only add if a verse, chapter, or book is mentioned. Normalize format: "John 3:16" becomes [[John 3]] and [[John 3:16]].

### Structure Path (Flexible)
{('Use the provided structure path: ' + structure_path_str if structure_path_str else 'Determine the hierarchical location in breadcrumb format: [[Section > Subsection]]')}

### Named Entities (Class Fixed, Entity Flexible)
Use namespaced format: `[[Class/Entity]]`
Classes: Person, Place, Event, Group, Work, Period, Ideology

## Output Format
Provide your response in this exact format (no additional explanation):

concepts:: [[Concept/Concept1]], [[Concept/Concept2]]
topics:: [[Concept1/Topic1]], [[Concept2/Topic2]]
terms:: [[Concept1/Term1]], [[Concept2/Term2]]
discourse-elements::
* [[Category/Element]] Description
* [[Category/Element]] Description
scripture-references:: [[Book Chapter:Verse]] (if any)
structure-path:: [[Section > Subsection]]
named-entities:: [[Person/Name]], [[Work/Title]] (if any)"""
        
        return prompt
    
    def _parse_annotation_response(self, response_text: str, valid_discourse_elements: Optional[set] = None, valid_concepts: Optional[set] = None) -> Dict[str, Any]:
        """Parse the AI response into structured metadata."""
        metadata = {
            'concepts': [],
            'topics': [],
            'terms': [],
            'discourse_elements': [],
            'scripture_references': [],
            'structure_path': '',
            'named_entities': []
        }
        
        # Extract concepts
        concepts_match = re.search(r'concepts::\s*(.+)', response_text, re.IGNORECASE | re.MULTILINE)
        if concepts_match:
            concepts_str = concepts_match.group(1).strip()
            # Try both formats: [[Concept/Name]] and [[Name]] (fallback)
            extracted_concepts = re.findall(r'\[\[Concept/([^\]]+)\]\]', concepts_str)
            if not extracted_concepts:
                # Fallback: try without Concept/ prefix
                extracted_concepts = re.findall(r'\[\[([^\]]+)\]\]', concepts_str)
            # Validate against fixed list
            if valid_concepts is None:
                # Fallback: load if not provided
                valid_concepts = self._load_indexes().get('concepts_set', set())
            # Only keep concepts that are in the fixed list
            metadata['concepts'] = [c for c in extracted_concepts if c in valid_concepts]
        
        # Fallback: If no concepts found, derive from topics and terms
        if not metadata['concepts']:
            derived_concepts = set()
            # Extract concepts from topics (format: Concept/Topic)
            for topic in metadata.get('topics', []):
                if '/' in topic:
                    concept = topic.split('/', 1)[0]
                    if valid_concepts and concept in valid_concepts:
                        derived_concepts.add(concept)
            # Extract concepts from terms (format: Concept/Term)
            for term in metadata.get('terms', []):
                if '/' in term:
                    concept = term.split('/', 1)[0]
                    if valid_concepts and concept in valid_concepts:
                        derived_concepts.add(concept)
            
            if derived_concepts:
                metadata['concepts'] = list(derived_concepts)
        
        # Extract topics
        topics_match = re.search(r'topics::\s*(.+)', response_text, re.IGNORECASE | re.MULTILINE)
        if topics_match:
            topics_str = topics_match.group(1).strip()
            metadata['topics'] = re.findall(r'\[\[([^\]]+)\]\]', topics_str)
        
        # Extract terms
        terms_match = re.search(r'terms::\s*(.+)', response_text, re.IGNORECASE | re.MULTILINE)
        if terms_match:
            terms_str = terms_match.group(1).strip()
            metadata['terms'] = re.findall(r'\[\[([^\]]+)\]\]', terms_str)
        
        # Extract discourse elements
        discourse_match = re.search(r'discourse-elements::\s*(.+?)(?=\n\w+::|\Z)', response_text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
        if discourse_match:
            discourse_text = discourse_match.group(1)
            # Extract each element with its description
            lines = discourse_text.split('\n')
            if valid_discourse_elements is None:
                # Fallback: load if not provided
                valid_discourse_elements = self._load_indexes().get('discourse_elements_set', set())
            for line in lines:
                line = line.strip()
                if line.startswith('*') or line.startswith('-'):
                    line = line.lstrip('*-').strip()
                    element_match = re.search(r'\[\[([^\]]+)\]\]\s*(.+)', line)
                    if element_match:
                        element_full = element_match.group(1)
                        # Validate against fixed list
                        if element_full in valid_discourse_elements:
                            desc = element_match.group(2).strip()
                            metadata['discourse_elements'].append(f"[[{element_full}]] {desc}")
                        # If invalid, skip it (don't add to metadata)
        
        # Extract scripture references - stop at next field (structure-path, named-entities, or any new field)
        # Use non-greedy match that stops at next field or end of string
        scripture_match = re.search(r'scripture-references::\s*(.+?)(?=\n(?:structure-path|named-entities|\w+)::|\Z)', response_text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
        if scripture_match:
            scripture_str = scripture_match.group(1).strip()
            if scripture_str and scripture_str.lower() not in ['none', 'n/a', '']:
                # Only extract if it looks like a Bible reference (contains book names or chapter/verse patterns)
                refs = re.findall(r'\[\[([^\]]+)\]\]', scripture_str)
                # Basic validation: check if it contains Bible book names or chapter/verse patterns
                # This will filter out structure_path content that got misclassified
                bible_books = ['genesis', 'exodus', 'leviticus', 'numbers', 'deuteronomy', 'joshua', 'judges', 'ruth', 
                              'samuel', 'kings', 'chronicles', 'ezra', 'nehemiah', 'esther', 'job', 'psalm', 'psalms',
                              'proverbs', 'ecclesiastes', 'song', 'isaiah', 'jeremiah', 'lamentations', 'ezekiel',
                              'daniel', 'hosea', 'joel', 'amos', 'obadiah', 'jonah', 'micah', 'nahum', 'habakkuk',
                              'zephaniah', 'haggai', 'zechariah', 'malachi', 'matthew', 'mark', 'luke', 'john',
                              'acts', 'romans', 'corinthians', 'galatians', 'ephesians', 'philippians', 'colossians',
                              'thessalonians', 'timothy', 'titus', 'philemon', 'hebrews', 'james', 'peter', 'jude', 'revelation']
                validated_refs = []
                for ref in refs:
                    ref_lower = ref.lower()
                    # Check if it contains a book name or chapter/verse pattern
                    # Also check that it doesn't look like a structure path (contains > or chapter/roman numerals pattern)
                    is_structure_path = '>' in ref or re.search(r'\bchapter\s+[ivxlcdm]+\b', ref_lower) or re.search(r'\b(chapter|part|section)\s+[ivxlcdm]+', ref_lower)
                    if not is_structure_path and (any(book in ref_lower for book in bible_books) or re.search(r'\d+:\d+|\d+\s+', ref)):
                        validated_refs.append(ref)
                metadata['scripture_references'] = validated_refs
        
        # Extract structure path
        structure_match = re.search(r'structure-path::\s*(.+)', response_text, re.IGNORECASE | re.MULTILINE)
        if structure_match:
            structure_str = structure_match.group(1).strip()
            if structure_str:
                # Remove surrounding brackets if present
                structure_str = re.sub(r'^\[\[', '', structure_str)
                structure_str = re.sub(r'\]\]$', '', structure_str)
                metadata['structure_path'] = structure_str
        
        # Extract named entities
        entities_match = re.search(r'named-entities::\s*(.+)', response_text, re.IGNORECASE | re.MULTILINE)
        if entities_match:
            entities_str = entities_match.group(1).strip()
            if entities_str and entities_str.lower() not in ['none', 'n/a', '']:
                metadata['named_entities'] = re.findall(r'\[\[([^\]]+)\]\]', entities_str)
        
        return metadata
    
    def _annotate_chunks_with_ai(self, chunks: List[Dict], metadata_file: Path) -> List[Dict]:
        """Annotate chunks using Anthropic Claude API."""
        import anthropic
        import os
        from dotenv import load_dotenv
        
        # Load environment variables from .env file
        load_dotenv()
        
        # Check for API key
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not found. Please set it in your .env file or as an environment variable.")
        
        # Initialize Anthropic client
        client = anthropic.Anthropic(api_key=api_key)
        
        # Load indexes
        print("Loading index files...")
        indexes = self._load_indexes()
        print(f"  ✓ Loaded {len(indexes['concepts'])} concepts")
        print(f"  ✓ Loaded {len(indexes['discourse_elements'])} discourse elements")
        
        # Load source metadata if available
        source_metadata = None
        if metadata_file.exists():
            # You might want to parse YAML here if needed
            pass
        
        annotated_chunks = []
        total_chunks = len(chunks)
        
        print(f"\nAnnotating {total_chunks} chunks using Anthropic Claude API...")
        print("(This may take several minutes and incur API costs)\n")
        
        for idx, chunk in enumerate(chunks, 1):
            chunk_text = chunk.get('text', '')
            chunk_structure_path = chunk.get('structure_path', [])
            
            if not chunk_text:
                print(f"⚠️  Skipping chunk {idx}: empty text")
                annotated_chunks.append(chunk.copy())
                continue
            
            try:
                # Build prompt
                prompt = self._build_annotation_prompt(chunk_text, chunk_structure_path, indexes, source_metadata)
                
                # Call Anthropic API
                message = client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=4000,
                    temperature=0.3,
                    messages=[{
                        "role": "user",
                        "content": prompt
                    }]
                )
                
                # Parse response
                response_text = message.content[0].text
                metadata = self._parse_annotation_response(
                    response_text, 
                    valid_discourse_elements=indexes['discourse_elements_set'],
                    valid_concepts=indexes['concepts_set']
                )
                
                # Create annotated chunk
                annotated_chunk = chunk.copy()
                
                # Remove the top-level structure_path since it will be in metadata
                # (it was only there during the chunking stage for reference)
                if 'structure_path' in annotated_chunk:
                    del annotated_chunk['structure_path']
                
                # Convert structure_path from array to string format
                structure_path_str = ""
                if chunk_structure_path and len(chunk_structure_path) > 0:
                    path_text = chunk_structure_path[0] if isinstance(chunk_structure_path, list) else str(chunk_structure_path)
                    structure_path_str = f"[[{path_text}]]"
                elif metadata.get('structure_path'):
                    structure_path_str = f"[[{metadata['structure_path']}]]"
                
                annotated_chunk.update({
                    'metadata': {
                        'concepts': metadata['concepts'],
                        'topics': metadata['topics'],
                        'terms': metadata['terms'],
                        'discourse_elements': metadata['discourse_elements'],
                        'scripture_references': metadata['scripture_references'],
                        'structure_path': structure_path_str,
                        'named_entities': metadata['named_entities']
                    },
                    'processing_stage': 'annotated',
                    'annotation_method': 'anthropic_claude',
                    'annotation_model': 'claude-sonnet-4-20250514',
                    'processing_timestamp': datetime.now().isoformat()
                })
                
                annotated_chunks.append(annotated_chunk)
                
                # Progress indicator
                if idx % 10 == 0 or idx == total_chunks:
                    print(f"  ✓ Annotated {idx}/{total_chunks} chunks")
                
            except Exception as e:
                print(f"⚠️  Error annotating chunk {idx}: {e}")
                # Add chunk with empty metadata on error
                annotated_chunk = chunk.copy()
                # Remove the top-level structure_path since it will be in metadata
                if 'structure_path' in annotated_chunk:
                    del annotated_chunk['structure_path']
                
                # Convert structure_path from array to string format for metadata
                structure_path_str = ""
                if chunk_structure_path and len(chunk_structure_path) > 0:
                    path_text = chunk_structure_path[0] if isinstance(chunk_structure_path, list) else str(chunk_structure_path)
                    structure_path_str = f"[[{path_text}]]"
                
                annotated_chunk.update({
                    'metadata': {
                        'concepts': [],
                        'topics': [],
                        'terms': [],
                        'discourse_elements': [],
                        'scripture_references': [],
                        'structure_path': structure_path_str,
                        'named_entities': []
                    },
                    'processing_stage': 'annotated',
                    'annotation_method': 'anthropic_claude_failed',
                    'annotation_error': str(e),
                    'processing_timestamp': datetime.now().isoformat()
                })
                annotated_chunks.append(annotated_chunk)
        
        print(f"\n✓ Completed annotation of {total_chunks} chunks")
        return annotated_chunks
    
    def _create_annotation_template(self, chunks: List[Dict], metadata_file: Path) -> List[Dict]:
        """Create annotation template for manual completion."""
        annotated_chunks = []
        
        for chunk in chunks:
            annotated_chunk = chunk.copy()
            annotated_chunk.update({
                'metadata': {
                    'concepts': ["# TODO: Add concepts from fixed index"],
                    'topics': ["# TODO: Add topics in [[Concept/Topic]] format"],
                    'terms': ["# TODO: Add discoverable terms"],
                    'discourse_elements': ["# TODO: Add [[Category/Element]] Description"],
                    'scripture_references': ["# TODO: Add Bible references if any"],
                    'named_entities': ["# TODO: Add [[Class/Entity]] format"]
                },
                'processing_stage': 'annotated',
                'annotation_method': 'manual_pending',
                'processing_timestamp': datetime.now().isoformat()
            })
            annotated_chunks.append(annotated_chunk)
        
        return annotated_chunks
    
    def _add_embeddings(self, chunks: List[Dict], embedding_model: str = 'openai') -> List[Dict]:
        """Add vector embeddings to chunks using OpenAI API.
        
        Only the 'text' field of each chunk is embedded, not metadata or other fields.
        
        embedding_model: 'openai' (uses text-embedding-3-small) or model name
        """
        from openai import OpenAI
        import os
        from dotenv import load_dotenv
        import time
        
        # Load environment variables
        load_dotenv()
        
        # Check for API key
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found. Please set it in your .env file or as an environment variable.")
        
        # Initialize OpenAI client
        client = OpenAI(api_key=api_key)
        
        # Determine model name
        if embedding_model == 'openai':
            model_name = 'text-embedding-3-small'
        else:
            model_name = embedding_model
        
        complete_chunks = []
        total_chunks = len(chunks)
        
        print(f"\nGenerating embeddings for {total_chunks} chunks using {model_name}...")
        print("(Only embedding the 'text' field of each chunk)")
        print("(This may take several minutes and incur API costs)\n")
        
        for idx, chunk in enumerate(chunks, 1):
            complete_chunk = chunk.copy()
            chunk_text = chunk.get('text', '')
            
            if not chunk_text:
                print(f"⚠️  Skipping chunk {idx}: empty text")
                complete_chunk.update({
                    'embedding': None,
                    'processing_stage': 'complete',
                    'embedding_model': model_name,
                    'embedding_error': 'empty_text',
                    'processing_timestamp': datetime.now().isoformat()
                })
                complete_chunks.append(complete_chunk)
                continue
            
            try:
                # Get embedding from OpenAI - ONLY embedding the text field
                response = client.embeddings.create(
                    model=model_name,
                    input=chunk_text
                )
                embedding = response.data[0].embedding
                
                complete_chunk.update({
                    'embedding': embedding,
                    'processing_stage': 'complete',
                    'embedding_model': model_name,
                    'processing_timestamp': datetime.now().isoformat()
                })
                complete_chunks.append(complete_chunk)
                
                # Progress indicator
                if idx % 10 == 0 or idx == total_chunks:
                    print(f"  ✓ Generated embeddings for {idx}/{total_chunks} chunks")
                
                # Rate limiting - small delay every 100 requests to avoid hitting limits
                if idx % 100 == 0:
                    time.sleep(1)
                    
            except Exception as e:
                print(f"⚠️  Error generating embedding for chunk {idx}: {e}")
                complete_chunk.update({
                    'embedding': None,
                    'processing_stage': 'complete',
                    'embedding_model': model_name,
                    'embedding_error': str(e),
                    'processing_timestamp': datetime.now().isoformat()
                })
                complete_chunks.append(complete_chunk)
        
        print(f"\n✓ Completed embedding generation for {total_chunks} chunks")
        return complete_chunks
    
    def _is_human_approved(self, file_path: Path) -> bool:
        """Check if file has been human-approved for next stage."""
        approval_file = Path(str(file_path) + '.approved')
        return approval_file.exists()
    
    def _save_jsonl(self, data: List[Dict], output_file: Path):
        """Save data as JSONL file."""
        with open(output_file, 'w', encoding='utf-8') as f:
            for item in data:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')
    
    def _load_jsonl(self, file_path: Path) -> List[Dict]:
        """Load JSONL file."""
        data = []
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    data.append(json.loads(line))
        return data
    
    def _log_processing(self, source_file: str, stage: str, chunk_count: int, output_file: Path):
        """Log processing step."""
        log_file = self.base_dir / 'logs' / 'processing.log'
        timestamp = datetime.now().isoformat()
        log_entry = f"{timestamp} | {stage.upper()} | {source_file} → {chunk_count} chunks → {output_file.name}\n"
        
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry)
    
    def status_report(self) -> Dict[str, int]:
        """Generate processing status report."""
        status = {}
        
        for stage_name, stage in self.stages.items():
            folder = self.base_dir / stage.input_folder
            if folder.exists():
                jsonl_files = list(folder.glob('*.jsonl'))
                xml_files = list(folder.glob('*.xml'))
                pdf_files = list(folder.glob('*.pdf'))
                all_files = jsonl_files + xml_files + pdf_files
                
                status[stage_name] = {
                    'total_files': len(all_files),
                    'approved_files': len([f for f in all_files if Path(str(f) + '.approved').exists()]),
                    'pending_review': len([f for f in all_files if not Path(str(f) + '.approved').exists()])
                }
        
        return status
    
    def list_pending_reviews(self):
        """List files that need human review."""
        print("\n=== FILES PENDING HUMAN REVIEW ===")
        
        # Check chunked files (need chunk review)
        chunked_folder = self.base_dir / '02_chunked'
        for jsonl_file in chunked_folder.glob('*.jsonl'):
            if not self._is_human_approved(jsonl_file):
                print(f"📝 CHUNK REVIEW: {jsonl_file.name}")
                print(f"   → Review chunks and run: touch {jsonl_file}.approved")
        
        # Check annotated files (need annotation review)  
        annotated_folder = self.base_dir / '03_annotated'
        for jsonl_file in annotated_folder.glob('*.jsonl'):
            if not self._is_human_approved(jsonl_file):
                print(f"🏷️  ANNOTATION REVIEW: {jsonl_file.name}")
                print(f"   → Review annotations and run: touch {jsonl_file}.approved")


def main():
    parser = argparse.ArgumentParser(description='Staged Theological Text Processing Pipeline')
    parser.add_argument('--stage', choices=['chunk', 'annotate', 'vectorize', 'deploy', 'status'], 
                       required=True, help='Processing stage to run')
    parser.add_argument('--source', help='Source file to process')
    parser.add_argument('--annotation-method', choices=['ai', 'manual'], default='ai',
                       help='Annotation method (default: ai)')
    parser.add_argument('--base-dir', default='./theological_processing',
                       help='Base processing directory')
    
    args = parser.parse_args()
    
    pipeline = TheologicalProcessingPipeline(args.base_dir)
    
    if args.stage == 'status':
        status = pipeline.status_report()
        print("\n=== PROCESSING PIPELINE STATUS ===")
        for stage, counts in status.items():
            print(f"{stage.upper()}: {counts['total_files']} files "
                  f"({counts['approved_files']} approved, {counts['pending_review']} pending)")
        
        pipeline.list_pending_reviews()
    
    elif args.stage == 'chunk':
        if not args.source:
            print("Error: --source required for chunking stage")
            return
        
        output_file = pipeline.process_stage_1_to_chunks(args.source)
        print(f"\nNext steps:")
        print(f"1. Review chunks in: {output_file}")
        print(f"2. When satisfied, approve: touch {output_file}.approved")
        print(f"3. Then run: python pipeline_manager.py --stage annotate --source {Path(output_file).name}")
    
    elif args.stage == 'annotate':
        if not args.source:
            print("Error: --source required for annotation stage")
            return
        
        output_file = pipeline.process_stage_2_to_annotated(args.source, args.annotation_method)
        if output_file:
            print(f"\nNext steps:")
            print(f"1. Review annotations in: {output_file}")
            print(f"2. When satisfied, approve: touch {output_file}.approved")
            print(f"3. Then run: python pipeline_manager.py --stage vectorize --source {Path(output_file).name}")
    
    elif args.stage == 'vectorize':
        if not args.source:
            print("Error: --source required for vectorization stage")
            return
        
        output_file = pipeline.process_stage_3_to_complete(args.source)
        if output_file:
            print(f"\nNext steps:")
            print(f"1. Complete file ready: {output_file}")
            print(f"2. Deploy to production: python pipeline_manager.py --stage deploy --source {Path(output_file).name}")
    
    elif args.stage == 'deploy':
        if not args.source:
            print("Error: --source required for deployment stage")
            return
        
        output_file = pipeline.process_stage_4_to_deployed(args.source)
        if output_file:
            print(f"\n✓ Successfully deployed to production: {output_file}")


if __name__ == '__main__':
    main()