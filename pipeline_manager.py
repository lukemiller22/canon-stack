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
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import argparse

from source_metadata_manager import SourceMetadataManager
from ccel_xml_to_markdown import CCELThMLProcessor


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
    
    def _annotate_chunks_with_ai(self, chunks: List[Dict], metadata_file: Path) -> List[Dict]:
        """Annotate chunks using AI (LLM).
        
        Note: This is a placeholder implementation. 
        To implement actual AI annotation, integrate with your LLM service
        and use the theological annotation prompt from README.md.
        """
        annotated_chunks = []
        
        for chunk in chunks:
            # Create chunk with annotation placeholder
            annotated_chunk = chunk.copy()
            annotated_chunk.update({
                'metadata': {
                    'concepts': [],
                    'topics': [],
                    'terms': [],
                    'discourse_elements': [],
                    'scripture_references': [],
                    'named_entities': []
                },
                'processing_stage': 'annotated',
                'annotation_method': 'ai_pending',
                'processing_timestamp': datetime.now().isoformat()
            })
            annotated_chunks.append(annotated_chunk)
        
        # TODO: Implement actual AI annotation using your prompt
        print("⚠️  AI annotation not yet implemented - creating template")
        
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
    
    def _add_embeddings(self, chunks: List[Dict], embedding_model: str) -> List[Dict]:
        """Add vector embeddings to chunks.
        
        Note: This is a placeholder implementation.
        To implement actual embedding generation, integrate with your embedding service
        (e.g., OpenAI embeddings, Cohere, or local models).
        """
        complete_chunks = []
        
        for chunk in chunks:
            complete_chunk = chunk.copy()
            
            # TODO: Implement actual embedding generation
            complete_chunk.update({
                'embedding': [0.0] * 1536,  # Placeholder for OpenAI embedding
                'processing_stage': 'complete',
                'embedding_model': embedding_model,
                'processing_timestamp': datetime.now().isoformat()
            })
            complete_chunks.append(complete_chunk)
        
        print("⚠️  Embedding generation not yet implemented - creating placeholder")
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
    parser.add_argument('--stage', choices=['chunk', 'annotate', 'vectorize', 'status'], 
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
            print(f"\nProcessing complete! Final file: {output_file}")


if __name__ == '__main__':
    main()