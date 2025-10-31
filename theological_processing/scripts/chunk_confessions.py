#!/usr/bin/env python3
"""
Enhanced CCEL ThML Processor for Confessions
Handles nested structure: div1 (Books) > div2 (Chapters)

This script extends the base CCELThMLProcessor to handle the nested
structure found in Augustine's Confessions, where Books contain Chapters.
"""

import sys
import os
from pathlib import Path
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional
import re

# Add parent directories to path to import base processor
# Script is in theological_processing/scripts/, need to go up 2 levels to root
script_dir = Path(__file__).parent
root_dir = script_dir.parent.parent
sys.path.insert(0, str(root_dir))

from ccel_xml_to_markdown import CCELThMLProcessor


class ConfessionsProcessor(CCELThMLProcessor):
    """
    Processor specifically for Augustine's Confessions.
    
    Handles nested structure:
    - div1 = Books (Book I, Book II, etc.)
    - div2 = Chapters within each Book (Chapter I, Chapter II, etc.)
    """
    
    def process_div1_sections(self, root: ET.Element) -> List[Dict]:
        """Process div1 sections, handling nested div2 chapters for Books."""
        body = root.find('.//ThML.body')
        if body is None:
            return []
        
        sections = []
        
        for div1 in body.findall('div1'):
            # Check if this div1 has nested div2 elements (chapters)
            div2_elements = div1.findall('div2')
            
            if div2_elements:
                # This is a Book with Chapters - process each chapter separately
                book_title = div1.get('title', '')
                book_id = div1.get('id', '')
                
                # Skip if it's the Contents table
                if book_title.lower() in ['contents', 'toc', 'table of contents']:
                    continue
                
                # Extract book-level headings
                book_headings = []
                for i in range(1, 7):
                    for heading in div1.findall(f'h{i}'):
                        heading_text = self.extract_text_content(heading)
                        if heading_text:
                            book_headings.append((i, self.clean_text(heading_text)))
                
                # Process each chapter (div2) within this book
                for div2 in div2_elements:
                    chapter_data = self.process_div2_as_section(
                        div2, 
                        parent_book_title=book_title,
                        parent_book_id=book_id,
                        parent_headings=book_headings
                    )
                    
                    if chapter_data:
                        sections.append(chapter_data)
                        if self.verbose:
                            print(f"Processing: {chapter_data['title']}")
            else:
                # No div2 elements - fall back to standard div1 processing
                # But still skip Contents
                title = div1.get('title', '')
                if title.lower() not in ['contents', 'toc', 'table of contents', 'title page']:
                    section_data = self.process_div1(div1)
                    if section_data:
                        sections.append(section_data)
        
        return sections
    
    def process_div2_as_section(
        self, 
        div2: ET.Element, 
        parent_book_title: str,
        parent_book_id: str,
        parent_headings: List[tuple]
    ) -> Optional[Dict]:
        """Process a div2 (Chapter) element within a div1 (Book)."""
        chapter_title = div2.get('title', '')
        chapter_id = div2.get('id', '')
        
        # Extract chapter-level headings
        chapter_headings = []
        for i in range(1, 7):
            for heading in div2.findall(f'h{i}'):
                heading_text = self.extract_text_content(heading)
                if heading_text:
                    chapter_headings.append((i, self.clean_text(heading_text)))
        
        # Extract paragraphs from this chapter
        paragraphs = []
        for p in div2.findall('p'):
            p_text = self.extract_text_content(p)
            if p_text:
                paragraphs.append(self.clean_text(p_text))
        
        # Also check for verse elements (poetry within prose)
        for verse in div2.findall('verse'):
            verse_text = self.extract_text_content(verse)
            if verse_text:
                # Add verse as a separate paragraph for clarity
                paragraphs.append(self.clean_text(verse_text))
        
        # Skip if no content
        if not paragraphs:
            if self.verbose:
                print(f"Skipping chapter with no content: {chapter_title}")
            return None
        
        # Build combined title: "Book I > Chapter I"
        full_title = f"{parent_book_title} > {chapter_title}"
        
        # Combine headings: book headings + chapter headings
        all_headings = parent_headings + chapter_headings
        
        return {
            'title': full_title,
            'id': chapter_id,
            'book_title': parent_book_title,
            'chapter_title': chapter_title,
            'headings': all_headings,
            'paragraphs': paragraphs,
            'full_text': '\n\n'.join(paragraphs)
        }
    
    def build_structure_path(self, div1_title: str, headings: List[tuple]) -> str:
        """Build hierarchical structure path, handling Book > Chapter format."""
        path_parts = []
        
        # If the title contains " > ", it's already in Book > Chapter format
        if ' > ' in div1_title:
            # Split and clean each part
            parts = div1_title.split(' > ')
            for part in parts:
                cleaned = part.strip()
                if cleaned:
                    path_parts.append(cleaned)
        else:
            # Standard processing for non-nested structures
            if div1_title:
                cleaned_title = div1_title.strip()
                # Clean up common chapter/section patterns
                if re.match(r'^[0-9]+$', cleaned_title):
                    cleaned_title = f"Chapter {cleaned_title}"
                elif re.match(r'^[ivxlc]+\.?$', cleaned_title.lower()):
                    cleaned_title = f"Chapter {cleaned_title.upper()}"
                elif cleaned_title.lower() in ['preface', 'foreword', 'introduction']:
                    cleaned_title = cleaned_title.capitalize()
                
                path_parts.append(cleaned_title)
        
        # Add meaningful headings (skip redundant ones)
        for level, heading_text in headings:
            cleaned_heading = heading_text.strip()
            
            # Skip if it's just repeating the title
            if div1_title and cleaned_heading.upper() in div1_title.upper():
                continue
            
            # Skip book titles
            if cleaned_heading.upper() in ['THE CONFESSIONS OF SAINT AUGUSTINE', 'CONFESSIONS']:
                continue
            
            # Add h1 and h2 level headings for structure
            if level <= 2:
                path_parts.append(cleaned_heading)
        
        return ' > '.join(path_parts) if path_parts else ''


if __name__ == '__main__':
    """Test the processor on confessions.xml"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Process Confessions XML with nested structure support')
    parser.add_argument('source_file', help='Path to confessions.xml')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    args = parser.parse_args()
    
    processor = ConfessionsProcessor()
    processor.verbose = args.verbose
    
    # Test processing
    source_path = Path(args.source_file)
    if not source_path.exists():
        print(f"Error: File not found: {source_path}")
        sys.exit(1)
    
    with open(source_path, 'r', encoding='utf-8') as f:
        xml_content = f.read()
    
    # Parse XML (simplified - actual pipeline uses more robust cleaning)
    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError as e:
        print(f"XML Parse Error: {e}")
        sys.exit(1)
    
    sections = processor.process_div1_sections(root)
    
    print(f"\nProcessed {len(sections)} sections")
    print(f"\nFirst few sections:")
    for i, section in enumerate(sections[:5]):
        print(f"{i+1}. {section['title']} ({len(section['paragraphs'])} paragraphs)")
        if section['paragraphs']:
            preview = section['paragraphs'][0][:100]
            print(f"   Preview: {preview}...")

