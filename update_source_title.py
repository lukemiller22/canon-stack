#!/usr/bin/env python3
"""
Update the source title across all pipeline stages for a given source.

Usage:
    python update_source_title.py <source_id> <new_title>
    
Example:
    python update_source_title.py MERE_CHRISTIANITY___C__S__LEWIS "Mere Christianity"
"""

import json
import sys
from pathlib import Path
from datetime import datetime
import shutil

def update_source_in_file(file_path: Path, old_title: str, new_title: str) -> tuple[int, bool]:
    """
    Update source title in a JSONL file.
    Returns: (chunks_updated, file_modified)
    """
    if not file_path.exists():
        print(f"  ⚠️  File not found: {file_path}")
        return 0, False
    
    # Create backup
    backup_path = file_path.parent / f"{file_path.name}.backup"
    if file_path.exists():
        shutil.copy2(file_path, backup_path)
    
    chunks_updated = 0
    updated_chunks = []
    
    # Read and update chunks
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                chunk = json.loads(line.strip())
                if chunk.get('source') == old_title:
                    chunk['source'] = new_title
                    chunks_updated += 1
                updated_chunks.append(chunk)
    
    # Write updated chunks back
    if chunks_updated > 0:
        # Determine field order based on stage
        stage = None
        if '02_chunked' in str(file_path):
            stage = 2
        elif '03_annotated' in str(file_path):
            stage = 3
        elif '04_complete' in str(file_path) or '05_deployed' in str(file_path):
            stage = 4
        
        field_order = ['id', 'structure_path', 'text', 'source', 'author', 'chunk_type', 'chunk_index', 
                       'processing_stage', 'processing_timestamp']
        
        if stage == 3:
            field_order = ['id', 'structure_path', 'text', 'source', 'author', 'chunk_type', 'chunk_index', 
                          'processing_stage', 'processing_timestamp', 'metadata']
            if any('annotation_method' in chunk for chunk in updated_chunks):
                field_order.extend(['annotation_method', 'annotation_model'])
        
        if stage == 4:
            field_order = ['id', 'structure_path', 'text', 'source', 'author', 'chunk_type', 'chunk_index', 
                          'processing_stage', 'processing_timestamp', 'metadata']
            if any('annotation_method' in chunk for chunk in updated_chunks):
                field_order.extend(['annotation_method', 'annotation_model'])
            if any('embedding' in chunk for chunk in updated_chunks):
                field_order.extend(['embedding', 'embedding_model'])
        
        def reorder_chunk(chunk):
            """Reorder chunk fields to match original format"""
            ordered_chunk = {}
            for field in field_order:
                if field in chunk:
                    ordered_chunk[field] = chunk[field]
            # Add any remaining fields
            for key, value in chunk.items():
                if key not in ordered_chunk:
                    ordered_chunk[key] = value
            return ordered_chunk
        
        with open(file_path, 'w', encoding='utf-8') as f:
            for chunk in updated_chunks:
                ordered_chunk = reorder_chunk(chunk)
                f.write(json.dumps(ordered_chunk, ensure_ascii=False) + '\n')
        
        return chunks_updated, True
    
    return 0, False

def main():
    if len(sys.argv) < 3:
        print("Usage: python update_source_title.py <source_id> <new_title>")
        print("\nExample:")
        print('  python update_source_title.py MERE_CHRISTIANITY___C__S__LEWIS "Mere Christianity"')
        sys.exit(1)
    
    source_id = sys.argv[1]
    new_title = sys.argv[2]
    
    base_dir = Path(__file__).parent / 'theological_processing'
    
    # Files to update
    files_to_update = [
        base_dir / '02_chunked' / f"{source_id}_chunks.jsonl",
        base_dir / '03_annotated' / f"{source_id}_annotated.jsonl",
        base_dir / '04_complete' / f"{source_id}_complete.jsonl",
        base_dir / '05_deployed' / f"{source_id}_complete.jsonl",
    ]
    
    print(f"Updating source title to: '{new_title}'")
    print(f"Source ID: {source_id}\n")
    
    # First, check what the current title is
    sample_file = files_to_update[0]
    if sample_file.exists():
        with open(sample_file, 'r', encoding='utf-8') as f:
            first_line = f.readline()
            if first_line.strip():
                sample_chunk = json.loads(first_line.strip())
                old_title = sample_chunk.get('source', '')
                print(f"Current title: '{old_title}'")
                print(f"New title: '{new_title}'\n")
            else:
                print("⚠️  Could not determine current title")
                old_title = None
    else:
        print("⚠️  Could not find sample file to determine current title")
        old_title = None
    
    if old_title and old_title == new_title:
        print("Title is already set to the new value. No changes needed.")
        return
    
    total_updated = 0
    files_modified = []
    
    for file_path in files_to_update:
        stage_name = file_path.parent.name
        print(f"Processing {stage_name}/{file_path.name}...")
        
        if old_title:
            chunks_updated, was_modified = update_source_in_file(file_path, old_title, new_title)
            if chunks_updated > 0:
                print(f"  ✓ Updated {chunks_updated} chunks")
                total_updated += chunks_updated
                files_modified.append(str(file_path))
            elif file_path.exists():
                print(f"  ⚠️  No chunks found with source '{old_title}'")
            else:
                print(f"  ⚠️  File does not exist (skipping)")
        else:
            print(f"  ⚠️  Skipping (could not determine old title)")
    
    print(f"\n✅ Total chunks updated: {total_updated}")
    print(f"✅ Files modified: {len(files_modified)}")
    if files_modified:
        print("\nModified files:")
        for f in files_modified:
            print(f"  - {f}")

if __name__ == '__main__':
    main()

