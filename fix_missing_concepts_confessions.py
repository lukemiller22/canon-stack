#!/usr/bin/env python3
"""
Fix missing concepts in THECONFE_AUGUST annotated chunks by deriving them from topics and terms.
"""

import json
from pathlib import Path
from pipeline_manager import TheologicalProcessingPipeline

def derive_concepts_from_metadata(chunk, valid_concepts):
    """Derive concepts from topics and terms if concepts are missing."""
    metadata = chunk.get('metadata', {})
    concepts = metadata.get('concepts', [])
    
    if concepts:
        return concepts  # Already has concepts
    
    derived_concepts = set()
    
    # Extract concepts from topics (format: Concept/Topic)
    for topic in metadata.get('topics', []):
        if '/' in topic:
            concept = topic.split('/', 1)[0]
            if concept in valid_concepts:
                derived_concepts.add(concept)
    
    # Extract concepts from terms (format: Concept/Term)
    for term in metadata.get('terms', []):
        if '/' in term:
            concept = term.split('/', 1)[0]
            if concept in valid_concepts:
                derived_concepts.add(concept)
    
    return list(derived_concepts) if derived_concepts else []

def main():
    pipeline = TheologicalProcessingPipeline()
    indexes = pipeline._load_indexes()
    valid_concepts = indexes.get('concepts_set', set())
    
    annotated_file = Path('theological_processing/03_annotated/THECONFE_AUGUST_annotated.jsonl')
    
    # Load chunks
    with open(annotated_file, 'r', encoding='utf-8') as f:
        chunks = [json.loads(line) for line in f]
    
    print(f"Processing {len(chunks)} chunks...")
    
    fixed_count = 0
    for chunk in chunks:
        original_concepts = chunk.get('metadata', {}).get('concepts', [])
        derived_concepts = derive_concepts_from_metadata(chunk, valid_concepts)
        
        if not original_concepts and derived_concepts:
            chunk['metadata']['concepts'] = derived_concepts
            fixed_count += 1
    
    print(f"Fixed {fixed_count} chunks with derived concepts")
    print(f"Chunks that already had concepts: {len(chunks) - fixed_count}")
    
    # Backup original
    backup_file = annotated_file.parent / f"{annotated_file.stem}_backup_before_concept_fix{annotated_file.suffix}"
    with open(backup_file, 'w', encoding='utf-8') as f:
        with open(annotated_file, 'r', encoding='utf-8') as orig:
            f.write(orig.read())
    print(f"Backup saved to: {backup_file}")
    
    # Write fixed chunks
    with open(annotated_file, 'w', encoding='utf-8') as f:
        for chunk in chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + '\n')
    
    print(f"✓ Updated {annotated_file}")
    
    # Stats
    with_concepts = sum(1 for c in chunks if c.get('metadata', {}).get('concepts'))
    without_concepts = len(chunks) - with_concepts
    print(f"\nFinal stats:")
    print(f"  Chunks with concepts: {with_concepts}")
    print(f"  Chunks without concepts: {without_concepts}")

if __name__ == '__main__':
    main()

