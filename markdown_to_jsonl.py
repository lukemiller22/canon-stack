# markdown_to_jsonl.py
import json
import re
import os
from pathlib import Path

def parse_chunk_metadata(chunk_text):
    """Extract metadata from a chunk with the theological annotation format."""
    metadata = {
        'topics': [],
        'concepts': [],
        'themes': [],
        'function': [],
        'scripture_references': [],
        'proper_nouns': [],
        'structure_path': []
    }
    
    # Extract metadata using regex patterns - handle both formats
    patterns = {
        'topics': r'- (?:Topics::|\*\*Topics:\*\*) (.*?)(?=\n\s*- (?:[A-Z]|\*\*)|$)',
        'concepts': r'- (?:Concepts::|\*\*Concepts:\*\*) (.*?)(?=\n\s*- (?:[A-Z]|\*\*)|$)',
        'themes': r'- (?:Themes::|\*\*Themes:\*\*) (.*?)(?=\n\s*- (?:[A-Z]|\*\*)|$)',
        'function': r'- (?:Function::|\*\*Function:\*\*)(.*?)(?=\n\s*- (?:[A-Z]|\*\*)|$)',
        'scripture_references': r'- (?:Scripture-References::|\*\*Scripture-References:\*\*) (.*?)(?=\n\s*- (?:[A-Z]|\*\*)|$)',
        'proper_nouns': r'- (?:Proper-Nouns::|\*\*Proper-Nouns:\*\*) (.*?)(?=\n\s*- (?:[A-Z]|\*\*)|$)'
    }
    
    for field, pattern in patterns.items():
        matches = re.findall(pattern, chunk_text, re.DOTALL | re.IGNORECASE)
        if matches:
            if field == 'function':
                # Parse function elements specially
                func_text = matches[0]
                func_elements = re.findall(r'\[\[([^]]+)\]\] (.+)', func_text)
                metadata[field] = [f"{elem[0]}: {elem[1].strip()}" for elem in func_elements]
            else:
                # Extract bracketed items
                bracketed_items = re.findall(r'\[\[([^]]+)\]\]', matches[0])
                metadata[field] = bracketed_items
    
    return metadata

def extract_chunks_from_markdown(file_path):
    """Extract chunks from a markdown file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extract source metadata
    source_match = re.search(r'- # Source Metadata\n(.*?)\n- # Chunks', content, re.DOTALL)
    source_info = {}
    if source_match:
        source_text = source_match.group(1)
        title_match = re.search(r'Title:: \[\[([^]]+)\]\]', source_text)
        author_match = re.search(r'Author-Primary:: \[\[([^]]+)\]\]', source_text)
        
        if title_match:
            source_info['title'] = title_match.group(1)
        if author_match:
            source_info['author'] = author_match.group(1)
    
    # Extract the chunks section
    chunks_section = re.search(r'- # Chunks\n(.*)', content, re.DOTALL)
    if not chunks_section:
        return []
    
    chunks_text = chunks_section.group(1)
    
    # Parse chunks using the new "Chunk::" format
    chunks = []
    current_section = None
    current_subsection = None
    
    # Process line by line to track section headings
    lines = chunks_text.split('\n')
    current_chunk = None
    current_metadata = []
    
    for line in lines:
        # Check for section headings (format: "    - ## Section Name")
        if line.strip().startswith('- ## '):
            current_section = line.strip()[5:].strip()  # Remove "- ## "
            current_subsection = None
            continue
        elif line.strip().startswith('- ### '):
            current_subsection = line.strip()[6:].strip()  # Remove "- ### "
            continue
            
        # Check for chunk start
        if line.strip().startswith('- Chunk::'):
            # Save previous chunk if exists
            if current_chunk is not None:
                chunks.append(process_chunk(current_chunk, current_metadata, current_section, current_subsection, source_info, len(chunks)))
            
            # Start new chunk
            current_chunk = line.strip()[9:].strip()  # Remove "- Chunk::"
            current_metadata = []
            continue
            
        # Check for metadata lines
        if (line.strip().startswith('- Topics::') or line.strip().startswith('- Concepts::') or \
            line.strip().startswith('- Themes::') or line.strip().startswith('- Function::') or \
            line.strip().startswith('- Scripture-References::') or line.strip().startswith('- Proper-Nouns::') or \
            line.strip().startswith('- **Topics:') or line.strip().startswith('- **Concepts:') or \
            line.strip().startswith('- **Themes:') or line.strip().startswith('- **Function:') or \
            line.strip().startswith('- **Scripture-References:') or line.strip().startswith('- **Proper-Nouns:')):
            current_metadata.append(line)
            continue
            
        # Check for function items (they start with - and contain [[)
        if current_chunk is not None and line.strip().startswith('- [[') and '[[' in line:
            current_metadata.append(line)
            continue
            
        # If we're in a chunk, add to chunk content
        if current_chunk is not None and line.strip() and not line.strip().startswith('- '):
            current_chunk += ' ' + line.strip()
    
    # Process the last chunk
    if current_chunk is not None:
        chunks.append(process_chunk(current_chunk, current_metadata, current_section, current_subsection, source_info, len(chunks)))
    
    return chunks

def process_chunk(chunk_content, metadata_lines, section, subsection, source_info, chunk_index):
    """Process a single chunk and return the chunk dictionary."""
    if not chunk_content.strip():
        return None
        
    # Parse metadata
    metadata_text = '\n'.join(metadata_lines)
    metadata = parse_chunk_metadata(metadata_text)
    
    # Build structure path
    structure_parts = [source_info.get('title', 'Unknown')]
    if section:
        structure_parts.append(section)
    if subsection:
        structure_parts.append(subsection)
    
    structure_path = ' > '.join(structure_parts)
    metadata['structure_path'] = [structure_path]
    
    return {
        'id': f"{source_info.get('title', 'unknown')}_{chunk_index}",
        'text': chunk_content.strip(),
        'source': source_info.get('title', 'Unknown'),
        'author': source_info.get('author', 'Unknown'),
        'metadata': metadata
    }

def convert_all_markdown_files(input_dir, output_file):
    """Convert all markdown files in a directory to JSONL."""
    all_chunks = []
    
    for md_file in Path(input_dir).glob('*.md'):
        print(f"Processing {md_file.name}...")
        chunks = extract_chunks_from_markdown(md_file)
        all_chunks.extend(chunks)
        print(f"  Extracted {len(chunks)} chunks")
    
    # Write to JSONL
    with open(output_file, 'w', encoding='utf-8') as f:
        for chunk in all_chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + '\n')
    
    print(f"\nTotal: {len(all_chunks)} chunks written to {output_file}")

if __name__ == "__main__":
    # Process files from the Markdown Source Files directory
    input_directory = "Markdown Source Files"  # Directory with .md files
    output_file = "theological_chunks.jsonl"
    
    convert_all_markdown_files(input_directory, output_file)