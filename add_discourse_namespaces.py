#!/usr/bin/env python3
"""
Add namespace labels to discourse elements in annotated chunks.

For each discourse element like "[[Narrative/Time]] description",
this script adds "[[Narrative]]" as a separate discourse element
so users can filter by the general category.
"""

import json
import re
from pathlib import Path
from typing import List, Dict

def extract_namespace_from_element(element: str) -> str:
    """Extract the namespace (category) from a discourse element string.
    
    Args:
        element: Discourse element string like "[[Narrative/Time]] description"
        
    Returns:
        Namespace string like "Narrative" or None if no namespace found
    """
    # Match pattern like [[Category/Element]] or [[Category]]
    match = re.search(r'\[\[([^\]]+)\]\]', element)
    if match:
        full_tag = match.group(1)
        # If it contains a slash, extract the part before it
        if '/' in full_tag:
            namespace = full_tag.split('/', 1)[0]
            return namespace
    return None

def add_namespace_labels(chunks: List[Dict]) -> List[Dict]:
    """Add namespace labels to discourse elements in chunks.
    
    For each discourse element with a namespace (e.g., "[[Narrative/Time]] ..."),
    adds the namespace itself (e.g., "[[Narrative]]") if not already present.
    
    Args:
        chunks: List of chunk dictionaries
        
    Returns:
        Updated chunks with namespace labels added
    """
    updated_chunks = []
    
    for chunk in chunks:
        metadata = chunk.get('metadata', {})
        discourse_elements = metadata.get('discourse_elements', [])
        
        if not discourse_elements:
            updated_chunks.append(chunk)
            continue
        
        # Extract namespaces from existing elements
        namespaces_to_add = set()
        
        for element in discourse_elements:
            namespace = extract_namespace_from_element(element)
            if namespace:
                # Create namespace-only element string
                namespace_element = f"[[{namespace}]]"
                
                # Check if this exact namespace element already exists in the list
                # (not just if any element starts with that namespace)
                namespace_exists = False
                for existing_element in discourse_elements:
                    # Extract tag from existing element
                    match = re.search(r'\[\[([^\]]+)\]\]', existing_element)
                    if match:
                        existing_tag = match.group(1)
                        # Check if it's exactly the namespace (not a sub-element)
                        if existing_tag == namespace:
                            namespace_exists = True
                            break
                
                if not namespace_exists:
                    namespaces_to_add.add(namespace_element)
        
        # Add namespace elements to the discourse_elements list
        if namespaces_to_add:
            # Add them at the beginning, sorted
            new_elements = sorted(list(namespaces_to_add))
            # Ensure we don't duplicate if somehow the namespace already exists in a different format
            updated_discourse_elements = []
            existing_tags = set()
            
            # First, add all existing elements and track their tags
            for element in discourse_elements:
                match = re.search(r'\[\[([^\]]+)\]\]', element)
                if match:
                    existing_tags.add(match.group(1))
                updated_discourse_elements.append(element)
            
            # Add namespace elements that don't already exist
            for namespace_element in new_elements:
                namespace_tag = namespace_element.replace('[[', '').replace(']]', '')
                if namespace_tag not in existing_tags:
                    updated_discourse_elements.insert(0, namespace_element)  # Insert at beginning
            
            # Update the chunk
            updated_metadata = metadata.copy()
            updated_metadata['discourse_elements'] = updated_discourse_elements
            
            updated_chunk = chunk.copy()
            updated_chunk['metadata'] = updated_metadata
            
            # Add a processing note
            if 'processing_notes' not in updated_chunk:
                updated_chunk['processing_notes'] = []
            updated_chunk['processing_notes'].append('Discourse namespace labels added')
            
            updated_chunks.append(updated_chunk)
            print(f"  ✓ Updated chunk {chunk.get('id', 'unknown')}: Added {len(new_elements)} namespace label(s)")
        else:
            updated_chunks.append(chunk)
    
    return updated_chunks

def process_file(file_path: Path, output_path: Path = None):
    """Process a single JSONL file to add namespace labels.
    
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
    
    updated_chunks = add_namespace_labels(chunks)
    
    # Write updated chunks
    with open(output_path, 'w', encoding='utf-8') as f:
        for chunk in updated_chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + '\n')
    
    print(f"  ✓ Saved {len(updated_chunks)} chunks to {output_path.name}")

def main():
    """Main function to process all annotated JSONL files."""
    script_dir = Path(__file__).parent
    annotated_dir = script_dir / 'theological_processing' / '03_annotated'
    
    if not annotated_dir.exists():
        print(f"Error: Annotated directory not found: {annotated_dir}")
        return
    
    # Find all annotated JSONL files (exclude backup and approved files)
    jsonl_files = [
        f for f in annotated_dir.glob('*.jsonl')
        if 'backup' not in f.name.lower() and not f.name.endswith('.approved')
    ]
    
    if not jsonl_files:
        print(f"No annotated JSONL files found in {annotated_dir}")
        return
    
    print(f"Found {len(jsonl_files)} annotated file(s) to process\n")
    
    for jsonl_file in jsonl_files:
        process_file(jsonl_file)
        print()
    
    print("Done! All files processed.")

if __name__ == '__main__':
    main()

