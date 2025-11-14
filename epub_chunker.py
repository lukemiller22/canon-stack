#!/usr/bin/env python3
"""
Simple ePub Chunker
===================

Does ONE thing well: chunks ePub files intelligently.

Philosophy:
- Headings provide structure but aren't content
- Boilerplate is predictable and removable
- Chunks at sentence boundaries targeting 1500 characters
- Prioritizes consistent chunk size over paragraph structure

Usage:
    python epub_chunker.py book.epub
    python epub_chunker.py book.epub --output theological_processing/02_chunked/
"""

import re
import json
import argparse
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime

try:
    import ebooklib
    from ebooklib import epub
    from bs4 import BeautifulSoup, NavigableString
except ImportError:
    print("ERROR: Required libraries not installed")
    print("Install with: pip install ebooklib beautifulsoup4")
    exit(1)


@dataclass
class Chunk:
    """A single content chunk."""
    text: str
    structure_path: List[str]
    chunk_type: str  # 'paragraph', 'blockquote', 'list'


class EpubChunker:
    """Simple ePub chunker that chunks at sentence boundaries targeting 1500 chars."""
    
    # Patterns that indicate boilerplate (case-insensitive)
    BOILERPLATE_TITLES = [
        r'^title\s*page$',
        r'^copyright',
        r'^table\s+of\s+contents?$',
        r'^contents?$',
        r'^toc$',
        r'^about\s+the\s+author',
        r'^about\s+the\s+publisher',
        r'^also\s+by',
        r'^other\s+books',
        r'^acknowledgments?',
        r'^dedication',
        r'^cover',
        r'^end\s*notes?$',
        r'^bibliography',
        r'^index$',
        r'^glossary$',
    ]
    
    # Mere Christianity book/chapter structure mapping
    MERE_CHRISTIANITY_STRUCTURE = {
        "Book 1": {
            "name": "Right and Wrong",
            "chapters": {
                "The Law of Human Nature": 1,
                "Some Objections": 2,
                "The Reality of the Law": 3,
                "What Lies Behind the Law": 4,
                "We Have Cause to Be Uneasy": 5,
            }
        },
        "Book 2": {
            "name": "What Christians Believe",
            "chapters": {
                "The Rival Conceptions of God": 1,
                "The Invasion": 2,
                "The Shocking Alternative": 3,
                "The Perfect Penitent": 4,
                "The Practical Conclusions": 5,
            }
        },
        "Book 3": {
            "name": "Christian Behavior",
            "chapters": {
                "The Three Parts of Morality": 1,
                "The \"Cardinal Virtues\"": 2,
                "Social Morality": 3,
                "Morality and Psychoanalysis": 4,
                "Sexual Morality": 5,
                "Christian Marriage": 6,
                "Forgiveness": 7,
                "The Great Sin": 8,
                "Charity": 9,
                "Hope": 10,
                "Faith (Pt. 1)": 11,
                "Faith (Pt. 2)": 12,
            }
        },
        "Book 4": {
            "name": "Beyond Personality",
            "chapters": {
                "Making and Begetting": 1,
                "The Three-Personal God": 2,
                "Time and Beyond Time": 3,
                "Good Infection": 4,
                "The Obstinate Toy Soldiers": 5,
                "Two Notes": 6,
                "Let's Pretend": 7,
                "Is Christianity Hard or Easy?": 8,
                "Counting the Cost": 9,
                "Nice People or New Men": 10,
                "The New Men": 11,
            }
        }
    }
    
    def __init__(self, epub_path: str):
        """Initialize with path to ePub file."""
        self.epub_path = Path(epub_path)
        self.book = epub.read_epub(str(self.epub_path))
        self.toc_map = self._build_toc_map()
        self.is_mere_christianity = "mere christianity" in self.epub_path.stem.lower()
        self.current_book = None  # Track current book for Mere Christianity
        self.current_chapter = None  # Track current chapter for Mere Christianity
        
    def chunk(self) -> List[Dict]:
        """
        Chunk the entire ePub.
        
        Returns:
            List of chunk dictionaries ready for JSONL output
        """
        print(f"📖 Processing: {self.epub_path.name}")
        
        all_chunks = []
        current_structure = []
        chunk_index = 0
        
        # Get all content documents in reading order
        spine = self.book.spine
        
        for item_id, _ in spine:
            item = self.book.get_item_with_id(item_id)
            
            if item.get_type() != ebooklib.ITEM_DOCUMENT:
                continue
            
            # Parse HTML content
            soup = BeautifulSoup(item.get_content(), 'html.parser')
            
            # Check if this is boilerplate
            if self._is_boilerplate(soup, item.get_name()):
                print(f"  ⏭️  Skipping boilerplate: {self._get_section_title(soup, item.get_name())}")
                continue
            
            # Extract chunks from this section
            section_title = self._get_section_title(soup, item.get_name())
            
            # Get text content for structure mapping (more text for better detection)
            text_content = soup.get_text(strip=True)[:2000] if soup else ""
            
            # Map to book/chapter structure for Mere Christianity
            # Keep Preface and Foreword separate
            if self.is_mere_christianity and section_title.lower() not in ['preface', 'foreword', 'contents']:
                current_structure = self._map_mere_christianity_structure(section_title, text_content)
                print(f"  📄 Processing: {section_title} -> {current_structure}")
            else:
                current_structure = [section_title]
                print(f"  📄 Processing: {section_title}")
            
            # Process the content
            section_chunks = self._extract_chunks_from_section(soup, current_structure)
            
            # Add to output with proper IDs
            source_id = self._make_source_id()
            for chunk in section_chunks:
                all_chunks.append({
                    "id": f"{source_id}_{chunk_index}",
                    "structure_path": chunk.structure_path,
                    "text": chunk.text,
                    "source": self.epub_path.stem,
                    "author": self._get_author(),
                    "chunk_type": chunk.chunk_type,
                    "chunk_index": chunk_index,
                    "processing_stage": "chunked",
                    "processing_timestamp": datetime.now().isoformat()
                })
                chunk_index += 1
        
        print(f"\n✅ Created {len(all_chunks)} chunks")
        return all_chunks
    
    def _build_toc_map(self) -> Dict[str, str]:
        """Build a map from file names to TOC titles."""
        toc_map = {}
        
        if not self.book.toc:
            return toc_map
        
        def process_toc_item(item, level=0):
            if isinstance(item, tuple):
                # Nested section
                section, children = item
                if hasattr(section, 'href'):
                    # Clean href (remove anchors)
                    href = section.href.split('#')[0]
                    toc_map[href] = section.title
                for child in children:
                    process_toc_item(child, level + 1)
            elif hasattr(item, 'href'):
                href = item.href.split('#')[0]
                toc_map[href] = item.title
        
        for item in self.book.toc:
            process_toc_item(item)
        
        return toc_map
    
    def _is_boilerplate(self, soup: BeautifulSoup, filename: str) -> bool:
        """Check if this section is boilerplate."""
        # Get title from soup
        title = None
        
        # Try to find title in the document
        title_tag = soup.find(['h1', 'h2', 'title'])
        if title_tag:
            title = title_tag.get_text(strip=True).lower()
        
        # Also check filename
        if not title:
            title = filename.lower()
        
        # Check against boilerplate patterns
        for pattern in self.BOILERPLATE_TITLES:
            if re.search(pattern, title, re.IGNORECASE):
                return True
        
        # Check if section is too short (likely boilerplate)
        text = soup.get_text(strip=True)
        if len(text) < 200:  # Less than 200 chars is suspicious
            return True
        
        # Check for copyright indicators in content
        if len(text) < 1000:  # Only check short sections
            copyright_indicators = [
                'all rights reserved',
                '© copyright',
                'published by',
                'isbn',
                'library of congress'
            ]
            text_lower = text.lower()
            if any(indicator in text_lower for indicator in copyright_indicators):
                return True
        
        return False
    
    def _get_section_title(self, soup: BeautifulSoup, filename: str) -> str:
        """Extract the title/heading for this section."""
        # Method 1: Check TOC
        if filename in self.toc_map:
            return self.toc_map[filename]
        
        # Method 2: Find first heading
        heading = soup.find(['h1', 'h2', 'h3'])
        if heading:
            return heading.get_text(strip=True)
        
        # Method 3: Use filename
        clean_name = Path(filename).stem
        clean_name = clean_name.replace('_', ' ').replace('-', ' ')
        return clean_name.title()
    
    def _map_mere_christianity_structure(self, section_title: str, text: str = "") -> List[str]:
        """Map section title to book/chapter structure for Mere Christianity."""
        if not self.is_mere_christianity:
            return [section_title]
        
        section_title_upper = section_title.upper()
        # Get more text for better detection (first 2000 chars)
        text_upper = text[:2000].upper() if text else ""
        combined_text = (section_title + " " + text).upper()[:2000]
        
        # First, check for book markers in section title
        book_match = re.search(r'book\s*([1-4])', section_title_upper)
        if book_match:
            book_num = book_match.group(1)
            book_key = f"Book {book_num}"
            if book_key in self.MERE_CHRISTIANITY_STRUCTURE:
                book_info = self.MERE_CHRISTIANITY_STRUCTURE[book_key]
                self.current_book = book_key
                # Now try to find chapter title in text
                for chapter_title, chapter_num in book_info["chapters"].items():
                    chapter_title_upper = chapter_title.upper()
                    # Check if chapter title appears in combined text
                    if chapter_title_upper in combined_text:
                        book_name = f"Book {book_num}: {book_info['name']}"
                        chapter_name = f"Chapter {chapter_num}: {chapter_title}"
                        self.current_chapter = chapter_title
                        return [book_name, chapter_name]
                # Book found but no chapter - return book only
                return [f"Book {book_num}: {book_info['name']}"]
        
        # Check each book for matching chapter titles (without book marker)
        # Prioritize matches that appear earlier in the text
        # Also prioritize current book if we have one
        best_match = None
        best_match_position = float('inf')
        best_match_is_current_book = False
        
        # First check current book if we have one
        if self.current_book:
            book_info = self.MERE_CHRISTIANITY_STRUCTURE[self.current_book]
            for chapter_title, chapter_num in book_info["chapters"].items():
                chapter_title_upper = chapter_title.upper()
                if chapter_title_upper in section_title_upper:
                    # Match in section title - highest priority
                    book_name = f"Book {self.current_book.split()[-1]}: {book_info['name']}"
                    chapter_name = f"Chapter {chapter_num}: {chapter_title}"
                    self.current_chapter = chapter_title
                    return [book_name, chapter_name]
                elif chapter_title_upper in combined_text:
                    # Match in text - find position
                    position = combined_text.find(chapter_title_upper)
                    if position < best_match_position:
                        best_match_position = position
                        best_match = (self.current_book, book_info, chapter_title, chapter_num)
                        best_match_is_current_book = True
        
        # Then check all books
        for book_key, book_info in self.MERE_CHRISTIANITY_STRUCTURE.items():
            # Skip if we already checked current book
            if self.current_book and book_key == self.current_book:
                continue
            for chapter_title, chapter_num in book_info["chapters"].items():
                chapter_title_upper = chapter_title.upper()
                # Check if chapter title appears in section title or text
                if chapter_title_upper in section_title_upper:
                    # Match in section title - use it (but current book takes precedence)
                    if not best_match_is_current_book:
                        book_name = f"Book {book_key.split()[-1]}: {book_info['name']}"
                        chapter_name = f"Chapter {chapter_num}: {chapter_title}"
                        self.current_book = book_key
                        self.current_chapter = chapter_title
                        return [book_name, chapter_name]
                elif chapter_title_upper in combined_text:
                    # Match in text - find position
                    position = combined_text.find(chapter_title_upper)
                    if position < best_match_position:
                        best_match_position = position
                        best_match = (book_key, book_info, chapter_title, chapter_num)
                        best_match_is_current_book = False
        
        if best_match:
            book_key, book_info, chapter_title, chapter_num = best_match
            book_name = f"Book {book_key.split()[-1]}: {book_info['name']}"
            chapter_name = f"Chapter {chapter_num}: {chapter_title}"
            self.current_book = book_key
            self.current_chapter = chapter_title
            return [book_name, chapter_name]
        
        # If we have a current book but no chapter match, use the current book
        # This handles continuation chunks
        if self.current_book:
            book_info = self.MERE_CHRISTIANITY_STRUCTURE[self.current_book]
            book_name = f"Book {self.current_book.split()[-1]}: {book_info['name']}"
            # Try to detect chapter from text one more time
            for chapter_title, chapter_num in book_info["chapters"].items():
                chapter_title_upper = chapter_title.upper()
                if chapter_title_upper in combined_text:
                    chapter_name = f"Chapter {chapter_num}: {chapter_title}"
                    self.current_chapter = chapter_title
                    return [book_name, chapter_name]
            # If we have a current chapter, use it
            if self.current_chapter and self.current_chapter in book_info["chapters"]:
                chapter_num = book_info["chapters"][self.current_chapter]
                chapter_name = f"Chapter {chapter_num}: {self.current_chapter}"
                return [book_name, chapter_name]
            # Return book only
            return [book_name]
        
        # Fallback: return original section title
        return [section_title]
    
    def _extract_chunks_from_section(
        self, 
        soup: BeautifulSoup, 
        base_structure: List[str]
    ) -> List[Chunk]:
        """Extract chunks from a section, breaking at sentence boundaries targeting 1500 chars."""
        target_chunk_size = 1500
        chunks = []
        current_structure = base_structure.copy()
        
        # Remove script and style tags
        for tag in soup(['script', 'style', 'nav']):
            tag.decompose()
        
        # Find the main content (body or first div)
        content = soup.find('body') or soup
        
        # Track structure changes from headings
        for element in content.descendants:
            if isinstance(element, NavigableString):
                continue
            
            # Update structure on headings
            if element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                heading_text = element.get_text(strip=True)
                if heading_text:
                    level = int(element.name[1])  # h1 -> 1, h2 -> 2, etc.
                    current_structure = base_structure[:level] + [heading_text]
        
        # Extract all text content from paragraphs, blockquotes, and lists
        all_text_parts = []
        
        for element in content.descendants:
            if isinstance(element, NavigableString):
                continue
            
            # Extract text from content elements
            if element.name in ['p', 'blockquote']:
                text = element.get_text(separator=' ', strip=True)
                if text and len(text) > 10:
                    all_text_parts.append(('text', text))
            
            # Extract list items
            elif element.name == 'li':
                text = element.get_text(strip=True)
                if text:
                    all_text_parts.append(('list_item', f"• {text}"))
        
        # Combine all text
        full_text = ' '.join(text for _, text in all_text_parts)
        
        # Split into sentences (handle . ! ? followed by space or newline)
        # Use regex to split at sentence boundaries: . ! ? followed by whitespace
        # This pattern captures the sentence ending punctuation group
        sentence_pattern = r'([.!?]+)\s+'
        parts = re.split(sentence_pattern, full_text)
        
        # Recombine sentences with their punctuation
        complete_sentences = []
        i = 0
        while i < len(parts):
            sentence_text = parts[i].strip()
            if not sentence_text:
                i += 1
                continue
            
            # Check if next part is punctuation
            if i + 1 < len(parts) and re.match(r'^[.!?]+$', parts[i + 1]):
                punctuation = parts[i + 1]
                combined = sentence_text + punctuation
                i += 2
            else:
                combined = sentence_text
                i += 1
            
            if combined.strip():
                complete_sentences.append(combined.strip())
        
        # Handle any remaining text
        if i < len(parts) and parts[-1].strip():
            last_text = parts[-1].strip()
            if last_text:
                complete_sentences.append(last_text)
        
        # Build chunks targeting 1500 characters
        current_chunk = ""
        for sentence in complete_sentences:
            potential_chunk = current_chunk + " " + sentence if current_chunk else sentence
            
            if len(potential_chunk) <= target_chunk_size:
                # Can add this sentence
                current_chunk = potential_chunk
            else:
                # Current chunk is full, save it
                if current_chunk:
                    chunks.append(Chunk(
                        text=current_chunk.strip(),
                        structure_path=current_structure.copy(),
                        chunk_type='text'
                    ))
                
                # Start new chunk with this sentence
                current_chunk = sentence
        
        # Add final chunk
        if current_chunk.strip():
            chunks.append(Chunk(
                text=current_chunk.strip(),
                structure_path=current_structure.copy(),
                chunk_type='text'
            ))
        
        return chunks
    
    def _make_source_id(self) -> str:
        """Create a source ID from the filename."""
        name = self.epub_path.stem.upper()
        # Replace non-alphanumeric with underscore
        name = re.sub(r'[^A-Z0-9]', '_', name)
        return name
    
    def _get_author(self) -> str:
        """Extract author from ePub metadata."""
        try:
            creators = self.book.get_metadata('DC', 'creator')
            if creators:
                return creators[0][0]  # First creator's name
        except:
            pass
        return "Unknown"
    
    def save_chunks(self, chunks: List[Dict], output_path: Optional[Path] = None):
        """Save chunks to JSONL file."""
        if output_path is None:
            output_path = Path(f"{self._make_source_id()}_chunks.jsonl")
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            for chunk in chunks:
                f.write(json.dumps(chunk, ensure_ascii=False) + '\n')
        
        print(f"💾 Saved to: {output_path}")
        return output_path


def main():
    parser = argparse.ArgumentParser(
        description="Simple ePub chunker - chunks by paragraph, preserves structure"
    )
    parser.add_argument('epub_file', help="Path to ePub file")
    parser.add_argument(
        '--output', 
        help="Output directory or file path (default: current directory)"
    )
    parser.add_argument(
        '--show-structure',
        action='store_true',
        help="Print document structure before chunking"
    )
    
    args = parser.parse_args()
    
    # Initialize chunker
    chunker = EpubChunker(args.epub_file)
    
    # Show structure if requested
    if args.show_structure:
        print("\n📚 Document Structure:")
        print("=" * 60)
        for filename, title in chunker.toc_map.items():
            print(f"  {title}")
        print("=" * 60 + "\n")
    
    # Chunk the ePub
    chunks = chunker.chunk()
    
    # Determine output path
    if args.output:
        output_path = Path(args.output)
        if output_path.is_dir():
            output_path = output_path / f"{chunker._make_source_id()}_chunks.jsonl"
    else:
        output_path = None
    
    # Save chunks
    chunker.save_chunks(chunks, output_path)
    
    # Show summary
    print(f"\n📊 Summary:")
    print(f"  Total chunks: {len(chunks)}")
    
    # Count chunk types
    chunk_types = {}
    for chunk in chunks:
        chunk_type = chunk['chunk_type']
        chunk_types[chunk_type] = chunk_types.get(chunk_type, 0) + 1
    
    for chunk_type, count in sorted(chunk_types.items()):
        print(f"  {chunk_type}: {count}")
    
    # Show first few chunks as examples
    print(f"\n📝 First 3 chunks:")
    for i, chunk in enumerate(chunks[:3]):
        print(f"\n  Chunk {i}:")
        print(f"    Structure: {' > '.join(chunk['structure_path'])}")
        print(f"    Type: {chunk['chunk_type']}")
        print(f"    Text: {chunk['text'][:100]}...")


if __name__ == "__main__":
    main()