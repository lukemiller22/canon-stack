#!/usr/bin/env python3
"""
Fix chunks without concepts by assigning proper concepts and ensuring topics/terms are correctly namespaced.

This script:
1. Identifies chunks that have no concepts or have topics/terms using invalid concept namespaces
2. Re-processes them with Claude Sonnet to assign valid concepts
3. Ensures topics and terms are properly namespaced under assigned concepts
"""

import json
import os
import re
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
CONCEPTS_INDEX = Path("Index: Concepts.md")

# Initialize Anthropic client
api_key = os.getenv('ANTHROPIC_API_KEY')
if not api_key:
    raise ValueError("ANTHROPIC_API_KEY not found. Please set it in your .env file.")

client = anthropic.Anthropic(api_key=api_key)


def load_valid_concepts() -> list:
    """Load valid concepts from the Concepts index."""
    concepts = []
    if CONCEPTS_INDEX.exists():
        with open(CONCEPTS_INDEX, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # Look for [[Concept/ConceptName]] format
                match = re.search(r'\[\[Concept/([^\]]+)\]\]', line)
                if match:
                    concepts.append(match.group(1))
    return concepts


def get_invalid_namespaces(chunk: dict, valid_concepts: list) -> dict:
    """Check if chunk has invalid concept namespaces in topics/terms."""
    metadata = chunk.get('metadata', {})
    concepts = metadata.get('concepts', [])
    topics = metadata.get('topics', [])
    terms = metadata.get('terms', [])
    
    invalid_topics = []
    invalid_terms = []
    
    # Check topics for invalid concept namespaces
    for topic in topics:
        if '/' in topic:
            concept_part = topic.split('/', 1)[0]
            # Remove [[ and ]] if present
            concept_part = concept_part.replace('[[', '').replace(']]', '')
            if concept_part not in valid_concepts:
                invalid_topics.append(topic)
    
    # Check terms for invalid concept namespaces
    for term in terms:
        if '/' in term:
            concept_part = term.split('/', 1)[0]
            # Remove [[ and ]] if present
            concept_part = concept_part.replace('[[', '').replace(']]', '')
            if concept_part not in valid_concepts:
                invalid_terms.append(term)
    
    return {
        'has_no_concepts': len(concepts) == 0,
        'has_invalid_topics': len(invalid_topics) > 0,
        'has_invalid_terms': len(invalid_terms) > 0,
        'invalid_topics': invalid_topics,
        'invalid_terms': invalid_terms
    }


def fix_chunk(chunk: dict, valid_concepts: list, line_num: int) -> dict:
    """Re-process chunk to assign valid concepts and fix namespacing."""
    metadata = chunk.get('metadata', {})
    text = chunk.get('text', '')
    current_concepts = metadata.get('concepts', [])
    current_topics = metadata.get('topics', [])
    current_terms = metadata.get('terms', [])
    structure_path = metadata.get('structure_path', '')
    
    # Build prompt
    concepts_list = ', '.join([f'[[Concept/{c}]]' for c in valid_concepts])
    
    # Show current state
    current_concepts_str = ', '.join(current_concepts) if current_concepts else 'NONE'
    current_topics_str = '\n'.join([f'  - {t}' for t in current_topics[:10]]) if current_topics else '  (none)'
    if len(current_topics) > 10:
        current_topics_str += f'\n  ... and {len(current_topics) - 10} more'
    
    current_terms_str = '\n'.join([f'  - {t}' for t in current_terms[:10]]) if current_terms else '  (none)'
    if len(current_terms) > 10:
        current_terms_str += f'\n  ... and {len(current_terms) - 10} more'
    
    prompt = f"""You are fixing metadata for a theological text chunk. This chunk currently has NO CONCEPTS assigned, which is incorrect. EVERY chunk must have at least one concept.

Text chunk (excerpt): {text[:500]}...

Current metadata:
- Concepts: {current_concepts_str}
- Structure Path: {structure_path}
- Topics: 
{current_topics_str}
- Terms:
{current_terms_str}

CRITICAL REQUIREMENTS:

1. CONCEPTS: You MUST assign at least 1-3 concepts from this EXACT list (NO additions, NO substitutions):
{concepts_list}

2. TOPICS: All topics must use namespaced format [[Concept/Topic]] where "Concept" is one of the concepts you assigned above. If a topic references a concept not in your assigned concepts, fix it to use one of your assigned concepts.

3. TERMS: All terms must use namespaced format [[Concept/Term]] where "Concept" is one of the concepts you assigned above.

Output your response in this exact format:
concepts:: [[Concept1]], [[Concept2]]
topics:: [[Concept1/Topic1]], [[Concept2/Topic2]]
terms:: [[Concept1/Term1]], [[Concept2/Term2]]

IMPORTANT: Only use concepts from the fixed list above. Do NOT create new concepts."""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            temperature=0.2,
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )
        
        response_text = message.content[0].text.strip()
        
        # Parse response
        concepts = []
        topics = []
        terms = []
        
        # Extract concepts
        concepts_match = re.search(r'concepts::\s*(.+)', response_text, re.IGNORECASE | re.MULTILINE)
        if concepts_match:
            concepts_str = concepts_match.group(1).strip()
            extracted = re.findall(r'\[\[Concept/([^\]]+)\]\]', concepts_str)
            # Validate against valid concepts list
            concepts = [c for c in extracted if c in valid_concepts]
        
        # Extract topics
        topics_match = re.search(r'topics::\s*(.+)', response_text, re.IGNORECASE | re.MULTILINE)
        if topics_match:
            topics_str = topics_match.group(1).strip()
            topics_raw = re.findall(r'\[\[([^\]]+)\]\]', topics_str)
            # Remove "Concept/" prefix if present
            topics = []
            for topic in topics_raw:
                if topic.startswith('Concept/'):
                    topic = topic.replace('Concept/', '', 1)
                topics.append(topic)
        
        # Extract terms
        terms_match = re.search(r'terms::\s*(.+)', response_text, re.IGNORECASE | re.MULTILINE)
        if terms_match:
            terms_str = terms_match.group(1).strip()
            terms_raw = re.findall(r'\[\[([^\]]+)\]\]', terms_str)
            # Remove "Concept/" prefix if present
            terms = []
            for term in terms_raw:
                if term.startswith('Concept/'):
                    term = term.replace('Concept/', '', 1)
                terms.append(term)
        
        # Ensure we have at least one concept
        if not concepts:
            print(f"  ⚠️  Warning: No valid concepts assigned for chunk at line {line_num}, using fallback")
            # Try to infer from topics/terms
            if topics:
                first_topic_concept = topics[0].split('/')[0] if '/' in topics[0] else None
                if first_topic_concept and first_topic_concept in valid_concepts:
                    concepts = [first_topic_concept]
            if not concepts and terms:
                first_term_concept = terms[0].split('/')[0] if '/' in terms[0] else None
                if first_term_concept and first_term_concept in valid_concepts:
                    concepts = [first_term_concept]
            if not concepts:
                # Last resort: use first valid concept
                concepts = [valid_concepts[0]] if valid_concepts else []
        
        # Update chunk
        updated_chunk = chunk.copy()
        updated_chunk['metadata'] = metadata.copy()
        updated_chunk['metadata']['concepts'] = concepts
        updated_chunk['metadata']['topics'] = topics
        updated_chunk['metadata']['terms'] = terms
        
        # Add processing note
        if 'processing_notes' not in updated_chunk:
            updated_chunk['processing_notes'] = []
        if not isinstance(updated_chunk['processing_notes'], list):
            updated_chunk['processing_notes'] = [updated_chunk['processing_notes']]
        updated_chunk['processing_notes'].append(f"Fixed concepts and namespacing on {datetime.now().isoformat()}")
        
        return updated_chunk
        
    except Exception as e:
        print(f"  ❌ Error processing chunk at line {line_num}: {e}")
        return chunk  # Return original on error


def main():
    print("=" * 70)
    print("Fixing Chunks Without Valid Concepts")
    print("=" * 70)
    
    # Load valid concepts
    print("\n1. Loading valid concepts from index...")
    valid_concepts = load_valid_concepts()
    print(f"   ✓ Loaded {len(valid_concepts)} valid concepts")
    
    if not valid_concepts:
        print("   ❌ Error: No valid concepts found!")
        return
    
    # Identify chunks that need fixing
    print("\n2. Identifying chunks that need fixing...")
    chunks_to_fix = []  # List of (line_num, chunk)
    
    if not ANNOTATED_FILE.exists():
        print(f"   ❌ Error: {ANNOTATED_FILE} not found!")
        return
    
    with open(ANNOTATED_FILE, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            if line.strip():
                chunk = json.loads(line)
                issues = get_invalid_namespaces(chunk, valid_concepts)
                
                if issues['has_no_concepts'] or issues['has_invalid_topics'] or issues['has_invalid_terms']:
                    chunks_to_fix.append((line_num, chunk, issues))
    
    print(f"   ✓ Found {len(chunks_to_fix)} chunks that need fixing")
    
    if not chunks_to_fix:
        print("\n✓ All chunks are valid!")
        return
    
    # Load all chunks from all three files
    print("\n3. Loading chunks from files...")
    
    def load_all_chunks(file_path: Path) -> list:
        chunks = []
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        chunks.append(json.loads(line))
        return chunks
    
    annotated_chunks = load_all_chunks(ANNOTATED_FILE)
    complete_chunks = load_all_chunks(COMPLETE_FILE)
    deployed_chunks = load_all_chunks(DEPLOYED_FILE)
    
    print(f"   Annotated: {len(annotated_chunks)} chunks")
    print(f"   Complete: {len(complete_chunks)} chunks")
    print(f"   Deployed: {len(deployed_chunks)} chunks")
    
    # Process chunks
    print(f"\n4. Processing {len(chunks_to_fix)} chunks with Claude Sonnet...")
    fixed_count = 0
    
    for line_num, chunk, issues in chunks_to_fix:
        chunk_idx = line_num - 1  # Convert to 0-based index
        print(f"\n   Chunk at line {line_num} (ID: {chunk.get('id', 'unknown')}):")
        print(f"     Issues: ", end="")
        issue_list = []
        if issues['has_no_concepts']:
            issue_list.append("no concepts")
        if issues['has_invalid_topics']:
            issue_list.append(f"invalid topics ({len(issues['invalid_topics'])})")
        if issues['has_invalid_terms']:
            issue_list.append(f"invalid terms ({len(issues['invalid_terms'])})")
        print(", ".join(issue_list))
        
        # Fix chunk
        fixed_chunk = fix_chunk(chunk, valid_concepts, line_num)
        
        # Update in all three arrays
        if chunk_idx < len(annotated_chunks):
            annotated_chunks[chunk_idx] = fixed_chunk
        if chunk_idx < len(complete_chunks):
            # Update metadata, keep embedding
            complete_chunks[chunk_idx]['metadata'] = fixed_chunk['metadata']
        if chunk_idx < len(deployed_chunks):
            # Update metadata, keep embedding
            deployed_chunks[chunk_idx]['metadata'] = fixed_chunk['metadata']
        
        fixed_count += 1
        print(f"     ✓ Fixed (assigned concepts: {fixed_chunk['metadata'].get('concepts', [])})")
    
    # Save updated files
    print(f"\n5. Saving updated files...")
    
    def save_chunks(chunks: list, file_path: Path):
        with open(file_path, 'w', encoding='utf-8') as f:
            for chunk in chunks:
                f.write(json.dumps(chunk, ensure_ascii=False) + '\n')
    
    save_chunks(annotated_chunks, ANNOTATED_FILE)
    print(f"   ✓ Updated {ANNOTATED_FILE.name}")
    
    if COMPLETE_FILE.exists():
        save_chunks(complete_chunks, COMPLETE_FILE)
        print(f"   ✓ Updated {COMPLETE_FILE.name}")
    
    if DEPLOYED_FILE.exists():
        save_chunks(deployed_chunks, DEPLOYED_FILE)
        print(f"   ✓ Updated {DEPLOYED_FILE.name}")
    
    print("\n" + "=" * 70)
    print(f"✓ Fixed {fixed_count} chunks!")
    print("=" * 70)


if __name__ == '__main__':
    main()

