#!/usr/bin/env python3
"""
Add namespacing to terms in ORTHODOX_CHESTE annotations.

This script:
1. Backs up the original annotated file
2. Processes each chunk to add [[Concept/Term]] namespacing to terms
3. Updates the annotated, complete, and deployed versions
"""

import json
import os
import shutil
from pathlib import Path
from datetime import datetime
import anthropic
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# File paths
BASE_DIR = Path("theological_processing")
ANNOTATED_FILE = BASE_DIR / "03_annotated" / "ORTHODOX_CHESTE_annotated.jsonl"
COMPLETE_FILE = BASE_DIR / "04_complete" / "ORTHODOX_CHESTE_complete.jsonl"
DEPLOYED_FILE = BASE_DIR / "05_deployed" / "ORTHODOX_CHESTE_complete.jsonl"

# Initialize Anthropic client
api_key = os.getenv('ANTHROPIC_API_KEY')
if not api_key:
    raise ValueError("ANTHROPIC_API_KEY not found. Please set it in your .env file.")

client = anthropic.Anthropic(api_key=api_key)


def backup_file(file_path: Path) -> Path:
    """Create a timestamped backup of the file."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = file_path.parent / f"{file_path.stem}_backup_{timestamp}{file_path.suffix}"
    shutil.copy2(file_path, backup_path)
    print(f"✓ Backed up {file_path.name} → {backup_path.name}")
    return backup_path


def add_namespacing_to_terms(concepts: list, terms: list) -> list:
    """
    Use Claude to add namespacing to terms based on concepts.
    
    Returns: List of namespaced terms in [[Concept/Term]] format
    """
    if not terms:
        return []
    
    if not concepts:
        # If no concepts, we can't namespace properly - skip these
        print("  ⚠️  Warning: No concepts found, cannot namespace terms")
        return terms
    
    # Build prompt
    concepts_str = ', '.join(concepts)
    terms_str = '\n'.join([f'  - "{term}"' for term in terms])
    
    prompt = f"""Update the terms for this theological text chunk by adding namespacing based on the concepts assigned to this chunk.

Concepts: {concepts_str}

Current terms (without namespacing):
{terms_str}

Your task:
1. Match each term to the most appropriate concept(s)
2. Format each term as [[Concept/Term]]
3. If a term relates to multiple concepts, choose the primary/most relevant one
4. Return ONLY the updated terms in the same order, one per line, in the format: [[Concept/Term]]

Output format:
[[Concept1/Term1]]
[[Concept2/Term2]]
[[Concept1/Term3]]
..."""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            temperature=0.1,  # Low temperature for consistent formatting
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )
        
        response_text = message.content[0].text.strip()
        
        # Parse the response - extract namespaced terms
        namespaced_terms = []
        for line in response_text.split('\n'):
            line = line.strip()
            # Look for [[Concept/Term]] pattern
            if line.startswith('[[') and line.endswith(']]'):
                # Extract the content
                content = line[2:-2]  # Remove [[ and ]]
                if '/' in content:
                    namespaced_terms.append(f"[[{content}]]")
                else:
                    # If no slash, it might be malformed - try to match to first concept
                    namespaced_terms.append(f"[[{concepts[0]}/{content}]]")
        
        # Ensure we have the same number of terms
        if len(namespaced_terms) != len(terms):
            print(f"  ⚠️  Warning: Expected {len(terms)} terms, got {len(namespaced_terms)}")
            # If we got fewer, pad with namespaced versions
            if len(namespaced_terms) < len(terms):
                for i in range(len(namespaced_terms), len(terms)):
                    # Match to first concept if we're missing terms
                    namespaced_terms.append(f"[[{concepts[0]}/{terms[i]}]]")
            else:
                # Take only the first len(terms)
                namespaced_terms = namespaced_terms[:len(terms)]
        
        return namespaced_terms
        
    except Exception as e:
        print(f"  ❌ Error processing terms: {e}")
        # Fallback: manually namespace to first concept
        return [f"[[{concepts[0]}/{term}]]" for term in terms] if concepts else terms


def process_file(file_path: Path, is_complete_or_deployed: bool = False) -> tuple:
    """
    Process a JSONL file to add namespacing to terms.
    
    Returns: (updated_chunks, stats)
    """
    print(f"\nProcessing {file_path.name}...")
    
    if not file_path.exists():
        print(f"  ⚠️  File not found: {file_path}")
        return [], {'processed': 0, 'skipped': 0, 'errors': 0}
    
    chunks = []
    stats = {'processed': 0, 'skipped': 0, 'errors': 0}
    
    # Load chunks
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                chunks.append(json.loads(line))
    
    print(f"  Found {len(chunks)} chunks")
    
    # Process each chunk
    updated_chunks = []
    for idx, chunk in enumerate(chunks, 1):
        metadata = chunk.get('metadata', {})
        concepts = metadata.get('concepts', [])
        terms = metadata.get('terms', [])
        
        if not terms:
            # No terms to update
            updated_chunks.append(chunk)
            stats['skipped'] += 1
            if idx % 50 == 0:
                print(f"  Processed {idx}/{len(chunks)} chunks...")
            continue
        
        # Check if terms already have namespacing
        if terms and all(term.startswith('[[') and '/' in term and term.endswith(']]') for term in terms):
            # Already namespaced
            updated_chunks.append(chunk)
            stats['skipped'] += 1
            if idx % 50 == 0:
                print(f"  Processed {idx}/{len(chunks)} chunks...")
            continue
        
        if idx % 10 == 0 or idx == 1:
            print(f"  Processing chunk {idx}/{len(chunks)}...")
        
        try:
            # Add namespacing
            namespaced_terms = add_namespacing_to_terms(concepts, terms)
            
            # Update chunk
            updated_chunk = chunk.copy()
            updated_chunk['metadata'] = metadata.copy()
            updated_chunk['metadata']['terms'] = namespaced_terms
            
            # Add processing note
            if 'processing_notes' not in updated_chunk:
                updated_chunk['processing_notes'] = []
            if not isinstance(updated_chunk['processing_notes'], list):
                updated_chunk['processing_notes'] = [updated_chunk['processing_notes']]
            updated_chunk['processing_notes'].append(f"Terms namespaced on {datetime.now().isoformat()}")
            
            updated_chunks.append(updated_chunk)
            stats['processed'] += 1
            
        except Exception as e:
            print(f"  ❌ Error processing chunk {idx}: {e}")
            updated_chunks.append(chunk)  # Keep original
            stats['errors'] += 1
    
    return updated_chunks, stats


def save_chunks(chunks: list, file_path: Path):
    """Save chunks to JSONL file."""
    with open(file_path, 'w', encoding='utf-8') as f:
        for chunk in chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + '\n')


def main():
    print("=" * 70)
    print("Adding Namespacing to Terms - ORTHODOX_CHESTE")
    print("=" * 70)
    
    # Step 1: Backup files
    print("\n1. Creating backups...")
    backup_paths = []
    
    if ANNOTATED_FILE.exists():
        backup_paths.append(backup_file(ANNOTATED_FILE))
    if COMPLETE_FILE.exists():
        backup_paths.append(backup_file(COMPLETE_FILE))
    if DEPLOYED_FILE.exists():
        backup_paths.append(backup_file(DEPLOYED_FILE))
    
    print(f"\n✓ Created {len(backup_paths)} backup(s)")
    
    # Step 2: Process annotated file
    if not ANNOTATED_FILE.exists():
        print(f"\n❌ Error: {ANNOTATED_FILE} not found!")
        return
    
    annotated_chunks, annotated_stats = process_file(ANNOTATED_FILE)
    
    if annotated_chunks:
        save_chunks(annotated_chunks, ANNOTATED_FILE)
        print(f"\n✓ Updated {ANNOTATED_FILE.name}")
        print(f"  Stats: {annotated_stats['processed']} processed, {annotated_stats['skipped']} skipped, {annotated_stats['errors']} errors")
    
    # Step 3: Process complete file (if exists)
    if COMPLETE_FILE.exists():
        complete_chunks, complete_stats = process_file(COMPLETE_FILE, is_complete_or_deployed=True)
        
        if complete_chunks:
            save_chunks(complete_chunks, COMPLETE_FILE)
            print(f"\n✓ Updated {COMPLETE_FILE.name}")
            print(f"  Stats: {complete_stats['processed']} processed, {complete_stats['skipped']} skipped, {complete_stats['errors']} errors")
    
    # Step 4: Process deployed file (if exists)
    if DEPLOYED_FILE.exists():
        deployed_chunks, deployed_stats = process_file(DEPLOYED_FILE, is_complete_or_deployed=True)
        
        if deployed_chunks:
            save_chunks(deployed_chunks, DEPLOYED_FILE)
            print(f"\n✓ Updated {DEPLOYED_FILE.name}")
            print(f"  Stats: {deployed_stats['processed']} processed, {deployed_stats['skipped']} skipped, {deployed_stats['errors']} errors")
    
    print("\n" + "=" * 70)
    print("✓ Processing complete!")
    print("=" * 70)
    print(f"\nBackups saved at:")
    for backup in backup_paths:
        print(f"  - {backup}")


if __name__ == '__main__':
    main()

