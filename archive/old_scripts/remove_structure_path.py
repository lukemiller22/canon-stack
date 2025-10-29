#!/usr/bin/env python3
"""
Remove top-level 'structure_path' field from annotated JSONL file.
Keeps structure_path in metadata section only.
"""

import json
import sys
from pathlib import Path

def remove_top_level_structure_path(input_file: str, output_file: str = None):
    """Remove top-level structure_path from each line in JSONL file."""
    input_path = Path(input_file)
    
    if not input_path.exists():
        print(f"Error: File not found: {input_file}")
        sys.exit(1)
    
    # Use input file as output if no output specified (backup first)
    if output_file is None:
        output_path = input_path
        # Create backup
        backup_path = input_path.with_suffix('.jsonl.backup')
        print(f"Creating backup: {backup_path}")
        backup_path.write_text(input_path.read_text())
    else:
        output_path = Path(output_file)
    
    print(f"Processing: {input_path}")
    
    # Read all chunks first
    chunks = []
    lines_processed = 0
    lines_modified = 0
    
    with open(input_path, 'r', encoding='utf-8') as f_in:
        for line in f_in:
            if not line.strip():
                continue
            
            try:
                chunk = json.loads(line)
                lines_processed += 1
                
                # Remove top-level structure_path if it exists
                if 'structure_path' in chunk:
                    del chunk['structure_path']
                    lines_modified += 1
                
                chunks.append(chunk)
                
            except json.JSONDecodeError as e:
                print(f"Error parsing line {lines_processed + 1}: {e}")
                # Skip invalid lines
    
    # Write all cleaned chunks
    with open(output_path, 'w', encoding='utf-8') as f_out:
        for chunk in chunks:
            f_out.write(json.dumps(chunk, ensure_ascii=False) + '\n')
    
    print(f"✓ Processed {lines_processed} chunks")
    print(f"✓ Removed top-level structure_path from {lines_modified} chunks")
    print(f"✓ Output: {output_path}")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python remove_structure_path.py <input_file.jsonl> [output_file.jsonl]")
        print("  If output_file is not specified, input_file will be modified in-place (with backup)")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    remove_top_level_structure_path(input_file, output_file)

