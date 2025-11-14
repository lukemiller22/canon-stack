#!/usr/bin/env python3
"""
PDF Chunker
===========

Does ONE thing well: chunks PDF files intelligently.

Philosophy:
- Headings provide structure but aren't content
- Boilerplate is predictable and removable
- Chunks at sentence boundaries targeting 1500 characters
- Prioritizes consistent chunk size over paragraph structure
- Handles PDF-specific issues: page breaks, headers/footers, multi-column layouts

Usage:
    python pdf_chunker.py book.pdf
    python pdf_chunker.py book.pdf --output theological_processing/02_chunked/
"""

import re
import json
import argparse
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import numpy as np

try:
    from pymupdf4llm import to_markdown
    import fitz  # PyMuPDF
    PYMUPDF4LLM_AVAILABLE = True
except ImportError:
    PYMUPDF4LLM_AVAILABLE = False

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

try:
    import PyPDF2
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False

if not PYMUPDF4LLM_AVAILABLE and not PDFPLUMBER_AVAILABLE and not PYPDF2_AVAILABLE:
    print("ERROR: Required libraries not installed")
    print("Install with: pip install pymupdf4llm")
    print("Or fallback: pip install pdfplumber")
    print("Or: pip install PyPDF2")
    exit(1)


@dataclass
class Chunk:
    """A single content chunk."""
    text: str
    structure_path: List[str]
    chunk_type: str  # 'paragraph', 'blockquote', 'list'


class PDFChunker:
    """PDF chunker that chunks at sentence boundaries targeting 1500 chars."""
    
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
    
    # Patterns for headers/footers (common patterns)
    HEADER_FOOTER_PATTERNS = [
        r'^\d+$',  # Just page numbers
        r'^page\s+\d+',
        r'^\d+\s+of\s+\d+',
        r'chapter\s+\d+',
        r'section\s+\d+',
    ]
    
    def __init__(self, pdf_path: str):
        """Initialize with path to PDF file."""
        self.pdf_path = Path(pdf_path)
        self.pdf = None
        self.pages = []
        self.current_structure = []
        self._load_pdf()
        
    def _load_pdf(self):
        """Load PDF using pymupdf4llm (preferred), pdfplumber, or PyPDF2 (fallback)."""
        print(f"📖 Loading PDF: {self.pdf_path.name}")
        
        if PYMUPDF4LLM_AVAILABLE:
            try:
                self.pdf = fitz.open(str(self.pdf_path))
                self.pages = list(self.pdf)
                print(f"  ✅ Loaded {len(self.pages)} pages using pymupdf4llm")
            except Exception as e:
                print(f"  ⚠️  pymupdf4llm failed: {e}")
                print(f"  🔄 Trying pdfplumber fallback...")
                self._load_with_pdfplumber()
        elif PDFPLUMBER_AVAILABLE:
            self._load_with_pdfplumber()
        else:
            self._load_with_pypdf2()
    
    def _load_with_pdfplumber(self):
        """Fallback: Load PDF using pdfplumber."""
        try:
            self.pdf = pdfplumber.open(str(self.pdf_path))
            self.pages = list(self.pdf.pages)
            print(f"  ✅ Loaded {len(self.pages)} pages using pdfplumber")
        except Exception as e:
            print(f"  ⚠️  pdfplumber failed: {e}")
            print(f"  🔄 Trying PyPDF2 fallback...")
            self._load_with_pypdf2()
    
    def _load_with_pypdf2(self):
        """Fallback: Load PDF using PyPDF2."""
        try:
            import PyPDF2
            with open(self.pdf_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                self.pages = pdf_reader.pages
                self.pdf = pdf_reader  # Store reader for metadata access
                print(f"  ✅ Loaded {len(self.pages)} pages using PyPDF2")
        except Exception as e:
            print(f"  ❌ Failed to load PDF: {e}")
            raise
    
    def chunk(self) -> List[Dict]:
        """
        Chunk the entire PDF.
        
        Returns:
            List of chunk dictionaries ready for JSONL output
        """
        print(f"📖 Processing: {self.pdf_path.name}")
        
        all_chunks = []
        chunk_index = 0
        
        # Extract text from all pages
        full_text_parts = []
        current_structure = []
        first_page_structure = None  # Track structure from first page
        
        for page_num, page in enumerate(self.pages, 1):
            if PYMUPDF4LLM_AVAILABLE:
                page_text = self._extract_text_pymupdf4llm(page, page_num)
            elif PDFPLUMBER_AVAILABLE:
                page_text = self._extract_text_pdfplumber(page, page_num)
            else:
                page_text = self._extract_text_pypdf2(page, page_num)
            
            if not page_text or len(page_text.strip()) < 50:
                continue
            
            # Detect structure changes (headings)
            page_structure = self._detect_structure(page_text, page_num)
            
            # For first page, prioritize its structure and use filename as fallback
            if page_num == 1:
                filename_title = self.pdf_path.stem
                if page_structure:
                    # Use detected structure if it's longer/more complete than filename
                    # or if filename is very short
                    detected_title = ' '.join(page_structure)
                    # Also check if detected title looks like a question (likely the actual title)
                    is_question_title = detected_title.endswith('?')
                    filename_is_question = filename_title.endswith('?')
                    
                    # Prefer question format titles, or if detected is significantly longer
                    if (is_question_title and not filename_is_question) or \
                       (len(detected_title) >= len(filename_title) * 0.9 and len(filename_title) < 10):
                        first_page_structure = page_structure
                        current_structure = page_structure
                    else:
                        # Filename is more complete or is a question, use it
                        current_structure = [filename_title]
                        first_page_structure = current_structure
                else:
                    # Use filename as structure (remove extension, clean up)
                    current_structure = [filename_title]
                    first_page_structure = current_structure
            elif page_structure:
                # Update structure if we find a new heading
                current_structure = page_structure
            elif first_page_structure:
                # Keep using first page structure if no new heading found
                current_structure = first_page_structure
            
            # Clean page text (remove headers/footers, normalize whitespace)
            cleaned_text = self._clean_page_text(page_text, page_num)
            
            if cleaned_text:
                full_text_parts.append((cleaned_text, current_structure.copy()))
        
        # Combine all text and chunk it
        all_chunks = self._chunk_text_parts(full_text_parts, chunk_index)
        
        print(f"\n✅ Created {len(all_chunks)} chunks")
        return all_chunks
    
    def _extract_text_pymupdf4llm(self, page, page_num: int) -> str:
        """Extract text from a page using pymupdf4llm (handles multi-column layouts)."""
        try:
            # pymupdf4llm handles multi-column layouts automatically
            # to_markdown can work with a page if we pass the page number
            # Or we can extract the full document and get the page
            markdown_text = to_markdown(self.pdf, pages=[page_num - 1])
            
            # Convert markdown to plain text (remove markdown formatting but keep structure)
            # Remove markdown headers (# ## ###)
            text = re.sub(r'^#+\s+', '', markdown_text, flags=re.MULTILINE)
            # Remove markdown bold/italic
            text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
            text = re.sub(r'\*([^*]+)\*', r'\1', text)
            # Keep line breaks for paragraph structure
            # Normalize multiple newlines to double newline
            text = re.sub(r'\n{3,}', '\n\n', text)
            
            return text.strip()
        except Exception as e:
            print(f"  ⚠️  Error extracting text from page {page_num} with pymupdf4llm: {e}")
            # Fallback to simple extraction
            try:
                return page.get_text()
            except:
                return ""
    
    def _extract_text_pdfplumber(self, page, page_num: int) -> str:
        """Extract text from a page using pdfplumber, handling multi-column layouts."""
        try:
            # Get words with their positions
            words = page.extract_words()
            if not words:
                # Fallback to simple extraction
                text = page.extract_text()
                return text or ""
            
            # Detect columns by analyzing word positions
            columns = self._detect_columns(words, page.width)
            
            if len(columns) > 1:
                print(f"  📊 Page {page_num}: Detected {len(columns)} columns")
                # Multi-column layout - extract each column separately
                column_texts = []
                for col_idx, col_words in enumerate(columns):
                    # Sort words by y position (top to bottom), then x position (left to right)
                    col_words_sorted = sorted(col_words, key=lambda w: (-round(w['top'], 1), w['x0']))
                    # Extract text maintaining reading order
                    col_text = self._words_to_text(col_words_sorted)
                    if col_text.strip():
                        column_texts.append(col_text)
                        print(f"    📄 Column {col_idx + 1}: {len(col_words)} words, {len(col_text)} chars")
                
                # Join columns with double newline (read left column fully, then right column)
                return '\n\n'.join(column_texts)
            else:
                print(f"  📄 Page {page_num}: Single column detected")
                # Single column - extract normally
                words_sorted = sorted(words, key=lambda w: (-w['top'], w['x0']))
                return self._words_to_text(words_sorted)
                
        except Exception as e:
            print(f"  ⚠️  Error extracting text from page {page_num}: {e}")
            # Fallback to simple extraction
            try:
                return page.extract_text() or ""
            except:
                return ""
    
    def _detect_columns(self, words: List[Dict], page_width: float) -> List[List[Dict]]:
        """Detect columns in a page by analyzing word x-positions."""
        if not words or len(words) < 10:
            return [words]
        
        # Get x-positions of word centers
        x_centers = [(w['x0'] + w['x1']) / 2 for w in words]
        
        # Simple approach: check if words cluster into two groups
        # Split page into left and right halves
        mid_point = page_width / 2
        
        left_words = [w for w in words if (w['x0'] + w['x1']) / 2 < mid_point]
        right_words = [w for w in words if (w['x0'] + w['x1']) / 2 >= mid_point]
        
        # Check if both halves have significant content
        if len(left_words) > len(words) * 0.2 and len(right_words) > len(words) * 0.2:
            # Check if there's a clear gap between columns
            left_max_x = max((w['x1'] for w in left_words), default=0)
            right_min_x = min((w['x0'] for w in right_words), default=page_width)
            
            gap = right_min_x - left_max_x
            
            # If gap is significant (>10% of page width), we have columns
            if gap > page_width * 0.1:
                print(f"    Found 2 columns: gap={gap:.1f}, left={len(left_words)} words, right={len(right_words)} words")
                return [left_words, right_words]
        
        # Try more sophisticated detection: find largest gap
        sorted_x = sorted(set(x_centers))
        if len(sorted_x) > 1:
            gaps = [(sorted_x[i+1] - sorted_x[i], sorted_x[i], sorted_x[i+1]) 
                   for i in range(len(sorted_x)-1)]
            gaps.sort(reverse=True)
            
            if gaps and gaps[0][0] > page_width * 0.15:  # Gap > 15% of page width
                boundary = (gaps[0][1] + gaps[0][2]) / 2
                left_col = [w for w in words if (w['x0'] + w['x1']) / 2 < boundary]
                right_col = [w for w in words if (w['x0'] + w['x1']) / 2 >= boundary]
                if len(left_col) > len(words) * 0.15 and len(right_col) > len(words) * 0.15:
                    print(f"    Found 2 columns via gap detection: gap={gaps[0][0]:.1f}")
                    return [left_col, right_col]
        
        # Fallback: single column
        return [words]
    
    def _words_to_text(self, words: List[Dict]) -> str:
        """Convert word list to text, maintaining reading order."""
        if not words:
            return ""
        
        # Sort by top (descending - top to bottom) then left (ascending)
        # Round y positions to handle slight variations
        sorted_words = sorted(words, key=lambda w: (-round(w['top'], 1), w['x0']))
        
        text_parts = []
        prev_word = None
        
        for word in sorted_words:
            word_text = word.get('text', '')
            if not word_text:
                continue
            
            # Determine if we need a space before this word
            if prev_word:
                # Calculate distance
                x_gap = word['x0'] - prev_word['x1']
                y_diff = abs(word['top'] - prev_word['top'])
                word_height = word.get('height', prev_word.get('height', 10))
                
                # If words are on different lines (y difference > threshold)
                if y_diff > word_height * 0.6:
                    text_parts.append(' ')
                # If words are far apart horizontally within same line, add space
                elif x_gap > word.get('width', 5) * 0.5:
                    text_parts.append(' ')
                # If words are very close, no space (might be part of same word)
                elif x_gap < -2:  # Overlapping
                    pass  # No space
                else:
                    # Default: add space for normal word spacing
                    text_parts.append(' ')
            
            text_parts.append(word_text)
            prev_word = word
        
        result = ''.join(text_parts)
        # Clean up multiple spaces
        result = re.sub(r' +', ' ', result)
        # Clean up spaces around newlines
        result = re.sub(r' +\n', '\n', result)
        result = re.sub(r'\n +', '\n', result)
        
        return result.strip()
    
    def _extract_text_pypdf2(self, page, page_num: int) -> str:
        """Extract text from a page using PyPDF2."""
        try:
            text = page.extract_text()
            return text or ""
        except Exception as e:
            print(f"  ⚠️  Error extracting text from page {page_num}: {e}")
            return ""
    
    def _detect_structure(self, page_text: str, page_num: int) -> List[str]:
        """Detect headings/structure from page text and layout."""
        # For first page, prioritize title detection
        if page_num == 1:
            # Look for question format title first
            lines = page_text.split('\n')
            for line in lines[:10]:  # Check first 10 lines
                line = line.strip()
                if line.endswith('?') and len(line) < 100 and (line.istitle() or self._is_title_case(line)):
                    if not self._is_boilerplate(line):
                        return [line]
        
        # First try to detect headings using pymupdf4llm's layout analysis
        if PYMUPDF4LLM_AVAILABLE and page_num <= len(self.pages):
            try:
                page = self.pages[page_num - 1]
                # Look for larger text (likely headings) using font sizes
                blocks = page.get_text("dict")["blocks"]
                font_sizes = {}
                
                for block in blocks:
                    if "lines" in block:
                        for line in block["lines"]:
                            for span in line["spans"]:
                                size = span.get("size", 0)
                                text = span.get("text", "").strip()
                                if size > 0 and text:
                                    if size not in font_sizes:
                                        font_sizes[size] = []
                                    font_sizes[size].append(text)
                
                if font_sizes:
                    # Find the largest font size (likely heading)
                    sizes = sorted(font_sizes.keys(), reverse=True)
                    if len(sizes) > 1 and sizes[0] > sizes[1] * 1.2:
                        # Extract text from largest font
                        heading_texts = font_sizes[sizes[0]]
                        heading_text = ' '.join(heading_texts[:3])  # First few lines
                        heading_text = re.sub(r'\s+', ' ', heading_text).strip()
                        
                        # Check if it looks like a heading
                        if (len(heading_text) < 100 and 
                            heading_text and 
                            not self._is_boilerplate(heading_text) and
                            not re.match(r'^[A-Za-z]+\s+\d+:\d+', heading_text)):
                            return [heading_text]
            except Exception as e:
                pass  # Fallback to text-based detection
        
        # Try pdfplumber layout analysis as fallback
        elif PDFPLUMBER_AVAILABLE and page_num <= len(self.pages):
            try:
                page = self.pages[page_num - 1]
                chars = page.chars
                if chars:
                    font_sizes = {}
                    for char in chars:
                        size = char.get('size', 0)
                        if size > 0:
                            if size not in font_sizes:
                                font_sizes[size] = []
                            font_sizes[size].append(char)
                    
                    if font_sizes:
                        max_size = max(font_sizes.keys())
                        sizes = sorted(font_sizes.keys(), reverse=True)
                        if len(sizes) > 1 and sizes[0] > sizes[1] * 1.2:
                            heading_chars = sorted(font_sizes[max_size], 
                                                  key=lambda c: (-c['top'], c['x0']))
                            heading_text = ''.join(c['text'] for c in heading_chars[:100])
                            heading_text = re.sub(r'\s+', ' ', heading_text).strip()
                            
                            if (len(heading_text) < 100 and 
                                heading_text and 
                                not self._is_boilerplate(heading_text) and
                                not re.match(r'^[A-Za-z]+\s+\d+:\d+', heading_text)):
                                return [heading_text]
            except Exception as e:
                pass  # Fallback to text-based detection
        
        # Fallback: text-based heading detection
        lines = page_text.split('\n')
        structure = []
        
        # Check first few lines for title/heading
        for i, line in enumerate(lines[:15]):  # Check first 15 lines of page
            line = line.strip()
            if not line:
                continue
            
            # Skip very short lines (likely page numbers)
            if len(line) < 3:
                continue
            
            # Check if line looks like a heading
            is_heading = False
            
            # Pattern 1: All caps and short (but not too short)
            if line.isupper() and 10 < len(line) < 100:
                is_heading = True
            
            # Pattern 2: Title case, short, followed by blank line or paragraph
            elif (line.istitle() or self._is_title_case(line)) and len(line) < 100:
                # Check if next non-empty line starts with lowercase (paragraph) or is blank
                next_line_idx = i + 1
                while next_line_idx < len(lines) and not lines[next_line_idx].strip():
                    next_line_idx += 1
                if next_line_idx < len(lines):
                    next_line = lines[next_line_idx].strip()
                    if next_line and (next_line[0].islower() or len(next_line) > 200):
                        is_heading = True
            
            # Pattern 3: Numbered headings (Chapter 1, Part 2.1, Section 3, etc.)
            if re.match(r'^(chapter|part|book|section)\s+\d+', line, re.IGNORECASE):
                is_heading = True
            
            # Pattern 4: Question format (like "Do We Have a Free Will?")
            if line.endswith('?') and len(line) < 100 and (line.istitle() or self._is_title_case(line)):
                is_heading = True
            
            # Skip Bible verse references (they look like headings but aren't)
            if re.match(r'^[A-Za-z]+\s+\d+:\d+', line) or re.match(r'^\d+:\d+', line):
                is_heading = False
                continue
            
            if is_heading:
                # Check if it's boilerplate
                if not self._is_boilerplate(line):
                    # Clean up the heading (fix spacing issues)
                    cleaned_heading = re.sub(r'\s+', ' ', line)
                    structure.append(cleaned_heading)
                    break  # Use first good heading
        
        return structure if structure else None
    
    def _is_title_case(self, text: str) -> bool:
        """Check if text is title case (most words capitalized)."""
        words = text.split()
        if not words:
            return False
        
        capitalized = sum(1 for w in words if w and w[0].isupper())
        return capitalized / len(words) > 0.7  # 70% of words capitalized
    
    def _is_boilerplate(self, text: str) -> bool:
        """Check if text matches boilerplate patterns."""
        text_lower = text.lower().strip()
        
        for pattern in self.BOILERPLATE_TITLES:
            if re.search(pattern, text_lower):
                return True
        
        return False
    
    def _clean_page_text(self, page_text: str, page_num: int) -> str:
        """Clean page text: remove headers/footers, normalize whitespace, fix missing spaces."""
        if not page_text:
            return ""
        
        lines = page_text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Skip header/footer patterns
            is_header_footer = False
            for pattern in self.HEADER_FOOTER_PATTERNS:
                if re.match(pattern, line, re.IGNORECASE):
                    is_header_footer = True
                    break
            
            # Skip very short lines that are likely headers/footers
            if len(line) < 5 and line.isdigit():
                is_header_footer = True
            
            if not is_header_footer:
                cleaned_lines.append(line)
        
        # Join lines with spaces
        text = ' '.join(cleaned_lines)
        
        # Fix missing spaces between words (common PDF issue)
        # Pattern: lowercase letter followed by uppercase letter = missing space
        text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
        
        # Pattern: digit followed by letter or letter followed by digit = add space if not already there
        text = re.sub(r'(\d)([A-Za-z])', r'\1 \2', text)
        text = re.sub(r'([A-Za-z])(\d)', r'\1 \2', text)
        
        # Fix punctuation spacing
        text = re.sub(r'([.!?])([A-Za-z])', r'\1 \2', text)
        text = re.sub(r'([,;:])([A-Za-z])', r'\1 \2', text)
        
        # Fix common word boundaries (lowercase to uppercase transitions)
        # But preserve acronyms (all caps words)
        text = re.sub(r'([a-z])([A-Z][a-z])', r'\1 \2', text)
        
        # Normalize whitespace: multiple spaces to single space
        text = re.sub(r'\s+', ' ', text)
        
        # Fix hyphenated words at line breaks (remove space after hyphen)
        text = re.sub(r'(\w+)-\s+(\w+)', r'\1-\2', text)
        
        return text.strip()
    
    def _chunk_text_parts(
        self, 
        text_parts: List[Tuple[str, List[str]]], 
        start_index: int
    ) -> List[Dict]:
        """Chunk text parts at sentence boundaries targeting 1500 chars."""
        target_chunk_size = 1500
        chunks = []
        chunk_index = start_index
        
        # Combine all text parts
        full_text = ""
        current_structure = []
        
        for text, structure in text_parts:
            # Update structure if we have a new one
            if structure:
                current_structure = structure
            
            # Add text with space
            if full_text and not full_text.endswith(' '):
                full_text += " "
            full_text += text
        
        # Split into sentences
        # Pattern: . ! ? followed by space or newline
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
        current_chunk_structure = current_structure.copy()
        
        for sentence in complete_sentences:
            potential_chunk = current_chunk + " " + sentence if current_chunk else sentence
            
            if len(potential_chunk) <= target_chunk_size:
                # Can add this sentence
                current_chunk = potential_chunk
            else:
                # Current chunk is full, save it
                if current_chunk:
                    source_id = self._make_source_id()
                    chunks.append({
                        "id": f"{source_id}_{chunk_index}",
                        "text": current_chunk.strip(),
                        "source": self.pdf_path.stem,
                        "author": self._get_author(),
                        "structure_path": current_chunk_structure.copy(),
                        "chunk_type": "paragraph",
                        "chunk_index": chunk_index,
                        "processing_stage": "chunked",
                        "processing_timestamp": datetime.now().isoformat()
                    })
                    chunk_index += 1
                
                # Start new chunk with this sentence
                current_chunk = sentence
        
        # Add final chunk
        if current_chunk.strip():
            source_id = self._make_source_id()
            chunks.append({
                "id": f"{source_id}_{chunk_index}",
                "text": current_chunk.strip(),
                "source": self.pdf_path.stem,
                "author": self._get_author(),
                "structure_path": current_chunk_structure.copy(),
                "chunk_type": "paragraph",
                "chunk_index": chunk_index,
                "processing_stage": "chunked",
                "processing_timestamp": datetime.now().isoformat()
            })
        
        return chunks
    
    def _make_source_id(self) -> str:
        """Create a source ID from the filename."""
        name = self.pdf_path.stem.upper()
        # Replace non-alphanumeric with underscore
        name = re.sub(r'[^A-Z0-9]', '_', name)
        return name
    
    def _get_author(self) -> str:
        """Extract author from PDF metadata."""
        try:
            if PYMUPDF4LLM_AVAILABLE and self.pdf:
                metadata = self.pdf.metadata
                if metadata and 'author' in metadata:
                    return metadata['author']
            elif PDFPLUMBER_AVAILABLE and self.pdf:
                metadata = self.pdf.metadata
                if metadata and 'Author' in metadata:
                    return metadata['Author']
            elif PYPDF2_AVAILABLE and hasattr(self, 'pdf') and self.pdf:
                if hasattr(self.pdf, 'metadata') and self.pdf.metadata:
                    author = self.pdf.metadata.get('/Author') or self.pdf.metadata.get('Author')
                    if author:
                        return author
        except Exception as e:
            print(f"  ⚠️  Could not extract author: {e}")
        
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
    
    def __del__(self):
        """Clean up PDF file handle."""
        if PYMUPDF4LLM_AVAILABLE and self.pdf:
            try:
                self.pdf.close()
            except:
                pass
        elif PDFPLUMBER_AVAILABLE and self.pdf:
            try:
                self.pdf.close()
            except:
                pass
        # PyPDF2 doesn't need explicit closing (file is closed after reading)


def main():
    parser = argparse.ArgumentParser(
        description="PDF chunker - chunks by sentence boundaries, preserves structure"
    )
    parser.add_argument('pdf_file', help="Path to PDF file")
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
    chunker = PDFChunker(args.pdf_file)
    
    # Chunk the PDF
    chunks = chunker.chunk()
    
    if not chunks:
        print("❌ No chunks created. Check if PDF is readable.")
        return
    
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
        print(f"    Structure: {' > '.join(chunk['structure_path']) if chunk['structure_path'] else 'None'}")
        print(f"    Type: {chunk['chunk_type']}")
        print(f"    Text: {chunk['text'][:100]}...")


if __name__ == "__main__":
    main()

