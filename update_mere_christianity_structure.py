#!/usr/bin/env python3
"""
Update structure_path for Mere Christianity chunks
"""

import json
import re
from pathlib import Path

# Book and chapter mapping
BOOK_CHAPTER_MAP = {
    "Book 1": {
        "name": "Right and Wrong",
        "chapters": {
            1: "The Law of Human Nature",
            2: "Some Objections",
            3: "The Reality of the Law",
            4: "What Lies Behind the Law",
            5: "We Have Cause to Be Uneasy"
        }
    },
    "Book 2": {
        "name": "What Christians Believe",
        "chapters": {
            1: "The Rival Conceptions of God",
            2: "The Invasion",
            3: "The Shocking Alternative",
            4: "The Perfect Penitent",
            5: "The Practical Conclusions"
        }
    },
    "Book 3": {
        "name": "Christian Behavior",
        "chapters": {
            1: "The Three Parts of Morality",
            2: "The \"Cardinal Virtues\"",
            3: "Social Morality",
            4: "Morality and Psychoanalysis",
            5: "Sexual Morality",
            6: "Christian Marriage",
            7: "Forgiveness",
            8: "The Great Sin",
            9: "Charity",
            10: "Hope",
            11: "Faith (Pt. 1)",
            12: "Faith (Pt. 2)"
        }
    },
    "Book 4": {
        "name": "Beyond Personality",
        "chapters": {
            1: "Making and Begetting",
            2: "The Three-Personal God",
            3: "Time and Beyond Time",
            4: "Good Infection",
            5: "The Obstinate Toy Soldiers",
            6: "Two Notes",
            7: "Let's Pretend",
            8: "Is Christianity Hard or Easy?",
            9: "Counting the Cost",
            10: "Nice People or New Men",
            11: "The New Men"
        }
    }
}

# Chapter title patterns for detection
CHAPTER_TITLES = {}
for book_num, book_info in BOOK_CHAPTER_MAP.items():
    for chap_num, chap_title in book_info["chapters"].items():
        # Normalize title for matching
        normalized = chap_title.upper().replace('"', "'")
        CHAPTER_TITLES[normalized] = (book_num, chap_num)

def detect_chapter_from_text(text):
    """Try to detect book and chapter from text content."""
    # Look for chapter titles in the first 500 characters
    text_upper = text[:500].upper()
    
    # Try to find chapter titles - check for full match first
    for title, (book_num, chap_num) in CHAPTER_TITLES.items():
        title_upper = title.upper()
        # Check if title appears near the start of the text
        # Remove common punctuation variations
        title_clean = title_upper.replace("'", "").replace('"', "").replace(" ", "")
        text_clean = text_upper.replace("'", "").replace('"', "").replace(" ", "")
        
        # Check if title (or cleaned version) appears in text
        if title_upper in text_upper or title_clean in text_clean:
            return book_num, chap_num
    
    return None, None

def update_structure_path(chunk):
    """Update structure_path for a chunk."""
    current_path = chunk.get("structure_path", [])
    
    # Handle special sections
    if not current_path:
        return chunk
    
    first_path = current_path[0] if current_path else ""
    
    # Keep special sections as-is
    if first_path in ["Contents", "Preface", "Foreword", "About the Author", 
                     "Other Books by C. S. Lewis", "About the Publisher", "Copyright"]:
        return chunk
    
    # Try to detect from text if structure_path is just a number
    if first_path.isdigit():
        chapter_num = int(first_path)
        text = chunk.get("text", "")
        
        # Detect book and chapter from text
        book_num, detected_chap = detect_chapter_from_text(text)
        
        if book_num and detected_chap:
            book_info = BOOK_CHAPTER_MAP[book_num]
            chapter_title = book_info["chapters"][detected_chap]
            
            # Format: Book 1: Right and Wrong > Chapter 1: The Law of Human Nature
            book_name = f"Book {book_num.split()[-1]}: {book_info['name']}"
            chapter_name = f"Chapter {detected_chap}: {chapter_title}"
            chunk["structure_path"] = [book_name, chapter_name]
        else:
            # Fallback: try to infer from chapter number sequence
            # Book 1: chapters 1-5
            # Book 2: chapters 1-5
            # Book 3: chapters 1-12
            # Book 4: chapters 1-11
            
            # We need to track which book we're in based on sequence
            # This is a fallback - ideally we'd detect from text
            # For now, we'll need to track state or use a different approach
            pass
    
    return chunk

def process_chunks_file(input_file, output_file):
    """Process all chunks and update structure_path."""
    chunks = []
    
    print(f"Reading chunks from: {input_file}")
    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                chunk = json.loads(line)
                chunks.append(chunk)
    
    print(f"Found {len(chunks)} chunks")
    
    # Track most recently detected book/chapter from text
    last_detected_book = None
    last_detected_chapter = None
    
    # Process chunks
    updated_chunks = []
    for i, chunk in enumerate(chunks):
        current_path = chunk.get("structure_path", [])
        first_path = current_path[0] if current_path else ""
        
        # Handle special sections
        if first_path in ["Contents", "Preface", "Foreword", "About the Author",
                         "Other Books by C. S. Lewis", "About the Publisher", "Copyright"]:
            updated_chunks.append(chunk)
            continue
        
        # If it's a numeric path, try to map it
        if first_path.isdigit():
            chapter_num = int(first_path)
            text = chunk.get("text", "")
            
            # Try to detect from text first (primary method)
            book_num, detected_chap = detect_chapter_from_text(text)
            
            if book_num and detected_chap:
                # Found chapter title in text - use it
                book_info = BOOK_CHAPTER_MAP[book_num]
                chapter_title = book_info["chapters"][detected_chap]
                book_name = f"Book {book_num.split()[-1]}: {book_info['name']}"
                chapter_name = f"Chapter {detected_chap}: {chapter_title}"
                chunk["structure_path"] = [book_name, chapter_name]
                # Update last detected
                last_detected_book = book_num
                last_detected_chapter = detected_chap
            else:
                # Fallback: use last detected book, but check if chapter_num matches
                if last_detected_book:
                    # Check if chapter_num exists in last detected book
                    if chapter_num in BOOK_CHAPTER_MAP[last_detected_book]["chapters"]:
                        # Use the chapter_num from structure_path
                        book_info = BOOK_CHAPTER_MAP[last_detected_book]
                        chapter_title = book_info["chapters"][chapter_num]
                        book_name = f"Book {last_detected_book.split()[-1]}: {book_info['name']}"
                        chapter_name = f"Chapter {chapter_num}: {chapter_title}"
                        chunk["structure_path"] = [book_name, chapter_name]
                        # Update last detected
                        last_detected_chapter = chapter_num
                    else:
                        # Chapter doesn't exist in last book - try to find which book it belongs to
                        found_book = None
                        for book_key, book_info in BOOK_CHAPTER_MAP.items():
                            if chapter_num in book_info["chapters"]:
                                found_book = book_key
                                break
                        
                        if found_book:
                            book_info = BOOK_CHAPTER_MAP[found_book]
                            chapter_title = book_info["chapters"][chapter_num]
                            book_name = f"Book {found_book.split()[-1]}: {book_info['name']}"
                            chapter_name = f"Chapter {chapter_num}: {chapter_title}"
                            chunk["structure_path"] = [book_name, chapter_name]
                            # Update last detected
                            last_detected_book = found_book
                            last_detected_chapter = chapter_num
                        else:
                            # Can't map - keep original
                            print(f"Warning: Could not map chunk {chunk.get('id')} with structure_path {current_path} (chapter {chapter_num} not found in any book)")
                else:
                    # No last detected - try to find which book chapter_num belongs to
                    # This happens for the first chunk
                    found_book = None
                    for book_key, book_info in BOOK_CHAPTER_MAP.items():
                        if chapter_num in book_info["chapters"]:
                            # For chapter 1, start with Book 1
                            if chapter_num == 1 and not found_book:
                                found_book = "Book 1"
                            elif chapter_num > 1:
                                # For other chapters, use first book that has it
                                if not found_book:
                                    found_book = book_key
                    
                    if found_book:
                        book_info = BOOK_CHAPTER_MAP[found_book]
                        chapter_title = book_info["chapters"][chapter_num]
                        book_name = f"Book {found_book.split()[-1]}: {book_info['name']}"
                        chapter_name = f"Chapter {chapter_num}: {chapter_title}"
                        chunk["structure_path"] = [book_name, chapter_name]
                        # Update last detected
                        last_detected_book = found_book
                        last_detected_chapter = chapter_num
                    else:
                        # Can't map - keep original
                        print(f"Warning: Could not map chunk {chunk.get('id')} with structure_path {current_path} (chapter {chapter_num} not found)")
        
        updated_chunks.append(chunk)
    
    # Write updated chunks
    print(f"Writing updated chunks to: {output_file}")
    with open(output_file, 'w', encoding='utf-8') as f:
        for chunk in updated_chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + '\n')
    
    print(f"✅ Updated {len(updated_chunks)} chunks")
    
    # Show some examples
    print("\n📝 Sample updated structure_path values:")
    for i, chunk in enumerate(updated_chunks[:10]):
        if chunk.get("structure_path"):
            print(f"  Chunk {i}: {chunk['structure_path']}")

if __name__ == "__main__":
    input_file = Path("theological_processing/02_chunked/MERE_CHRISTIANITY___C__S__LEWIS_chunks.jsonl")
    output_file = input_file  # Update in place
    
    process_chunks_file(input_file, output_file)

