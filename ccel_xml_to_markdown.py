#!/usr/bin/env python3
"""
CCEL ThML to Markdown Converter

This script converts theological XML files from CCEL (ccel.org) using ThML format 
into the markdown format expected by the theological text metadata annotation prompt.

Usage:
    python ccel_xml_to_markdown.py input.xml output.md
    python ccel_xml_to_markdown.py https://ccel.org/ccel/c/chesterton/orthodoxy.xml orthodoxy.md
"""

import xml.etree.ElementTree as ET
import re
import sys
import requests
from pathlib import Path
import argparse
from typing import Dict, List, Optional
import urllib.parse


class CCELThMLProcessor:
    def __init__(self):
        self.source_metadata = {}
        self.chunks = []
        self.current_structure_path = []
        self.include_front_matter = False
        self.include_back_matter = False
        self.verbose = False
        
    def clean_text(self, text: str) -> str:
        """Clean and normalize text content."""
        if not text:
            return ""
        
        # Remove extra whitespace and normalize
        text = re.sub(r'\s+', ' ', text.strip())
        
        return text
    
    def extract_text_content(self, element: ET.Element) -> str:
        """Extract all text content from an element, handling nested elements."""
        text_parts = []
        
        # Get text before first child
        if element.text:
            text_parts.append(element.text)
        
        # Process all children
        for child in element:
            # Get text content of child (recursive)
            child_text = self.extract_text_content(child)
            if child_text:
                text_parts.append(child_text)
            
            # Get tail text after child
            if child.tail:
                text_parts.append(child.tail)
        
        return " ".join(text_parts)
    
    def extract_source_metadata(self, root: ET.Element) -> Dict[str, str]:
        """Extract source metadata from ThML head section."""
        metadata = {}
        
        # Extract from DC (Dublin Core) metadata in ThML.head
        dc_title = root.find('.//DC.Title')
        if dc_title is not None and dc_title.text:
            metadata['title'] = self.clean_text(dc_title.text)
        
        # Extract author from DC.Creator
        dc_creator = root.find('.//DC.Creator[@sub="Author"][@scheme="short-form"]')
        if dc_creator is not None and dc_creator.text:
            metadata['author'] = self.clean_text(dc_creator.text)
        elif root.find('.//DC.Creator[@sub="Author"]') is not None:
            # Fallback to any DC.Creator with Author sub
            author_elem = root.find('.//DC.Creator[@sub="Author"]')
            if author_elem.text:
                metadata['author'] = self.clean_text(author_elem.text)
        
        # Extract publication year from DC.Date
        dc_date = root.find('.//DC.Date')
        if dc_date is not None and dc_date.text:
            # Try to extract year from date
            date_text = dc_date.text
            year_match = re.search(r'\b(19|20)\d{2}\b', date_text)
            if year_match:
                metadata['publication_year'] = year_match.group(0)
        
        # Extract subjects/topics
        dc_subjects = root.findall('.//DC.Subject[@scheme="lcsh1"]')
        if dc_subjects:
            subjects = [self.clean_text(subj.text) for subj in dc_subjects if subj.text]
            metadata['subjects'] = subjects
        
        return metadata
    
    def process_div1_sections(self, root: ET.Element) -> List[Dict]:
        """Process div1 sections from ThML body into structured chunks."""
        body = root.find('.//ThML.body')
        if body is None:
            return []
        
        sections = []
        
        for div1 in body.findall('div1'):
            section_data = self.process_div1(div1)
            if section_data:
                if self.verbose:
                    print(f"Processing section: {section_data['title']} ({len(section_data['paragraphs'])} paragraphs)")
                sections.append(section_data)
        
        return sections
    
    def process_div1(self, div1: ET.Element) -> Optional[Dict]:
        """Process a single div1 section."""
        # Get section title and metadata
        title = div1.get('title', '')
        section_id = div1.get('id', '')
        
        # Skip front matter, back matter, and non-content sections
        front_matter_skip = {
            # Publisher/administrative content
            'title page', 'toc', 'table of contents', 'contents',
            'acknowledgments', 'acknowledgements', 'dedication', 
            'epigraph', 'frontispiece', 'publisher', 'copyright', 
            'about', 'biographical sketch', 'translator\'s note', 
            'editor\'s note', 'editorial note',
        }
        
        # Note: preface, foreword, introduction are NOT in skip list - they contain theological content
        
        back_matter = {
            'appendix', 'bibliography', 'index', 'glossary',
            'notes', 'endnotes', 'footnotes', 'references',
            'about the author', 'about the editor', 'colophon',
            'advertisement', 'advertisements', 'other works',
            'also by', 'books by', 'related titles'
        }
        
        title_lower = title.lower()
        
        # Always skip these regardless of options
        always_skip = {'title page', 'toc', 'table of contents', 'contents', 'copyright'}
        if title_lower in always_skip:
            if self.verbose:
                print(f"Skipping section: {title} (always skip)")
            return None
        
        # Check front matter (excluding preface, foreword, introduction)
        if not self.include_front_matter and title_lower in front_matter_skip:
            if self.verbose:
                print(f"Skipping front matter section: {title}")
            return None
        
        # Check back matter  
        if not self.include_back_matter and title_lower in back_matter:
            if self.verbose:
                print(f"Skipping back matter section: {title}")
            return None
        
        # Roman numeral sections - only skip if they're very short administrative content
        if re.match(r'^[ivxlc]+\.?$', title_lower.strip()):
            paragraph_count = len(div1.findall('p'))
            if paragraph_count < 2 and not self.include_front_matter:
                if self.verbose:
                    print(f"Skipping short Roman numeral section: {title} ({paragraph_count} paragraphs)")
                return None
        
        # Extract headings
        headings = []
        for i in range(1, 7):  # h1 through h6
            for heading in div1.findall(f'h{i}'):
                heading_text = self.extract_text_content(heading)
                if heading_text:
                    headings.append((i, self.clean_text(heading_text)))
        
        # Extract paragraph content
        paragraphs = []
        for p in div1.findall('p'):
            p_text = self.extract_text_content(p)
            if p_text:
                paragraphs.append(self.clean_text(p_text))
        
        # Quality check: Skip sections with no substantial content
        # But be lenient for sections that might have content in other formats
        if not paragraphs and not headings:
            if self.verbose:
                print(f"Skipping section with no content: {title}")
            return None
        
        # If we have headings but no paragraphs, it might be a structural section
        if headings and not paragraphs:
            if self.verbose:
                print(f"Skipping structural section (headings only): {title}")
            return None
        
        return {
            'title': title,
            'id': section_id,
            'headings': headings,
            'paragraphs': paragraphs,
            'full_text': '\n\n'.join(paragraphs)
        }
    
    def chunk_text(self, text: str, max_length: int = 1500) -> List[str]:
        """
        Chunk text into segments of approximately max_length characters,
        respecting paragraph boundaries when possible.
        """
        if len(text) <= max_length:
            return [text]
        
        chunks = []
        paragraphs = text.split('\n\n')
        current_chunk = ""
        
        for paragraph in paragraphs:
            # If adding this paragraph would exceed max_length
            if len(current_chunk) + len(paragraph) + 2 > max_length:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = paragraph
                else:
                    # Single paragraph is too long, split by sentences
                    sentences = re.split(r'(?<=[.!?])\s+', paragraph)
                    temp_chunk = ""
                    for sentence in sentences:
                        if len(temp_chunk) + len(sentence) + 1 > max_length:
                            if temp_chunk:
                                chunks.append(temp_chunk.strip())
                                temp_chunk = sentence
                            else:
                                # Single sentence too long, force split
                                while len(sentence) > max_length:
                                    chunks.append(sentence[:max_length].strip())
                                    sentence = sentence[max_length:]
                                temp_chunk = sentence
                        else:
                            temp_chunk += " " + sentence if temp_chunk else sentence
                    current_chunk = temp_chunk
            else:
                current_chunk += "\n\n" + paragraph if current_chunk else paragraph
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def build_structure_path(self, div1_title: str, headings: List[tuple]) -> str:
        """Build hierarchical structure path for a section."""
        path_parts = []
        
        # Add div1 title if meaningful (now including preface, foreword, introduction)
        if div1_title:
            # Clean up common chapter/section patterns
            cleaned_title = div1_title.strip()
            # If it's just a number or roman numeral, make it more descriptive
            if re.match(r'^[0-9]+$', cleaned_title):
                cleaned_title = f"Chapter {cleaned_title}"
            elif re.match(r'^[ivxlc]+\.?$', cleaned_title.lower()):
                cleaned_title = f"Chapter {cleaned_title.upper()}"
            # Capitalize standard sections
            elif cleaned_title.lower() in ['preface', 'foreword', 'introduction']:
                cleaned_title = cleaned_title.capitalize()
            
            path_parts.append(cleaned_title)
        
        # Add meaningful headings (skip redundant ones)
        for level, heading_text in headings:
            cleaned_heading = heading_text.strip()
            
            # Skip if it's just repeating the div1 title
            if div1_title and cleaned_heading.upper() == div1_title.upper():
                continue
                
            # Skip if it's just the book title
            if cleaned_heading.upper() in ['ORTHODOXY', 'HERETICS']:
                continue
            
            # Add h1 and h2 level headings for structure
            if level <= 2:
                path_parts.append(cleaned_heading)
        
        return ' > '.join(path_parts) if path_parts else ''
    
    def convert_to_markdown(self, source_file: str) -> str:
        """Convert CCEL ThML to markdown format expected by annotation prompt."""
        
        # Parse XML
        if source_file.startswith('http'):
            response = requests.get(source_file)
            response.raise_for_status()
            xml_content = response.text
            self.source_filename = Path(urllib.parse.urlparse(source_file).path).name
        else:
            with open(source_file, 'r', encoding='utf-8') as f:
                xml_content = f.read()
            self.source_filename = Path(source_file).name
        
        # Clean up XML content
        # Remove XML processing instructions and DOCTYPE
        xml_content = re.sub(r'<\?xml[^>]*\?>', '', xml_content)
        xml_content = re.sub(r'<!DOCTYPE[^>]*>', '', xml_content)
        xml_content = re.sub(r'<!--.*?-->', '', xml_content, flags=re.DOTALL)
        
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
        
        try:
            root = ET.fromstring(xml_content)
        except ET.ParseError as e:
            print(f"XML Parse Error: {e}")
            print("Attempting more aggressive fixes...")
            
            # More aggressive cleanup
            # Remove style elements which might contain problematic content
            xml_content = re.sub(r'<style[^>]*>.*?</style>', '', xml_content, flags=re.DOTALL)
            
            try:
                root = ET.fromstring(xml_content)
            except ET.ParseError as e2:
                print(f"Still failing: {e2}")
                # Last resort: try to extract just the body content
                body_match = re.search(r'<ThML\.body>(.*?)</ThML\.body>', xml_content, re.DOTALL)
                if body_match:
                    body_content = body_match.group(1)
                    # Create a minimal valid XML structure
                    minimal_xml = f"""<ThML>
<ThML.head>
<DC>
<DC.Title>Orthodoxy</DC.Title>
<DC.Creator sub="Author" scheme="short-form">Gilbert K. Chesterton</DC.Creator>
</DC>
</ThML.head>
<ThML.body>
{body_content}
</ThML.body>
</ThML>"""
                    root = ET.fromstring(minimal_xml)
                else:
                    raise e2
        
        # Extract metadata
        self.source_metadata = self.extract_source_metadata(root)
        
        # Process sections
        sections = self.process_div1_sections(root)
        
        # Generate markdown
        markdown_lines = []
        
        # Source Metadata section
        markdown_lines.append("- # Source Metadata")
        markdown_lines.append("    - Core-Identification")
        markdown_lines.append("        - Source-ID:: ")
        
        title = self.source_metadata.get('title', 'Unknown Title')
        markdown_lines.append(f"        - Title:: [[{title}]]")
        markdown_lines.append("        - Subtitle::")
        
        author = self.source_metadata.get('author', 'Unknown Author')
        markdown_lines.append(f"        - Author-Primary:: [[{author}]]")
        markdown_lines.append("        - Author-Additional::")
        markdown_lines.append("        - Editor::")
        markdown_lines.append("        - Translator::")
        
        pub_year = self.source_metadata.get('publication_year', '')
        if pub_year:
            markdown_lines.append(f"        - Publication-Year:: [[{pub_year}]]")
        else:
            markdown_lines.append("        - Publication-Year::")
        
        markdown_lines.append("    - Source-Classification")
        markdown_lines.append("        - Genre-Primary::")
        markdown_lines.append("        - Genre-Secondary::")
        markdown_lines.append("    - Content-Characteristics")
        markdown_lines.append("        - Length-Words::")
        markdown_lines.append(f"        - Length-Chunks:: {len([chunk for section in sections for chunk in self.chunk_text(section['full_text'])])}")
        markdown_lines.append("        - Chapters:: true")
        markdown_lines.append("        - Sections:: false")
        markdown_lines.append("    - Theological-Coverage")
        markdown_lines.append("        - Topics::")
        markdown_lines.append("")
        
        # Chunks section
        markdown_lines.append("- # Chunks")
        
        for section in sections:
            section_title = section['title']
            
            # Add section header if it has a meaningful title
            if section_title and section_title.lower() not in ['preface', 'introduction']:
                markdown_lines.append(f"    - ## {section_title}")
            
            # Add any h1 or h2 headings as subsections
            for level, heading_text in section['headings']:
                if level == 1 and heading_text.upper() != section_title.upper():
                    markdown_lines.append(f"        - ### {heading_text}")
                elif level == 2:
                    markdown_lines.append(f"            - #### {heading_text}")
            
            # Chunk the section content
            chunks = self.chunk_text(section['full_text'])
            
            # Build structure path for this section
            structure_path = self.build_structure_path(section['title'], section['headings'])
            
            for chunk_text in chunks:
                if len(chunk_text.strip()) > 100:  # Only include substantial chunks
                    markdown_lines.append(f"        - Chunk:: {chunk_text}")
                    # Add metadata template for each chunk
                    markdown_lines.append("            - concepts::")
                    markdown_lines.append("            - topics::")
                    markdown_lines.append("            - terms::")
                    markdown_lines.append("            - discourse-elements::")
                    markdown_lines.append("            - scripture-references::")
                    
                    # Add structure path if available
                    if structure_path:
                        markdown_lines.append(f"            - structure-path:: [[{structure_path}]]")
                    else:
                        markdown_lines.append("            - structure-path::")
                    
                    markdown_lines.append("            - named-entities::")
                    markdown_lines.append("")
        
        return '\n'.join(markdown_lines)


def main():
    parser = argparse.ArgumentParser(description='Convert CCEL ThML files to markdown format for theological annotation')
    parser.add_argument('input', help='Input XML file (local file or URL)')
    parser.add_argument('output', help='Output markdown file')
    parser.add_argument('--max-chunk-length', type=int, default=1500, 
                      help='Maximum character length for text chunks (default: 1500)')
    parser.add_argument('--include-front-matter', action='store_true',
                      help='Include front matter sections like prefaces and introductions')
    parser.add_argument('--include-back-matter', action='store_true', 
                      help='Include back matter sections like appendices and indexes')
    parser.add_argument('--verbose', '-v', action='store_true',
                      help='Show detailed processing information')
    
    args = parser.parse_args()
    
    try:
        processor = CCELThMLProcessor()
        processor.include_front_matter = args.include_front_matter
        processor.include_back_matter = args.include_back_matter
        processor.verbose = args.verbose
        
        markdown_content = processor.convert_to_markdown(args.input)
        
        # Write output file
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        print(f"Successfully converted {args.input} to {args.output}")
        print(f"Generated {len([line for line in markdown_content.split('\n') if 'Chunk::' in line])} chunks")
        
    except Exception as e:
        print(f"Error processing file: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()