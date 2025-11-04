#!/usr/bin/env python3
"""
Add discourse_tags field to chunks by extracting tags from discourse_elements.

This creates a separate metadata field containing just the discourse tags
(e.g., "Symbolic", "Symbolic/Metaphor") for efficient filtering, while
keeping discourse_elements with their full descriptions.
"""

import json
import re
from pathlib import Path
from typing import List, Dict

def extract_discourse_tags(discourse_elements: List[str]) -> List[str]:
    """Extract unique discourse tags from discourse_elements strings.
    
    Args:
        discourse_elements: List of discourse element strings like
            ["[[Symbolic/Metaphor]] description", "[[Symbolic]]", ...]
            
    Returns:
        List of unique tags like ["Symbolic", "Symbolic/Metaphor", ...]
    """
    tags = set()
    
    for element in discourse_elements:
        # Extract tag from brackets (e.g., "[[Logical/Claim]] description" -> "Logical/Claim")
        match = re.search(r'\[\[([^\]]+)\]\]', element)
        if match:
            tag = match.group(1)
            tags.add(tag)
    
    # Sort for consistency
    return sorted(list(tags))

def add_discourse_tags_to_chunks(chunks: List[Dict]) -> List[Dict]:
    """Add discourse_tags field to chunks.
    
    Args:
        chunks: List of chunk dictionaries
        
    Returns:
        Updated chunks with discourse_tags field
    """
    updated_chunks = []
    
    for chunk in chunks:
        metadata = chunk.get('metadata', {})
        discourse_elements = metadata.get('discourse_elements', [])
        
        # Extract tags from discourse_elements
        discourse_tags = extract_discourse_tags(discourse_elements)
        
        # Update metadata
        updated_metadata = metadata.copy()
        updated_metadata['discourse_tags'] = discourse_tags
        
        # Update chunk
        updated_chunk = chunk.copy()
        updated_chunk['metadata'] = updated_metadata
        
        # Add processing note
        if 'processing_notes' not in updated_chunk:
            updated_chunk['processing_notes'] = []
        updated_chunk['processing_notes'].append('Discourse tags extracted')
        
        updated_chunks.append(updated_chunk)
    
    return updated_chunks

def process_file(file_path: Path, output_path: Path = None):
    """Process a single JSONL file to add discourse_tags.
    
    Args:
        file_path: Path to input JSONL file
        output_path: Path to output JSONL file (if None, overwrites input)
    """
    if output_path is None:
        output_path = file_path
    
    print(f"Processing {file_path.name}...")
    
    chunks = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                chunks.append(json.loads(line))
    
    print(f"  Loaded {len(chunks)} chunks")
    
    updated_chunks = add_discourse_tags_to_chunks(chunks)
    
    # Write updated chunks
    with open(output_path, 'w', encoding='utf-8') as f:
        for chunk in updated_chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + '\n')
    
    print(f"  ✓ Saved {len(updated_chunks)} chunks to {output_path.name}")

def main():
    """Main function to process all JSONL files across stages."""
    script_dir = Path(__file__).parent
    processing_dir = script_dir / 'theological_processing'
    
    # Process files in these stages
    stages = ['03_annotated', '04_complete', '05_deployed']
    
    for stage in stages:
        stage_dir = processing_dir / stage
        
        if not stage_dir.exists():
            print(f"Skipping {stage} - directory not found")
            continue
        
        # Find all JSONL files (exclude backup and approved files)
        jsonl_files = [
            f for f in stage_dir.glob('*.jsonl')
            if 'backup' not in f.name.lower() and not f.name.endswith('.approved')
        ]
        
        if not jsonl_files:
            print(f"No files found in {stage}")
            continue
        
        print(f"\n=== Processing {stage} ===")
        
        for jsonl_file in jsonl_files:
            process_file(jsonl_file)
        
        print()
    
    print("Done! All files processed.")

if __name__ == '__main__':
    main()

