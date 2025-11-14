import json
import re
from flask import Flask, request, jsonify, Response, stream_with_context
from openai import OpenAI
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import os
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
import time
import asyncio
import chromadb
from chromadb.config import Settings

# Load environment variables from .env file (look in parent directories too)
env_path = Path(__file__).parent / '.env'
if not env_path.exists():
    env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

app = Flask(__name__)

# Initialize OpenAI client
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY not found. Please set it in your .env file.")
client = OpenAI(api_key=api_key)

# Global variables
dataset = []
available_sources = []
valid_concepts = []
valid_discourse_elements = []
valid_scripture_references = set()
valid_named_entities = set()
valid_authors = set()
valid_sources = set()
chroma_client = None
chroma_collection = None

def load_schema_indices():
    """Load valid concepts and discourse elements from index files"""
    global valid_concepts, valid_discourse_elements
    
    script_dir = Path(__file__).parent
    
    # Load concepts from Concepts.md
    concepts_file = script_dir / 'Index: Concepts.md'
    valid_concepts = []
    if concepts_file.exists():
        with open(concepts_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith('- '):
                    concept = line[2:].strip()
                    concept = concept.replace('[[', '').replace(']]', '')
                    if concept.startswith('Concept/'):
                        concept = concept.replace('Concept/', '', 1)
                    valid_concepts.append(concept)
    
    # Load discourse elements from Function.md
    function_file = script_dir / 'Index: Function.md'
    valid_discourse_elements = []
    if function_file.exists():
        import re
        with open(function_file, 'r', encoding='utf-8') as f:
            content = f.read()
            # Extract all discourse tags like [[Semantic/Metaphor]], [[Logical/Claim]], etc.
            tags = re.findall(r'\[\[([^\]]+)\]\]', content)
            valid_discourse_elements = sorted(set(tags))
    
    print(f"✅ Loaded {len(valid_concepts)} concepts and {len(valid_discourse_elements)} discourse elements from schema indices")

def load_chromadb():
    """Initialize ChromaDB client and collection"""
    global chroma_client, chroma_collection
    
    script_dir = Path(__file__).parent
    chroma_db_path = script_dir / 'chroma_db'
    
    try:
        chroma_client = chromadb.PersistentClient(
            path=str(chroma_db_path),
            settings=Settings(anonymized_telemetry=False)
        )
        
        collection_name = "theological_corpus"
        chroma_collection = chroma_client.get_collection(name=collection_name)
        
        print(f"✅ ChromaDB initialized: {chroma_collection.count()} chunks in collection")
        return True
    except Exception as e:
        print(f"⚠️  ChromaDB initialization failed: {e}")
        print("   Make sure you've run migrate_to_chroma.py first!")
        return False

def load_dataset():
    """Load the theological chunks dataset from deployed sources"""
    global dataset, available_sources, valid_scripture_references, valid_named_entities, valid_authors, valid_sources
    
    # Get the path to deployed sources (relative to this file)
    script_dir = Path(__file__).parent
    deployed_dir = script_dir / 'theological_processing' / '05_deployed'
    
    if not deployed_dir.exists():
        print(f"Error: Deployed directory not found: {deployed_dir}")
        return False
    
    try:
        dataset = []
        sources_map = {}
        
        # Load all JSONL files from the deployed directory (exclude backup files)
        jsonl_files = [f for f in deployed_dir.glob('*.jsonl') if 'backup' not in f.name.lower()]
        
        if not jsonl_files:
            print(f"Warning: No JSONL files found in {deployed_dir}")
            return False
        
        chunk_index_counter = 0
        for jsonl_file in jsonl_files:
            print(f"Loading {jsonl_file.name}...")
            with open(jsonl_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        try:
                            chunk = json.loads(line.strip())
                            if chunk and 'text' in chunk and 'embedding' in chunk:
                                chunk['_chunk_index'] = chunk_index_counter
                                dataset.append(chunk)
                                chunk_index_counter += 1
                                
                                # Track available sources
                                source_key = f"{chunk.get('source', 'Unknown')}_{chunk.get('author', 'Unknown')}"
                                if source_key not in sources_map:
                                    sources_map[source_key] = {
                                        'id': source_key.lower().replace(' ', '_').replace('.', '').replace('/', '_'),
                                        'name': chunk.get('source', 'Unknown Source'),
                                        'author': chunk.get('author', 'Unknown Author'),
                                        'chunkCount': 0
                                    }
                                sources_map[source_key]['chunkCount'] += 1
                        except json.JSONDecodeError:
                            print(f"Failed to parse line in {jsonl_file.name}")
                            continue
        
        available_sources = list(sources_map.values())
        
        # Extract valid scripture references, named entities, authors, and sources from dataset
        for chunk in dataset:
            if chunk.get('source'):
                valid_sources.add(chunk.get('source'))
            if chunk.get('author'):
                author = chunk.get('author').strip()
                author = re.sub(r'([A-Z])\.\s+([A-Z])\.', r'\1.\2.', author)
                author = ' '.join(author.split())
                valid_authors.add(author)
            
            metadata = chunk.get('metadata', {})
            for ref in metadata.get('scripture_references', []):
                valid_scripture_references.add(ref)
            for ne in metadata.get('named_entities', []):
                valid_named_entities.add(ne)
        
        print(f"✅ Loaded {len(dataset)} chunks from {len(available_sources)} sources")
        print(f"✅ Found {len(valid_scripture_references)} unique scripture references, {len(valid_named_entities)} named entities")
        return True
    except Exception as e:
        print(f"Error loading dataset: {e}")
        return False

def get_embedding(text):
    """Get embedding for a text using OpenAI API"""
    start_time = time.time()
    try:
        response = client.embeddings.create(
            input=text,
            model="text-embedding-3-small"
        )
        elapsed = time.time() - start_time
        print(f"[TIMING] get_embedding: {elapsed:.2f}s")
        return response.data[0].embedding
    except Exception as e:
        print(f"Error getting embedding: {e}")
        elapsed = time.time() - start_time
        print(f"[TIMING] get_embedding (error): {elapsed:.2f}s")
        return None

async def get_embedding_async(text):
    """Async version of get_embedding"""
    start_time = time.time()
    try:
        # OpenAI client doesn't have native async, but we can run in executor
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.embeddings.create(
                input=text,
                model="text-embedding-3-small"
            )
        )
        elapsed = time.time() - start_time
        print(f"[TIMING] get_embedding_async: {elapsed:.2f}s")
        return response.data[0].embedding
    except Exception as e:
        print(f"Error getting embedding (async): {e}")
        elapsed = time.time() - start_time
        print(f"[TIMING] get_embedding_async (error): {elapsed:.2f}s")
        return None

async def analyze_query_async(query):
    """Async version of analyze_query"""
    start_time = time.time()
    try:
        # Build lists for the prompt
        concepts_list = ', '.join(valid_concepts[:100])
        if len(valid_concepts) > 100:
            concepts_list += f" ... and {len(valid_concepts) - 100} more"
        
        discourse_list = ', '.join(valid_discourse_elements)
        
        scripture_list = ', '.join(sorted(list(valid_scripture_references))[:50])
        if len(valid_scripture_references) > 50:
            scripture_list += f" ... and {len(valid_scripture_references) - 50} more"
        
        named_entities_list = ', '.join(sorted(list(valid_named_entities))[:50])
        if len(valid_named_entities) > 50:
            named_entities_list += f" ... and {len(valid_named_entities) - 50} more"
        
        authors_list = ', '.join(sorted(list(valid_authors))[:30])
        if len(valid_authors) > 30:
            authors_list += f" ... and {len(valid_authors) - 30} more"
        
        sources_list = ', '.join(sorted(list(valid_sources))[:20])
        if len(valid_sources) > 20:
            sources_list += f" ... and {len(valid_sources) - 20} more"
        
        # Run API call in executor
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{
                    "role": "system",
                    "content": f"""You are an expert theological research assistant. Analyze queries to determine the best search strategy and filters.

CRITICAL: You MUST ONLY select filters from the provided lists below. Do NOT invent or create new concepts, discourse elements, scripture references, or named entities.

FILTER PRIORITY ORDER:
1. CONCEPTS (highest priority) - Select from the valid concepts list below
2. DISCOURSE ELEMENTS - Select from the valid discourse elements list below (e.g., if user mentions "metaphor", look for "Symbolic/Metaphor")
3. SCRIPTURE REFERENCES - Extract from query if mentioned (book, chapter, verse)
4. NAMED ENTITIES - Select from valid named entities if person/place mentioned
5. SOURCE & AUTHOR - Select from valid sources/authors if specific source/author mentioned

VALID CONCEPTS ({len(valid_concepts)} total):
{concepts_list}

VALID DISCOURSE ELEMENTS ({len(valid_discourse_elements)} total):
{discourse_list}

VALID SCRIPTURE REFERENCES (examples from dataset):
{scripture_list}

VALID NAMED ENTITIES (examples from dataset):
{named_entities_list}

VALID AUTHORS (examples from dataset):
{authors_list}

VALID SOURCES (examples from dataset):
{sources_list}

INSTRUCTIONS:
- For CONCEPTS: Match the query to concepts from the valid list above. Only select concepts that actually appear in the list.
- For DISCOURSE ELEMENTS: If the query mentions things like "metaphor", "claim", "argument", "story", etc., find the matching discourse element from the valid list (e.g., "metaphor" → "Symbolic/Metaphor", "argument" → "Logical/Claim").
- For SCRIPTURE REFERENCES: Extract exact references if mentioned (e.g., "Genesis 1" → "Genesis 1", "John 14:6" → "John 14:6"). Normalize format to match dataset.
- For NAMED ENTITIES: Only include if a specific person/place is mentioned AND it appears in the valid list.
- For SOURCE/AUTHOR: Only include if user specifically asks for content from a particular source or author.

Respond in JSON format:
{{
    "query_type": "doctrinal|exegetical|historical|biographical|comparative|practical|other",
    "suggested_filters": {{
        "concepts": ["concept1", "concept2"],  // MUST be from valid concepts list
        "discourse_elements": ["discourse1", "discourse2"],  // MUST be from valid discourse elements list
        "scripture_references": ["ref1", "ref2"],  // Extract from query if mentioned
        "named_entities": ["entity1"],  // Only if mentioned AND in valid list
        "sources": ["source1"],  // Only if user asks for specific source
        "authors": ["author1"]  // Only if user asks for specific author
    }},
    "search_strategy": "Brief technical explanation of filters selected and why"
}}"""
                }, {
                    "role": "user",
                    "content": f"Analyze this theological query: {query}"
                }],
                temperature=0.2
            )
        )
        
        analysis = json.loads(response.choices[0].message.content)
        elapsed = time.time() - start_time
        print(f"[TIMING] analyze_query_async: {elapsed:.2f}s")
        return analysis
    except Exception as e:
        print(f"Error analyzing query (async): {e}")
        elapsed = time.time() - start_time
        print(f"[TIMING] analyze_query_async (error): {elapsed:.2f}s")
        return {
            "query_type": "general",
            "theological_concepts": [],
            "suggested_filters": {},
            "search_strategy": "Using basic vector similarity search"
        }

def analyze_query(query):
    """Use AI to analyze the theological query and determine search strategy"""
    start_time = time.time()
    try:
        # Build lists for the prompt
        concepts_list = ', '.join(valid_concepts[:100])  # Limit to first 100 to avoid token limits
        if len(valid_concepts) > 100:
            concepts_list += f" ... and {len(valid_concepts) - 100} more"
        
        discourse_list = ', '.join(valid_discourse_elements)
        
        scripture_list = ', '.join(sorted(list(valid_scripture_references))[:50])  # Limit to 50 examples
        if len(valid_scripture_references) > 50:
            scripture_list += f" ... and {len(valid_scripture_references) - 50} more"
        
        named_entities_list = ', '.join(sorted(list(valid_named_entities))[:50])  # Limit to 50 examples
        if len(valid_named_entities) > 50:
            named_entities_list += f" ... and {len(valid_named_entities) - 50} more"
        
        authors_list = ', '.join(sorted(list(valid_authors))[:30])  # Limit to 30 examples
        if len(valid_authors) > 30:
            authors_list += f" ... and {len(valid_authors) - 30} more"
        
        sources_list = ', '.join(sorted(list(valid_sources))[:20])  # Limit to 20 examples
        if len(valid_sources) > 20:
            sources_list += f" ... and {len(valid_sources) - 20} more"
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "system",
                "content": f"""You are an expert theological research assistant. Analyze queries to determine the best search strategy and filters.

CRITICAL: You MUST ONLY select filters from the provided lists below. Do NOT invent or create new concepts, discourse elements, scripture references, or named entities.

FILTER PRIORITY ORDER:
1. CONCEPTS (highest priority) - Select from the valid concepts list below
2. DISCOURSE ELEMENTS - Select from the valid discourse elements list below (e.g., if user mentions "metaphor", look for "Symbolic/Metaphor")
3. SCRIPTURE REFERENCES - Extract from query if mentioned (book, chapter, verse)
4. NAMED ENTITIES - Select from valid named entities if person/place mentioned
5. SOURCE & AUTHOR - Select from valid sources/authors if specific source/author mentioned

VALID CONCEPTS ({len(valid_concepts)} total):
{concepts_list}

VALID DISCOURSE ELEMENTS ({len(valid_discourse_elements)} total):
{discourse_list}

VALID SCRIPTURE REFERENCES (examples from dataset):
{scripture_list}

VALID NAMED ENTITIES (examples from dataset):
{named_entities_list}

VALID AUTHORS (examples from dataset):
{authors_list}

VALID SOURCES (examples from dataset):
{sources_list}

INSTRUCTIONS:
- For CONCEPTS: Match the query to concepts from the valid list above. Only select concepts that actually appear in the list.
- For DISCOURSE ELEMENTS: If the query mentions things like "metaphor", "claim", "argument", "story", etc., find the matching discourse element from the valid list (e.g., "metaphor" → "Symbolic/Metaphor", "argument" → "Logical/Claim").
- For SCRIPTURE REFERENCES: Extract exact references if mentioned (e.g., "Genesis 1" → "Genesis 1", "John 14:6" → "John 14:6"). Normalize format to match dataset.
- For NAMED ENTITIES: Only include if a specific person/place is mentioned AND it appears in the valid list.
- For SOURCE/AUTHOR: Only include if user specifically asks for content from a particular source or author.

Respond in JSON format:
{{
    "query_type": "doctrinal|exegetical|historical|biographical|comparative|practical|other",
    "suggested_filters": {{
        "concepts": ["concept1", "concept2"],  // MUST be from valid concepts list
        "discourse_elements": ["discourse1", "discourse2"],  // MUST be from valid discourse elements list
        "scripture_references": ["ref1", "ref2"],  // Extract from query if mentioned
        "named_entities": ["entity1"],  // Only if mentioned AND in valid list
        "sources": ["source1"],  // Only if user asks for specific source
        "authors": ["author1"]  // Only if user asks for specific author
    }},
    "search_strategy": "Brief technical explanation of filters selected and why"
}}"""
            }, {
                "role": "user",
                "content": f"Analyze this theological query: {query}"
            }],
            temperature=0.2  # Lower temperature for more consistent selection from lists
        )
        
        analysis = json.loads(response.choices[0].message.content)
        elapsed = time.time() - start_time
        print(f"[TIMING] analyze_query: {elapsed:.2f}s")
        return analysis
    except Exception as e:
        print(f"Error analyzing query: {e}")
        elapsed = time.time() - start_time
        print(f"[TIMING] analyze_query (error): {elapsed:.2f}s")
        return {
            "query_type": "general",
            "theological_concepts": [],
            "suggested_filters": {},
            "search_strategy": "Using basic vector similarity search"
        }

def search_with_filters(query, query_embedding, analysis, selected_sources=None):
    """Perform intelligent two-stage search: ChromaDB top 100 → re-rank with metadata → top 15"""
    try:
        if not query_embedding:
            return []
        
        start_time = time.time()
        
        # STAGE 1: ChromaDB vector search - get top 100 by similarity
        if not chroma_collection:
            raise RuntimeError("ChromaDB collection not initialized. Please run migrate_to_chroma.py first.")
        
        stage1_start = time.time()
        
        # Build where clause for source filtering if needed
        where_clause = None
        if selected_sources and len(selected_sources) > 0:
            # ChromaDB where clause: {"source": {"$in": [...]}}
            # Need to map source IDs back to source names
            source_names = []
            for source_info in available_sources:
                if source_info['id'] in selected_sources:
                    source_names.append(source_info['name'])
            if source_names:
                where_clause = {"source": {"$in": source_names}}
        
        # Query ChromaDB for top 100 results
        results = chroma_collection.query(
            query_embeddings=[query_embedding],
            n_results=100,  # Get top 100 for re-ranking
            where=where_clause
        )
        
        stage1_time = time.time() - stage1_start
        print(f"[TIMING] Stage 1 (ChromaDB top 100): {stage1_time:.3f}s")
        
        # Map ChromaDB results back to full chunk objects
        top_100_chunks = []
        if results['ids'] and len(results['ids'][0]) > 0:
            # Create mapping from chunk ID to full chunk data
            chunk_map = {chunk.get('id'): chunk for chunk in dataset}
            
            # Get distances (ChromaDB returns distances, convert to similarities)
            distances = results['distances'][0] if results.get('distances') else []
            
            # Debug: Check for unusual distances and log distribution
            if distances:
                min_dist = min(distances)
                max_dist = max(distances)
                distances_at_1 = sum(1 for d in distances if abs(d - 1.0) < 0.001)
                if max_dist > 1.0:
                    print(f"[WARNING] ChromaDB returned distances > 1.0: max={max_dist:.3f}, min={min_dist:.3f}")
                if distances_at_1 > 0:
                    print(f"[DEBUG] Found {distances_at_1} chunks with distance ~1.0 (similarity ~0.0)")
            
            for idx, chunk_id in enumerate(results['ids'][0]):
                if chunk_id in chunk_map:
                    chunk = chunk_map[chunk_id].copy()
                    # Convert ChromaDB distance to cosine similarity
                    # ChromaDB by default uses L2 (Euclidean) distance, not cosine distance
                    # For normalized embeddings: L2_distance² = 2 * (1 - cosine_similarity)
                    # So: cosine_similarity = 1 - (L2_distance² / 2)
                    distance = distances[idx] if idx < len(distances) else 2.0
                    # Convert L2 distance to cosine similarity
                    similarity = 1.0 - ((distance ** 2) / 2.0)
                    # Clamp to [0, 1] range
                    similarity = max(0.0, min(1.0, similarity))
                    chunk['similarity_score'] = float(similarity)
                    top_100_chunks.append(chunk)
        
        if not top_100_chunks:
            return []
        
        # STAGE 2: Re-rank top 100 with metadata boost
        stage2_start = time.time()
        scored_chunks = []
        
        for chunk in top_100_chunks:
            base_score = chunk.get('similarity_score', 0.0)
            metadata_boost = calculate_metadata_boost(chunk, analysis)
            final_score = base_score + metadata_boost
            
            scored_chunks.append({
                **chunk,
                'similarity_score': float(base_score),
                'metadata_boost': float(metadata_boost),
                'final_score': float(final_score)
            })
        
        # Sort by final score and return top 15
        scored_chunks.sort(key=lambda x: x['final_score'], reverse=True)
        top_15 = scored_chunks[:15]
        
        stage2_time = time.time() - stage2_start
        total_time = time.time() - start_time
        print(f"[TIMING] Stage 2 (Re-rank top 100): {stage2_time:.3f}s")
        print(f"[TIMING] Total search time: {total_time:.3f}s")
        
        return top_15
        
    except Exception as e:
        print(f"Error in search_with_filters: {e}")
        import traceback
        traceback.print_exc()
        return []

def calculate_metadata_boost(chunk, analysis):
    """Calculate metadata-based relevance boost"""
    boost = 0.0
    metadata = chunk.get('metadata', {})
    suggested = analysis.get('suggested_filters', {})
    
    # SCRIPTURE REFERENCE MATCHING - Priority 3
    # Scripture references are precise metadata but lower priority than concepts/discourse
    chunk_scripture = metadata.get('scripture_references', [])
    suggested_scripture = suggested.get('scripture_references', [])
    
    if chunk_scripture and suggested_scripture:
        # Normalize Scripture references for comparison
        def normalize_scripture(ref):
            """Normalize Scripture reference for comparison"""
            if not ref:
                return None
            # Remove extra spaces, convert to lowercase
            normalized = re.sub(r'\s+', ' ', str(ref).strip().lower())
            return normalized
        
        chunk_scripture_normalized = [normalize_scripture(ref) for ref in chunk_scripture]
        suggested_scripture_normalized = [normalize_scripture(ref) for ref in suggested_scripture]
        
        # Check for exact matches first (highest priority)
        exact_matches = set(chunk_scripture_normalized) & set(suggested_scripture_normalized)
        if exact_matches:
            # Exact match gets very high boost (0.5 per match, up to 1.0 total)
            boost += min(len(exact_matches) * 0.5, 1.0)
        else:
            # Check for chapter-level matches (e.g., "Genesis 1" matches "Genesis 1:1-5")
            for suggested_ref in suggested_scripture_normalized:
                if not suggested_ref:
                    continue
                # Extract book and chapter from suggested reference
                # Format: "book chapter" or "book chapter:verse"
                parts = suggested_ref.split(':')
                if len(parts) > 0:
                    book_chapter = parts[0].strip()  # e.g., "genesis 1"
                    # Check if any chunk reference starts with this book/chapter
                    # Important: Use word boundary to avoid "genesis 1" matching "genesis 14"
                    for chunk_ref in chunk_scripture_normalized:
                        if chunk_ref:
                            # Check for exact chapter match: chunk starts with "book chapter:" or equals "book chapter"
                            if chunk_ref == book_chapter or chunk_ref.startswith(book_chapter + ':'):
                                # Chapter-level match gets high boost (0.3 per match, up to 0.6 total)
                                boost += 0.3
                                break
                            # Also check if chunk reference has the same book and chapter (handles variations)
                            # Split chunk_ref to get its book_chapter part
                            chunk_parts = chunk_ref.split(':')
                            chunk_book_chapter = chunk_parts[0].strip() if chunk_parts else chunk_ref
                            if chunk_book_chapter == book_chapter:
                                boost += 0.3
                                break
                    if boost >= 0.6:
                        break
            
            # Check for book-level matches (e.g., "Genesis" matches "Genesis 1", "Genesis 3", etc.)
            if boost < 0.3:  # Only if no chapter match found
                for suggested_ref in suggested_scripture_normalized:
                    if not suggested_ref:
                        continue
                    # Extract book name (first word)
                    book_name = suggested_ref.split()[0] if suggested_ref.split() else None
                    if book_name:
                        for chunk_ref in chunk_scripture_normalized:
                            if chunk_ref and chunk_ref.startswith(book_name):
                                # Book-level match gets moderate boost (0.15 per match, up to 0.3 total)
                                boost += 0.15
                                break
                        if boost >= 0.3:
                            break
    
    # NAMED ENTITY MATCHING - Priority 4
    chunk_entities = metadata.get('named_entities', [])
    suggested_entities = suggested.get('named_entities', [])
    if chunk_entities and suggested_entities:
        entity_overlap = len(set(chunk_entities) & set(suggested_entities))
        boost += entity_overlap * 0.1
    
    # CONCEPT MATCHING - HIGHEST PRIORITY (Priority 1)
    chunk_concepts = metadata.get('concepts', [])
    suggested_concepts = suggested.get('concepts', [])
    if chunk_concepts and suggested_concepts:
        concept_overlap = len(set(chunk_concepts) & set(suggested_concepts))
        boost += concept_overlap * 0.15  # Higher boost for concepts
    
    # DISCOURSE ELEMENT MATCHING - Priority 2
    chunk_discourse_tags = metadata.get('discourse_tags', [])
    # Fallback: extract from discourse_elements for backward compatibility
    if not chunk_discourse_tags:
        chunk_functions = metadata.get('discourse_elements', [])
        if chunk_functions:
            for func in chunk_functions:
                # Extract tag from format "[[Category/Element]] description"
                tag_match = re.search(r'\[\[([^\]]+)\]\]', func)
                if tag_match:
                    chunk_discourse_tags.append(tag_match.group(1))
    
    suggested_discourse = suggested.get('discourse_elements', [])
    if chunk_discourse_tags and suggested_discourse:
        # Match discourse tags (e.g., "Symbolic/Metaphor", "Logical/Claim")
        discourse_overlap = len(set(chunk_discourse_tags) & set(suggested_discourse))
        boost += discourse_overlap * 0.12  # High boost for discourse elements
    
    # Cap boost at 1.5 (increased from 0.3 to allow Scripture reference boosts)
    return min(boost, 1.5)

def generate_research_summary(query, analysis, chunks, existing_reasoning=None):
    """Generate comprehensive research summary with proper citations"""
    try:
        if not chunks:
            return {
                "summary": "No relevant sources found for this query.",
                "sources_used": [],
                "reasoning_transparency": existing_reasoning or analysis.get('search_strategy', 'No search strategy available')
            }
        
        # Prepare context for synthesis
        sources_context = []
        for i, chunk in enumerate(chunks[:10], 1):  # Use top 10 chunks
            source_info = f"[{i}] {chunk.get('source', 'Unknown')}"
            if chunk.get('author'):
                source_info += f" by {chunk['author']}"
            if chunk.get('metadata', {}).get('structure_path'):
                source_info += f" - {chunk['metadata']['structure_path']}"
            
            sources_context.append(f"{source_info}\n{chunk['text']}\n")
        
        context_text = "\n".join(sources_context)
        
        # Generate synthesis
        summary_start = time.time()
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "system",
                "content": """You are an expert theological research assistant. Create a comprehensive research summary that:

1. Synthesizes information from multiple sources
2. Uses numbered citations [1], [2], etc. that correspond to the source numbers provided
3. Maintains theological accuracy and nuance
4. Organizes information logically
5. Highlights key points and different perspectives when present

CRITICAL REQUIREMENTS:
- Use citations frequently to support statements throughout the summary
- ALWAYS end the summary with a "Citations" section that lists ALL cited sources
- The Citations section MUST be formatted as a numbered list (e.g., "[1] Source Name by Author - Location")
- Include every source that was cited with [1], [2], etc. in the summary text
- The Citations list should appear at the very end, after all summary content

Guidelines:
- Maintain respectful tone for all theological traditions
- Be comprehensive but concise
- Include multiple perspectives when sources differ
- Make clear distinctions between biblical text, historical positions, and theological interpretations"""
            }, {
                "role": "user",
                "content": f"""Research question: {query}

Available sources:
{context_text}

Create a comprehensive research summary with proper numbered citations. IMPORTANT: You MUST end the summary with a "Citations" section listing all cited sources as a numbered list."""
            }],
            temperature=0.5,
            max_tokens=1500
        )
        summary_time = time.time() - summary_start
        print(f"[TIMING] Summary generation: {summary_time:.2f}s")
        
        summary = response.choices[0].message.content
        
        # Extract citations and create source list
        # Look for both square brackets [1] and parentheses (1)
        citation_pattern = re.compile(r'[\[\(](\d+)[\]\)]')
        cited_numbers = set()
        for match in citation_pattern.finditer(summary):
            try:
                cited_numbers.add(int(match.group(1)))
            except ValueError:
                continue
        
        # Renumber citations to be sequential
        old_to_new_mapping = {}
        for new_num, old_num in enumerate(sorted(cited_numbers), 1):
            old_to_new_mapping[old_num] = new_num
        
        # Build sources list with explanations (only for cited chunks)
        # Batch generate relevance explanations for cited chunks
        cited_chunks = []
        cited_indices = []
        for old_num in sorted(cited_numbers):
            chunk_index = old_num - 1
            if chunk_index < len(chunks):
                cited_chunks.append(chunks[chunk_index])
                cited_indices.append(chunk_index)
        
        # Generate simple relevance explanations (no API call for speed)
        summary_explanation_start = time.time()
        cited_explanations = []
        for chunk in cited_chunks:
            similarity_score = chunk.get('similarity_score', 0)
            metadata = chunk.get('metadata', {})
            
            # Build simple explanation from metadata
            explanation_parts = []
            if metadata.get('scripture_references'):
                refs = metadata['scripture_references'][:1]
                explanation_parts.append(f"Scripture: {', '.join(refs)}")
            if metadata.get('concepts'):
                concepts = metadata['concepts'][:1]
                explanation_parts.append(f"Concept: {', '.join(concepts)}")
            if metadata.get('topics'):
                topics = metadata['topics'][:1]
                explanation_parts.append(f"Topic: {', '.join(topics)}")
            
            if explanation_parts:
                explanation = f"{' | '.join(explanation_parts)}. (similarity: {similarity_score:.3f})"
            else:
                explanation = f"Relevant content matching query. (similarity: {similarity_score:.3f})"
            
            cited_explanations.append(explanation)
        
        summary_explanation_time = time.time() - summary_explanation_start
        print(f"[TIMING] Simple summary explanations ({len(cited_chunks)} chunks): {summary_explanation_time:.3f}s")
        
        # Build sources list
        renumbered_sources = []
        for new_num, old_num in enumerate(sorted(cited_numbers), 1):
            chunk_index = old_num - 1
            if chunk_index < len(chunks):
                chunk = chunks[chunk_index]
                # Get explanation from batch results
                # Find the position of this chunk_index in cited_indices
                try:
                    explanation_idx = cited_indices.index(chunk_index)
                    explanation = cited_explanations[explanation_idx] if explanation_idx < len(cited_explanations) else f"Relevant content. (similarity: {chunk.get('similarity_score', 0):.3f})"
                except ValueError:
                    # Chunk not in cited_indices (shouldn't happen, but handle gracefully)
                    explanation = f"Relevant content. (similarity: {chunk.get('similarity_score', 0):.3f})"
                
                source_entry = {
                    'number': new_num,  # Add number field for frontend
                    'source': chunk.get('source', 'Unknown Source'),
                    'author': chunk.get('author', 'Unknown Author'),
                    'location': chunk.get('metadata', {}).get('structure_path', 'Unknown'),
                    'relevance_explanation': explanation,
                    'chunk_id': chunk.get('id', ''),
                    '_chunk_index': chunk.get('_chunk_index', chunk_index),
                    'metadata': chunk.get('metadata', {}),
                    'text': chunk.get('text', '')  # Include text for display
                }
                renumbered_sources.append(source_entry)
        
        # Fix citations in summary - preserve original format (brackets or parentheses)
        # Extract all citations with their positions and formats
        citation_matches = []
        for match in citation_pattern.finditer(summary):
            old_citation_num = int(match.group(1))
            # Determine if it's brackets or parentheses
            start_char = summary[match.start()]
            end_char = summary[match.end() - 1]
            citation_format = (start_char, end_char)  # e.g., ('[', ']') or ('(', ')')
            citation_matches.append((match.start(), match.end(), old_citation_num, citation_format))
        
        # Sort by position in reverse to replace from end to start
        citation_matches.sort(key=lambda x: x[0], reverse=True)
        fixed_summary = summary
        
        for start_pos, end_pos, old_citation_num, citation_format in citation_matches:
            if old_citation_num in old_to_new_mapping:
                new_citation_num = old_to_new_mapping[old_citation_num]
                # Preserve original format (brackets or parentheses)
                if citation_format == ('(', ')'):
                    new_citation = f'({new_citation_num})'
                else:
                    new_citation = f'[{new_citation_num}]'
                fixed_summary = fixed_summary[:start_pos] + new_citation + fixed_summary[end_pos:]
        
        return {
            "summary": fixed_summary,
            "sources_used": renumbered_sources,
            "reasoning_transparency": existing_reasoning or analysis.get('search_strategy', 'No search strategy available')
        }
    except Exception as e:
        print(f"Error generating summary: {e}")
        return {
            "summary": "Error generating research summary.",
            "sources_used": [],
            "reasoning_transparency": "Error in synthesis process"
        }

@app.route('/')
def index():
    # Read the enhanced HTML file (relative to script location)
    script_dir = Path(__file__).parent
    html_path = script_dir / 'enhanced_index.html'
    
    try:
        with open(html_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        return html_content
    except FileNotFoundError:
        return f"Enhanced UI file not found at {html_path}. Please ensure enhanced_index.html exists in the same directory as enhanced_app.py.", 404

@app.route('/api/sources')
def get_sources():
    """Get available sources for selection"""
    return jsonify(available_sources)

@app.route('/api/filter-options')
def get_filter_options():
    """Get all available filter options from the dataset"""
    try:
        sources = set()
        authors = set()
        concepts = set()
        topics = set()
        terms = set()
        discourse_elements = set()
        discourse_namespaces = set()
        scripture_references = set()
        named_entities = set()
        
        for chunk in dataset:
            # Sources and authors
            if chunk.get('source'):
                sources.add(chunk.get('source'))
            if chunk.get('author'):
                # Normalize author name: strip whitespace and normalize spaces between initials only
                author = chunk.get('author').strip()
                # Normalize "G. K. Chesterton" to "G.K. Chesterton" (remove spaces between initials)
                # Pattern: capital letter, period, space, capital letter, period -> remove space
                # This handles "G. K." -> "G.K." but preserves "St. Augustine" and "C. S. Lewis" -> "C.S. Lewis"
                author = re.sub(r'([A-Z])\.\s+([A-Z])\.', r'\1.\2.', author)
                # Normalize any remaining double spaces
                author = ' '.join(author.split())
                authors.add(author)
            
            metadata = chunk.get('metadata', {})
            
            # Concepts, topics, terms
            for concept in metadata.get('concepts', []):
                concepts.add(concept)
            
            for topic in metadata.get('topics', []):
                topics.add(topic)
                # Extract concept namespace - strip brackets first
                topic_clean = topic.replace('[[', '').replace(']]', '')
                if '/' in topic_clean:
                    concept_ns = topic_clean.split('/', 1)[0]
                    concepts.add(concept_ns)
            
            for term in metadata.get('terms', []):
                terms.add(term)
                # Extract concept namespace - strip brackets first
                term_clean = term.replace('[[', '').replace(']]', '')
                if '/' in term_clean:
                    concept_ns = term_clean.split('/', 1)[0]
                    concepts.add(concept_ns)
            
            # Discourse tags (extracted tags) - prefer this field if available
            discourse_tags = metadata.get('discourse_tags', [])
            if not discourse_tags:
                # Fallback: extract tags from discourse_elements
                for de in metadata.get('discourse_elements', []):
                    tag_match = re.search(r'\[\[([^\]]+)\]\]', de)
                    if tag_match:
                        discourse_tags.append(tag_match.group(1))
            
            # Add all discourse tags and extract namespaces
            for tag in discourse_tags:
                discourse_elements.add(tag)  # Store tags (not full strings) for filtering
                # Extract namespace (e.g., "Logical" from "Logical/Claim")
                if '/' in tag:
                    namespace = tag.split('/', 1)[0]
                    discourse_namespaces.add(namespace)
                else:
                    # Standalone namespace
                    discourse_namespaces.add(tag)
            
            # Scripture references
            for ref in metadata.get('scripture_references', []):
                scripture_references.add(ref)
            
            # Named entities
            for ne in metadata.get('named_entities', []):
                named_entities.add(ne)
        
        # Build concept/topic/term suggestions (namespaced)
        concept_suggestions = {}
        for topic in topics:
            # Strip brackets before extracting concept namespace
            topic_clean = topic.replace('[[', '').replace(']]', '')
            if '/' in topic_clean:
                concept = topic_clean.split('/', 1)[0]
                # Normalize concept key (strip brackets) to avoid duplicates
                concept_key = concept.replace('[[', '').replace(']]', '')
                if concept_key not in concept_suggestions:
                    concept_suggestions[concept_key] = {'topics': [], 'terms': []}
                concept_suggestions[concept_key]['topics'].append(topic)
        for term in terms:
            # Strip brackets before extracting concept namespace
            term_clean = term.replace('[[', '').replace(']]', '')
            if '/' in term_clean:
                concept = term_clean.split('/', 1)[0]
                # Normalize concept key (strip brackets) to avoid duplicates
                concept_key = concept.replace('[[', '').replace(']]', '')
                if concept_key not in concept_suggestions:
                    concept_suggestions[concept_key] = {'topics': [], 'terms': []}
                concept_suggestions[concept_key]['terms'].append(term)
        
        # Add standalone concepts (without topics/terms)
        # Normalize concept keys to avoid duplicates with brackets
        for concept in concepts:
            concept_key = concept.replace('[[', '').replace(']]', '')
            if concept_key not in concept_suggestions:
                concept_suggestions[concept_key] = {'topics': [], 'terms': []}
        
        # Build discourse element suggestions (namespaced)
        # discourse_elements now contains tags (not full strings)
        discourse_suggestions = {}
        for namespace in discourse_namespaces:
            # Find all discourse tags that have this namespace
            matching_tags = []
            for tag in discourse_elements:
                # Check if tag is exactly the namespace or starts with namespace/
                if tag == namespace or tag.startswith(namespace + '/'):
                    matching_tags.append(tag)
            discourse_suggestions[namespace] = sorted(matching_tags)
        
        # Add standalone discourse tags (without namespace)
        for tag in discourse_elements:
            if '/' not in tag:
                # This is a standalone namespace-only tag
                if tag not in discourse_suggestions:
                    discourse_suggestions[tag] = []
        
        return jsonify({
            'sources': sorted(list(sources)),
            'authors': sorted(list(authors)),
            'concept_suggestions': {k: v for k, v in sorted(concept_suggestions.items())},
            'discourse_suggestions': {k: sorted(v) for k, v in sorted(discourse_suggestions.items())},
            'scripture_references': sorted(list(scripture_references)),
            'named_entities': sorted(list(named_entities))
        })
    except Exception as e:
        print(f"Error getting filter options: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/filter-chunks', methods=['POST'])
def filter_chunks():
    """Filter chunks based on selected filter criteria"""
    try:
        data = request.get_json()
        filters = data.get('filters', {})
        
        selected_sources = set(filters.get('sources', []))
        selected_authors = set(filters.get('authors', []))
        selected_concepts = set(filters.get('concepts', []))
        selected_topics = set(filters.get('topics', []))
        selected_terms = set(filters.get('terms', []))
        selected_discourse = set(filters.get('discourse_elements', []))
        selected_scripture = set(filters.get('scripture_references', []))
        selected_entities = set(filters.get('named_entities', []))
        
        filtered_chunks = []
        
        for chunk in dataset:
            # Source filter
            if selected_sources and chunk.get('source') not in selected_sources:
                continue
            
            # Author filter (with normalization)
            if selected_authors:
                chunk_author = chunk.get('author', '').strip()
                # Normalize author name same way as in filter-options
                chunk_author = re.sub(r'([A-Z])\.\s+([A-Z])\.', r'\1.\2.', chunk_author)
                chunk_author = ' '.join(chunk_author.split())
                # Normalize selected authors too
                normalized_selected = set()
                for auth in selected_authors:
                    norm_auth = auth.strip()
                    norm_auth = re.sub(r'([A-Z])\.\s+([A-Z])\.', r'\1.\2.', norm_auth)
                    norm_auth = ' '.join(norm_auth.split())
                    normalized_selected.add(norm_auth)
                if chunk_author not in normalized_selected:
                    continue
            
            metadata = chunk.get('metadata', {})
            
            # Concept/Topic/Term filters (namespaced)
            chunk_concepts = set(metadata.get('concepts', []))
            chunk_topics = set(metadata.get('topics', []))
            chunk_terms = set(metadata.get('terms', []))
            
            # Extract concept namespaces from topics and terms (strip brackets first)
            for topic in chunk_topics:
                topic_clean = topic.replace('[[', '').replace(']]', '')
                if '/' in topic_clean:
                    chunk_concepts.add(topic_clean.split('/', 1)[0])
            for term in chunk_terms:
                term_clean = term.replace('[[', '').replace(']]', '')
                if '/' in term_clean:
                    chunk_concepts.add(term_clean.split('/', 1)[0])
            
            # Normalize selected concepts (strip brackets) for matching
            selected_concepts_normalized = {c.replace('[[', '').replace(']]', '') for c in selected_concepts}
            chunk_concepts_normalized = {c.replace('[[', '').replace(']]', '') for c in chunk_concepts}
            
            # Check concept match (exact match or namespace match)
            concept_match = False
            if selected_concepts:
                # Direct concept match (using normalized versions)
                if chunk_concepts_normalized & selected_concepts_normalized:
                    concept_match = True
                # Namespace match (e.g., if filter is "Faith", match "Faith/Topic" or "[[Faith/Topic]]")
                for selected_concept in selected_concepts_normalized:
                    if any(topic.replace('[[', '').replace(']]', '').startswith(selected_concept + '/') for topic in chunk_topics):
                        concept_match = True
                    if any(term.replace('[[', '').replace(']]', '').startswith(selected_concept + '/') for term in chunk_terms):
                        concept_match = True
            else:
                concept_match = True  # No concept filter = match all
            
            # Normalize topics (strip brackets) for matching
            chunk_topics_normalized = {t.replace('[[', '').replace(']]', '') for t in chunk_topics}
            selected_topics_normalized = {t.replace('[[', '').replace(']]', '') for t in selected_topics}
            topic_match = not selected_topics or bool(chunk_topics_normalized & selected_topics_normalized)
            
            # Normalize terms (strip brackets) for matching
            chunk_terms_normalized = {t.replace('[[', '').replace(']]', '') for t in chunk_terms}
            selected_terms_normalized = {t.replace('[[', '').replace(']]', '') for t in selected_terms}
            term_match = not selected_terms or bool(chunk_terms_normalized & selected_terms_normalized)
            
            if not (concept_match and topic_match and term_match):
                continue
            
            # Discourse element filter (with namespace support)
            # Use discourse_tags if available, otherwise extract from discourse_elements
            chunk_discourse_tags = set(metadata.get('discourse_tags', []))
            
            # Fallback: extract tags from discourse_elements if discourse_tags not available
            if not chunk_discourse_tags:
                discourse_elements = metadata.get('discourse_elements', [])
                for de in discourse_elements:
                    tag_match = re.search(r'\[\[([^\]]+)\]\]', de)
                    if tag_match:
                        chunk_discourse_tags.add(tag_match.group(1))
            
            discourse_match = False
            if selected_discourse:
                # selected_discourse contains tags (not full strings)
                selected_tags = set(selected_discourse)
                
                # Direct tag match
                if chunk_discourse_tags & selected_tags:
                    discourse_match = True
                
                # Namespace match (e.g., if filter is "Semantic", match "Semantic/Concept")
                if not discourse_match:
                    for selected_tag in selected_tags:
                        if '/' not in selected_tag:
                            # If filter is namespace only, match any element with that namespace
                            if any(tag == selected_tag or tag.startswith(selected_tag + '/') for tag in chunk_discourse_tags):
                                discourse_match = True
                        else:
                            # Exact match for namespaced filters
                            if selected_tag in chunk_discourse_tags:
                                discourse_match = True
            else:
                discourse_match = True  # No discourse filter = match all
            
            if not discourse_match:
                continue
            
            # Scripture reference filter
            chunk_scripture = set(metadata.get('scripture_references', []))
            if selected_scripture and not (chunk_scripture & selected_scripture):
                continue
            
            # Named entity filter
            chunk_entities = set(metadata.get('named_entities', []))
            if selected_entities and not (chunk_entities & selected_entities):
                continue
            
            # All filters passed, include this chunk
            filtered_chunks.append(chunk)
        
        # Format response similar to search results
        sources_used = []
        for i, chunk in enumerate(filtered_chunks[:50], 1):  # Limit to 50 for display
            source_info = {
                "number": i,
                "source": chunk.get('source', 'Unknown'),
                "author": chunk.get('author', 'Unknown'),
                "location": chunk.get('metadata', {}).get('structure_path', 'Unknown'),
                "chunk_id": chunk.get('id', ''),
                "_chunk_index": chunk.get('_chunk_index', i-1),
                "metadata": chunk.get('metadata', {}),
                "text": chunk.get('text', '')
            }
            sources_used.append(source_info)
        
        return jsonify({
            "sources_used": sources_used,
            "total_count": len(filtered_chunks),
            "displayed_count": len(sources_used)
        })
        
    except Exception as e:
        print(f"Error filtering chunks: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/search-only', methods=['POST'])
def search_only():
    """Search without generating summary - returns chunks and analysis immediately"""
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        selected_sources = data.get('sources', [])
        
        if not query:
            return jsonify({"error": "Query is required"}), 400
        
        if not dataset:
            return jsonify({"error": "Dataset not loaded"}), 500
        
        # Step 1: Parallel async processing - query analysis + embedding generation
        parallel_start = time.time()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            analysis, query_embedding = loop.run_until_complete(
                asyncio.gather(
                    analyze_query_async(query),
                    get_embedding_async(query)
                )
            )
        finally:
            loop.close()
        parallel_time = time.time() - parallel_start
        print(f"[TIMING] Parallel (analysis + embedding): {parallel_time:.2f}s")
        
        if not query_embedding:
            return jsonify({"error": "Failed to generate query embedding"}), 500
        
        # Step 2: Search with filters and source selection (two-stage retrieval)
        start_time = time.time()
        chunks = search_with_filters(query, query_embedding, analysis, selected_sources)
        search_time = time.time() - start_time
        print(f"[TIMING] Two-stage search: {search_time:.2f}s")
        
        # Step 3: Generate relevance explanations - SKIPPED for faster response
        # Using simple similarity-based explanations instead of AI-generated ones
        # This reduces response time from ~18s to ~3-4s
        top_chunks = chunks[:15]  # Use top 15 chunks
        relevance_explanations = []
        for chunk in top_chunks:
            similarity_score = chunk.get('similarity_score', 0)
            metadata = chunk.get('metadata', {})
            
            # Build simple explanation from metadata (no API call)
            explanation_parts = []
            if metadata.get('scripture_references'):
                refs = metadata['scripture_references'][:1]
                explanation_parts.append(f"Scripture: {', '.join(refs)}")
            if metadata.get('concepts'):
                concepts = metadata['concepts'][:1]
                explanation_parts.append(f"Concept: {', '.join(concepts)}")
            if metadata.get('topics'):
                topics = metadata['topics'][:1]
                explanation_parts.append(f"Topic: {', '.join(topics)}")
            
            if explanation_parts:
                explanation = f"{' | '.join(explanation_parts)}. (similarity: {similarity_score:.3f})"
            else:
                explanation = f"Relevant content matching query. (similarity: {similarity_score:.3f})"
            
            relevance_explanations.append(explanation)
        
        print(f"[TIMING] Simple relevance explanations (no API): <0.01s")
        
        # Format sources for display (without summary)
        sources_used = []
        for i, chunk in enumerate(top_chunks, 1):
            source_entry = {
                'number': i,
                'source': chunk.get('source', 'Unknown Source'),
                'author': chunk.get('author', 'Unknown Author'),
                'location': chunk.get('metadata', {}).get('structure_path', 'Unknown'),
                'relevance_explanation': relevance_explanations[i-1] if i-1 < len(relevance_explanations) else f"Relevant content. (similarity: {chunk.get('similarity_score', 0):.3f})",
                'chunk_id': chunk.get('id', ''),
                '_chunk_index': chunk.get('_chunk_index', i-1),
                'metadata': chunk.get('metadata', {}),
                'text': chunk.get('text', ''),
                'similarity_score': chunk.get('similarity_score', 0),
                'final_score': chunk.get('final_score', 0)
            }
            sources_used.append(source_entry)
        
        # Build technical search strategy description
        strategy_parts = []
        
        # Query processing
        strategy_parts.append(f"QUERY: \"{query}\"")
        strategy_parts.append("QUERY EXPANSION: None - used as-is for embedding")
        
        # Metadata filters identified (in priority order)
        suggested_filters = analysis.get('suggested_filters', {})
        filter_sections = []
        
        # Priority 1: Concepts
        if suggested_filters.get('concepts'):
            concepts = suggested_filters['concepts']
            filter_sections.append(f"CONCEPTS (Priority 1): {concepts}")
        
        # Priority 2: Discourse Elements
        if suggested_filters.get('discourse_elements'):
            discourse = suggested_filters['discourse_elements']
            filter_sections.append(f"DISCOURSE_ELEMENTS (Priority 2): {discourse}")
        
        # Priority 3: Scripture References
        if suggested_filters.get('scripture_references'):
            refs = suggested_filters['scripture_references']
            filter_sections.append(f"SCRIPTURE_REFERENCES (Priority 3): {refs}")
        
        # Priority 4: Named Entities
        if suggested_filters.get('named_entities'):
            entities = suggested_filters['named_entities']
            filter_sections.append(f"NAMED_ENTITIES (Priority 4): {entities}")
        
        # Priority 5: Sources & Authors
        if suggested_filters.get('sources'):
            sources = suggested_filters['sources']
            filter_sections.append(f"SOURCES (Priority 5): {sources}")
        if suggested_filters.get('authors'):
            authors = suggested_filters['authors']
            filter_sections.append(f"AUTHORS (Priority 5): {authors}")
        
        if filter_sections:
            strategy_parts.append("METADATA_FILTERS_IDENTIFIED:")
            for section in filter_sections:
                strategy_parts.append(f"  - {section}")
        else:
            strategy_parts.append("METADATA_FILTERS_IDENTIFIED: None")
        
        # Scoring method
        strategy_parts.append("SCORING_METHOD: cosine_similarity(vector_embedding) + metadata_boost")
        strategy_parts.append("METADATA_BOOST_PRIORITY: Concepts (0.15) > Discourse Elements (0.12) > Scripture References (0.15-1.0) > Named Entities (0.1)")
        
        search_strategy_text = "\n".join(strategy_parts)
        
        result = {
            "sources_used": sources_used,
            "chunks": chunks,
            "query_analysis": analysis,
            "reasoning_transparency": search_strategy_text,
            "query": query
        }
        
        return jsonify(result)
        
    except Exception as e:
        print(f"Error in search-only: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/generate-summary', methods=['POST'])
def generate_summary():
    """Generate research summary from existing chunks with streaming"""
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        chunks = data.get('chunks', [])
        analysis = data.get('query_analysis', {})
        existing_reasoning = data.get('reasoning_transparency', None)  # Preserve original search strategy
        
        if not query:
            return jsonify({"error": "Query is required"}), 400
        
        if not chunks:
            return jsonify({"error": "Chunks are required"}), 400
        
        # Check if client wants streaming (default to True)
        stream = data.get('stream', True)
        
        if stream:
            return Response(
                stream_with_context(generate_research_summary_stream(query, analysis, chunks, existing_reasoning)),
                mimetype='text/event-stream',
                headers={
                    'Cache-Control': 'no-cache',
                    'X-Accel-Buffering': 'no'
                }
            )
        else:
            # Non-streaming fallback
            result = generate_research_summary(query, analysis, chunks, existing_reasoning)
            result["query_analysis"] = analysis
            result["chunks"] = chunks
            result["query"] = query
            return jsonify(result)
        
    except Exception as e:
        print(f"Error generating summary: {e}")
        return jsonify({"error": str(e)}), 500

def generate_research_summary_stream(query, analysis, chunks, existing_reasoning=None):
    """Generate research summary with streaming response"""
    try:
        if not chunks:
            yield f"data: {json.dumps({'type': 'error', 'message': 'No relevant sources found for this query.'})}\n\n"
            return
        
        # Prepare context for synthesis
        sources_context = []
        for i, chunk in enumerate(chunks[:10], 1):  # Use top 10 chunks
            source_info = f"[{i}] {chunk.get('source', 'Unknown')}"
            if chunk.get('author'):
                source_info += f" by {chunk['author']}"
            if chunk.get('metadata', {}).get('structure_path'):
                source_info += f" - {chunk['metadata']['structure_path']}"
            
            sources_context.append(f"{source_info}\n{chunk['text']}\n")
        
        context_text = "\n".join(sources_context)
        
        # Send initial message
        yield f"data: {json.dumps({'type': 'start'})}\n\n"
        
        # Generate synthesis with streaming
        summary_start = time.time()
        full_summary = ""
        
        stream = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "system",
                "content": """You are an expert theological research assistant. Create a comprehensive research summary that:

1. Synthesizes information from multiple sources
2. Uses numbered citations [1], [2], etc. that correspond to the source numbers provided
3. Maintains theological accuracy and nuance
4. Organizes information logically
5. Highlights key points and different perspectives when present

CRITICAL REQUIREMENTS:
- Use citations frequently to support statements throughout the summary
- ALWAYS end the summary with a "Citations" section that lists ALL cited sources
- The Citations section MUST be formatted as a numbered list (e.g., "[1] Source Name by Author - Location")
- Include every source that was cited with [1], [2], etc. in the summary text
- The Citations list should appear at the very end, after all summary content

Guidelines:
- Maintain respectful tone for all theological traditions
- Be comprehensive but concise
- Include multiple perspectives when sources differ
- Make clear distinctions between biblical text, historical positions, and theological interpretations"""
            }, {
                "role": "user",
                "content": f"""Research question: {query}

Available sources:
{context_text}

Create a comprehensive research summary with proper numbered citations. IMPORTANT: You MUST end the summary with a "Citations" section listing all cited sources as a numbered list."""
            }],
            temperature=0.5,
            max_tokens=1500,
            stream=True
        )
        
        # Stream chunks as they arrive
        for chunk in stream:
            if chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                full_summary += content
                # Send each chunk to client
                yield f"data: {json.dumps({'type': 'chunk', 'content': content})}\n\n"
        
        summary_time = time.time() - summary_start
        print(f"[TIMING] Summary generation (streaming): {summary_time:.2f}s")
        
        # Extract citations and create source list
        citation_pattern = re.compile(r'[\[\(](\d+)[\]\)]')
        cited_numbers = set()
        for match in citation_pattern.finditer(full_summary):
            try:
                cited_numbers.add(int(match.group(1)))
            except ValueError:
                continue
        
        # Renumber citations to be sequential
        old_to_new_mapping = {}
        for new_num, old_num in enumerate(sorted(cited_numbers), 1):
            old_to_new_mapping[old_num] = new_num
        
        # Build sources list with explanations (only for cited chunks)
        cited_chunks = []
        cited_indices = []
        for old_num in sorted(cited_numbers):
            chunk_index = old_num - 1
            if chunk_index < len(chunks):
                cited_chunks.append(chunks[chunk_index])
                cited_indices.append(chunk_index)
        
        # Generate simple relevance explanations (no API call for speed)
        cited_explanations = []
        for chunk in cited_chunks:
            similarity_score = chunk.get('similarity_score', 0)
            metadata = chunk.get('metadata', {})
            
            explanation_parts = []
            if metadata.get('scripture_references'):
                refs = metadata['scripture_references'][:1]
                explanation_parts.append(f"Scripture: {', '.join(refs)}")
            if metadata.get('concepts'):
                concepts = metadata['concepts'][:1]
                explanation_parts.append(f"Concept: {', '.join(concepts)}")
            if metadata.get('topics'):
                topics = metadata['topics'][:1]
                explanation_parts.append(f"Topic: {', '.join(topics)}")
            
            if explanation_parts:
                explanation = f"{' | '.join(explanation_parts)}. (similarity: {similarity_score:.3f})"
            else:
                explanation = f"Relevant content matching query. (similarity: {similarity_score:.3f})"
            
            cited_explanations.append(explanation)
        
        # Build sources list
        renumbered_sources = []
        for new_num, old_num in enumerate(sorted(cited_numbers), 1):
            chunk_index = old_num - 1
            if chunk_index < len(chunks):
                chunk = chunks[chunk_index]
                explanation_idx = cited_indices.index(chunk_index) if chunk_index in cited_indices else -1
                explanation = cited_explanations[explanation_idx] if explanation_idx >= 0 and explanation_idx < len(cited_explanations) else f"Relevant content. (similarity: {chunk.get('similarity_score', 0):.3f})"
                
                source_entry = {
                    'number': new_num,
                    'source': chunk.get('source', 'Unknown Source'),
                    'author': chunk.get('author', 'Unknown Author'),
                    'location': chunk.get('metadata', {}).get('structure_path', 'Unknown'),
                    'relevance_explanation': explanation,
                    'chunk_id': chunk.get('id', ''),
                    '_chunk_index': chunk.get('_chunk_index', chunk_index),
                    'metadata': chunk.get('metadata', {}),
                    'text': chunk.get('text', '')
                }
                renumbered_sources.append(source_entry)
        
        # Fix citations in summary - preserve original format
        citation_matches = []
        for match in citation_pattern.finditer(full_summary):
            old_citation_num = int(match.group(1))
            start_char = full_summary[match.start()]
            end_char = full_summary[match.end() - 1]
            citation_format = (start_char, end_char)
            citation_matches.append((match.start(), match.end(), old_citation_num, citation_format))
        
        citation_matches.sort(key=lambda x: x[0], reverse=True)
        fixed_summary = full_summary
        
        for start_pos, end_pos, old_citation_num, citation_format in citation_matches:
            if old_citation_num in old_to_new_mapping:
                new_citation_num = old_to_new_mapping[old_citation_num]
                if citation_format == ('(', ')'):
                    new_citation = f'({new_citation_num})'
                else:
                    new_citation = f'[{new_citation_num}]'
                fixed_summary = fixed_summary[:start_pos] + new_citation + fixed_summary[end_pos:]
        
        # Send final data
        yield f"data: {json.dumps({
            'type': 'complete',
            'summary': fixed_summary,
            'sources_used': renumbered_sources,
            'reasoning_transparency': existing_reasoning or analysis.get('search_strategy', 'No search strategy available'),
            'query_analysis': analysis,
            'chunks': chunks,
            'query': query
        })}\n\n"
        
    except Exception as e:
        print(f"Error generating streaming summary: {e}")
        yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

@app.route('/search', methods=['POST'])
def search():
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        selected_sources = data.get('sources', [])
        
        if not query:
            return jsonify({"error": "Query is required"}), 400
        
        if not dataset:
            return jsonify({"error": "Dataset not loaded"}), 500
        
        # Step 1: Parallel async processing - query analysis + embedding generation
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            analysis, query_embedding = loop.run_until_complete(
                asyncio.gather(
                    analyze_query_async(query),
                    get_embedding_async(query)
                )
            )
        finally:
            loop.close()
        
        if not query_embedding:
            return jsonify({"error": "Failed to generate query embedding"}), 500
        
        # Step 2: Search with filters and source selection (two-stage retrieval)
        chunks = search_with_filters(query, query_embedding, analysis, selected_sources)
        
        # Step 3: Generate research summary
        result = generate_research_summary(query, analysis, chunks)
        
        # Add the analysis and chunks to the result
        result["query_analysis"] = analysis
        result["chunks"] = chunks
        
        return jsonify(result)
        
    except Exception as e:
        print(f"Error in search: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/search-context', methods=['POST'])
def search_context():
    """Search for relevant chunks based on draft context around cursor"""
    try:
        data = request.get_json()
        context_text = data.get('context_text', '').strip()
        selected_sources = data.get('selected_sources', [])
        
        if not context_text:
            return jsonify({"error": "Context text is required"}), 400
        
        # Parallel async processing - query analysis + embedding generation
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            analysis, query_embedding = loop.run_until_complete(
                asyncio.gather(
                    analyze_query_async(context_text),
                    get_embedding_async(context_text)
                )
            )
        finally:
            loop.close()
        
        if not query_embedding:
            return jsonify({"error": "Failed to generate query embedding"}), 500
        
        # Search with filters and source selection (two-stage retrieval)
        chunks = search_with_filters(context_text, query_embedding, analysis, selected_sources)
        
        # For draft mode, we don't need a research summary, just return the chunks
        # Format the response similar to research mode but without synthesis
        sources_used = []
        for i, chunk in enumerate(chunks[:10], 1):  # Use top 10 chunks
            # Generate a relevance explanation using AI
            relevance_explanation = generate_relevance_explanation(context_text, chunk)
            
            source_info = {
                "number": i,
                "source": chunk.get('source', 'Unknown'),
                "author": chunk.get('author', 'Unknown'),
                "location": chunk.get('metadata', {}).get('structure_path', 'Unknown'),
                "relevance": relevance_explanation
            }
            sources_used.append(source_info)
        
        result = {
            "sources_used": sources_used,
            "chunks": chunks,
            "reasoning_transparency": analysis.get('search_strategy', 'Context-based search'),
            "query_analysis": analysis
        }
        
        return jsonify(result)
        
    except Exception as e:
        print(f"Error in context search: {e}")
        return jsonify({"error": str(e)}), 500

def generate_relevance_explanation(context_text, chunk):
    """Generate a single-sentence explanation of why this chunk is relevant to the query"""
    try:
        chunk_text = chunk.get('text', '')[:400]  # Limit chunk text for API efficiency
        similarity_score = chunk.get('similarity_score', 0)
        metadata = chunk.get('metadata', {})
        
        # Build metadata context for the AI - prioritize most relevant metadata
        metadata_highlights = []
        # Scripture references are highest priority
        if metadata.get('scripture_references'):
            refs = metadata['scripture_references'][:3]  # Limit to first 3
            metadata_highlights.append(f"Scripture: {', '.join(refs)}")
        # Then concepts/topics
        if metadata.get('concepts'):
            concepts = metadata['concepts'][:2]  # Limit to first 2
            metadata_highlights.append(f"Concepts: {', '.join(concepts)}")
        if metadata.get('topics'):
            topics = metadata['topics'][:2]  # Limit to first 2
            metadata_highlights.append(f"Topics: {', '.join(topics)}")
        
        metadata_str = " | ".join(metadata_highlights) if metadata_highlights else "General relevance"
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "system",
                "content": """You are a theological research assistant. Generate EXACTLY ONE sentence (no more) that identifies the key connection between a query and a source chunk. The sentence must be concise (under 20 words), direct, and scannable. Prioritize Scripture references, then theological concepts, then topics. Do NOT write multiple sentences - only ONE sentence ending with a period."""
            }, {
                "role": "user",
                "content": f"""Query: {context_text}

Source chunk (first 400 chars): {chunk_text}

Key metadata: {metadata_str}

Write EXACTLY ONE sentence (under 20 words) explaining the key connection. Focus on the most specific connection (Scripture references > concepts > topics). End with a period. Do not write multiple sentences."""
            }],
            temperature=0.2,  # Lower temperature for more consistent, concise output
            max_tokens=50  # Further reduced to enforce brevity (20 words max ≈ 50 tokens)
        )
        
        explanation = response.choices[0].message.content.strip()
        
        # Aggressive post-processing to ensure single sentence
        # Remove any trailing sentences
        sentences = explanation.split('. ')
        if len(sentences) > 1:
            # Take only the first sentence
            explanation = sentences[0].strip()
        
        # Also check for other sentence-ending punctuation
        for punct in ['!', '?']:
            if punct in explanation:
                parts = explanation.split(punct)
                if len(parts) > 1:
                    explanation = parts[0].strip()
                    break
        
        # Ensure it ends with a period
        if explanation and not explanation.endswith('.'):
            explanation += '.'
        
        # Final check: if still too long, truncate at first period
        if len(explanation.split()) > 25:  # Safety check for overly long sentences
            first_period = explanation.find('.')
            if first_period > 0:
                explanation = explanation[:first_period + 1]
        
        # Append similarity score
        explanation += f" (similarity: {similarity_score:.3f})"
        
        return explanation
        
    except Exception as e:
        print(f"Error generating relevance explanation: {e}")
        return f"Relevant content with similarity score {similarity_score:.3f}"

def generate_relevance_explanations_batch(query, chunks):
    """Generate relevance explanations for multiple chunks in a single API call"""
    try:
        if not chunks:
            return []
        
        # Prepare batch data for all chunks
        prep_start = time.time()
        chunks_data = []
        for i, chunk in enumerate(chunks):
            chunk_text = chunk.get('text', '')[:200]  # Reduced from 300 to 200 for faster processing
            similarity_score = chunk.get('similarity_score', 0)
            metadata = chunk.get('metadata', {})
            
            # Build metadata context (simplified)
            metadata_highlights = []
            if metadata.get('scripture_references'):
                refs = metadata['scripture_references'][:1]  # Reduced to 1
                metadata_highlights.append(f"Scripture: {', '.join(refs)}")
            if metadata.get('concepts'):
                concepts = metadata['concepts'][:1]  # Reduced to 1
                metadata_highlights.append(f"Concepts: {', '.join(concepts)}")
            
            metadata_str = " | ".join(metadata_highlights) if metadata_highlights else "General relevance"
            
            chunks_data.append({
                'index': i,
                'chunk_text': chunk_text,
                'metadata_str': metadata_str,
                'similarity_score': similarity_score
            })
        
        # Build batch prompt (more compact)
        chunks_prompt = "\n\n".join([
            f"{i+1}. {data['chunk_text'][:150]}... | {data['metadata_str']} | Score: {data['similarity_score']:.3f}"
            for i, data in enumerate(chunks_data)
        ])
        prep_time = time.time() - prep_start
        print(f"[TIMING] Batch prep time: {prep_time:.3f}s")
        
        # Single API call for all chunks
        api_start = time.time()
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "system",
                "content": """Generate one sentence per chunk explaining relevance. Format: "1: explanation. (similarity: 0.xxx)" for each chunk."""
            }, {
                "role": "user",
                "content": f"""Query: {query}

Chunks:
{chunks_prompt}

Generate numbered explanations (1:, 2:, etc.)"""
            }],
            temperature=0.2,
            max_tokens=600  # Reduced from 800
        )
        api_time = time.time() - api_start
        print(f"[TIMING] Batch API call time: {api_time:.2f}s")
        
        # Parse the response
        response_text = response.choices[0].message.content.strip()
        explanations = {}
        
        # Extract numbered explanations
        import re
        pattern = r'(\d+):\s*(.+?)(?=\d+:|$)'
        matches = re.findall(pattern, response_text, re.DOTALL)
        
        for match_num, explanation_text in matches:
            chunk_idx = int(match_num) - 1
            if chunk_idx < len(chunks):
                explanation = explanation_text.strip()
                # Ensure it ends with period
                if explanation and not explanation.endswith('.'):
                    explanation += '.'
                # Add similarity score if not already present
                similarity_score = chunks_data[chunk_idx]['similarity_score']
                if f"(similarity: {similarity_score:.3f})" not in explanation:
                    explanation += f" (similarity: {similarity_score:.3f})"
                explanations[chunk_idx] = explanation
        
        # Fallback: if parsing failed, try to extract by lines
        if len(explanations) < len(chunks):
            lines = response_text.split('\n')
            for i, line in enumerate(lines):
                if i < len(chunks) and line.strip():
                    explanation = line.strip()
                    # Remove leading numbers if present
                    explanation = re.sub(r'^\d+[:.]\s*', '', explanation)
                    if explanation and not explanation.endswith('.'):
                        explanation += '.'
                    similarity_score = chunks_data[i]['similarity_score']
                    if f"(similarity: {similarity_score:.3f})" not in explanation:
                        explanation += f" (similarity: {similarity_score:.3f})"
                    explanations[i] = explanation
        
        # Return explanations in order, with fallback for any missing ones
        result = []
        for i, chunk in enumerate(chunks):
            if i in explanations:
                result.append(explanations[i])
            else:
                # Fallback: simple explanation with similarity score
                similarity_score = chunk.get('similarity_score', 0)
                result.append(f"Relevant content matching query. (similarity: {similarity_score:.3f})")
        
        return result
        
    except Exception as e:
        print(f"Error generating batch relevance explanations: {e}")
        # Fallback: return simple explanations
        return [
            f"Relevant content matching query. (similarity: {chunk.get('similarity_score', 0):.3f})"
            for chunk in chunks
        ]

# ==================== ADMIN PANEL ROUTES ====================

@app.route('/admin')
def admin_panel():
    """Admin panel view for managing pipeline stages"""
    script_dir = Path(__file__).parent
    html_path = script_dir / 'admin_panel.html'
    
    try:
        with open(html_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        return html_content
    except FileNotFoundError:
        return f"Admin panel file not found at {html_path}. Please ensure admin_panel.html exists.", 404

@app.route('/api/admin/sources')
def get_admin_sources():
    """Get all sources at different pipeline stages"""
    try:
        script_dir = Path(__file__).parent
        base_dir = script_dir / 'theological_processing'
        
        sources_data = {
            'stage_2': [],
            'stage_3': [],
            'stage_4': [],
            'stage_5': []
        }
        
        # Stage 2: Chunked files
        chunked_dir = base_dir / '02_chunked'
        if chunked_dir.exists():
            for jsonl_file in chunked_dir.glob('*.jsonl'):
                if 'backup' not in jsonl_file.name.lower():
                    is_approved = (chunked_dir / f"{jsonl_file.name}.approved").exists()
                    # Count chunks
                    chunk_count = 0
                    with open(jsonl_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            if line.strip():
                                chunk_count += 1
                    
                    sources_data['stage_2'].append({
                        'filename': jsonl_file.name,
                        'path': str(jsonl_file.relative_to(base_dir)),
                        'approved': is_approved,
                        'chunk_count': chunk_count
                    })
        
        # Stage 3: Annotated files
        annotated_dir = base_dir / '03_annotated'
        if annotated_dir.exists():
            for jsonl_file in annotated_dir.glob('*_annotated.jsonl'):
                if 'backup' not in jsonl_file.name.lower():
                    is_approved = (annotated_dir / f"{jsonl_file.name}.approved").exists()
                    # Count chunks
                    chunk_count = 0
                    with open(jsonl_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            if line.strip():
                                chunk_count += 1
                    
                    sources_data['stage_3'].append({
                        'filename': jsonl_file.name,
                        'path': str(jsonl_file.relative_to(base_dir)),
                        'approved': is_approved,
                        'chunk_count': chunk_count
                    })
        
        # Stage 4: Complete files
        complete_dir = base_dir / '04_complete'
        if complete_dir.exists():
            for jsonl_file in complete_dir.glob('*.jsonl'):
                if 'backup' not in jsonl_file.name.lower():
                    chunk_count = 0
                    with open(jsonl_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            if line.strip():
                                chunk_count += 1
                    
                    sources_data['stage_4'].append({
                        'filename': jsonl_file.name,
                        'path': str(jsonl_file.relative_to(base_dir)),
                        'chunk_count': chunk_count
                    })
        
        # Stage 5: Deployed files
        deployed_dir = base_dir / '05_deployed'
        if deployed_dir.exists():
            for jsonl_file in deployed_dir.glob('*.jsonl'):
                if 'backup' not in jsonl_file.name.lower():
                    chunk_count = 0
                    with open(jsonl_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            if line.strip():
                                chunk_count += 1
                    
                    sources_data['stage_5'].append({
                        'filename': jsonl_file.name,
                        'path': str(jsonl_file.relative_to(base_dir)),
                        'chunk_count': chunk_count
                    })
        
        return jsonify(sources_data)
    except Exception as e:
        print(f"Error getting admin sources: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/chunks/<stage>', methods=['GET'])
def get_chunks(stage):
    """Get chunks from a specific stage (2 or 3)"""
    try:
        script_dir = Path(__file__).parent
        base_dir = script_dir / 'theological_processing'
        
        filename = request.args.get('filename')
        if not filename:
            return jsonify({"error": "filename parameter required"}), 400
        
        if stage == '2':
            file_path = base_dir / '02_chunked' / filename
        elif stage == '3':
            file_path = base_dir / '03_annotated' / filename
        else:
            return jsonify({"error": "stage must be 2 or 3"}), 400
        
        if not file_path.exists():
            return jsonify({"error": f"File not found: {filename}"}), 404
        
        chunks = []
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    try:
                        chunk = json.loads(line.strip())
                        chunks.append(chunk)
                    except json.JSONDecodeError:
                        continue
        
        is_approved = (file_path.parent / f"{file_path.name}.approved").exists()
        
        return jsonify({
            'chunks': chunks,
            'approved': is_approved,
            'total_count': len(chunks)
        })
    except Exception as e:
        print(f"Error getting chunks: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/chunks/<stage>', methods=['POST'])
def update_chunks(stage):
    """Update chunks in a specific stage"""
    try:
        script_dir = Path(__file__).parent
        base_dir = script_dir / 'theological_processing'
        
        data = request.get_json()
        filename = data.get('filename')
        chunks = data.get('chunks', [])
        
        if not filename:
            return jsonify({"error": "filename required"}), 400
        
        if stage == '2':
            file_path = base_dir / '02_chunked' / filename
        elif stage == '3':
            file_path = base_dir / '03_annotated' / filename
        else:
            return jsonify({"error": "stage must be 2 or 3"}), 400
        
        # Create backup before updating (replace any existing backup)
        backup_path = file_path.parent / f"{file_path.name}.backup"
        
        # Remove any existing backup files (both fixed and timestamped)
        if file_path.exists():
            import shutil
            
            # Remove the fixed backup if it exists
            if backup_path.exists():
                backup_path.unlink()
            
            # Remove any timestamped backups (from previous code versions)
            pattern = f"{file_path.name}.backup_*"
            for old_backup in file_path.parent.glob(pattern):
                old_backup.unlink()
            
            # Create new backup
            shutil.copy2(file_path, backup_path)
        
        # Write updated chunks with consistent field order
        # Put structure_path right after id for easy scanning of file structure
        field_order = ['id', 'structure_path', 'text', 'source', 'author', 'chunk_type', 'chunk_index', 
                       'processing_stage', 'processing_timestamp']
        
        # For stage 3, also include metadata fields
        if stage == '3':
            # Check if any chunks have metadata to determine field order
            has_metadata = any('metadata' in chunk for chunk in chunks)
            if has_metadata:
                field_order = ['id', 'structure_path', 'text', 'source', 'author', 'chunk_type', 'chunk_index', 
                              'processing_stage', 'processing_timestamp', 'metadata']
                # Add annotation_method and annotation_model if present
                if any('annotation_method' in chunk for chunk in chunks):
                    field_order.extend(['annotation_method', 'annotation_model'])
        
        def reorder_chunk(chunk):
            """Reorder chunk fields to match original format"""
            ordered_chunk = {}
            # Add fields in specified order
            for field in field_order:
                if field in chunk:
                    ordered_chunk[field] = chunk[field]
            # Add any remaining fields that weren't in the order list
            for key, value in chunk.items():
                if key not in ordered_chunk:
                    ordered_chunk[key] = value
            return ordered_chunk
        
        with open(file_path, 'w', encoding='utf-8') as f:
            for chunk in chunks:
                ordered_chunk = reorder_chunk(chunk)
                f.write(json.dumps(ordered_chunk, ensure_ascii=False) + '\n')
        
        return jsonify({
            'success': True,
            'message': f'Updated {len(chunks)} chunks',
            'backup': str(backup_path.name) if backup_path.exists() else None
        })
    except Exception as e:
        print(f"Error updating chunks: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/chunks/<stage>/approve', methods=['POST'])
def approve_chunks(stage):
    """Approve chunks in a specific stage"""
    try:
        script_dir = Path(__file__).parent
        base_dir = script_dir / 'theological_processing'
        
        data = request.get_json()
        filename = data.get('filename')
        
        if not filename:
            return jsonify({"error": "filename required"}), 400
        
        if stage == '2':
            file_path = base_dir / '02_chunked' / filename
        elif stage == '3':
            file_path = base_dir / '03_annotated' / filename
        else:
            return jsonify({"error": "stage must be 2 or 3"}), 400
        
        if not file_path.exists():
            return jsonify({"error": f"File not found: {filename}"}), 404
        
        # Create .approved file
        approved_path = file_path.parent / f"{file_path.name}.approved"
        approved_path.touch()
        
        return jsonify({
            'success': True,
            'message': f'Approved {filename}',
            'approved_path': str(approved_path.name)
        })
    except Exception as e:
        print(f"Error approving chunks: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/chunks/<stage>/unapprove', methods=['POST'])
def unapprove_chunks(stage):
    """Unapprove chunks in a specific stage"""
    try:
        script_dir = Path(__file__).parent
        base_dir = script_dir / 'theological_processing'
        
        data = request.get_json()
        filename = data.get('filename')
        
        if not filename:
            return jsonify({"error": "filename required"}), 400
        
        if stage == '2':
            file_path = base_dir / '02_chunked' / filename
        elif stage == '3':
            file_path = base_dir / '03_annotated' / filename
        else:
            return jsonify({"error": "stage must be 2 or 3"}), 400
        
        # Remove .approved file
        approved_path = file_path.parent / f"{file_path.name}.approved"
        if approved_path.exists():
            approved_path.unlink()
            return jsonify({
                'success': True,
                'message': f'Unapproved {filename}'
            })
        else:
            return jsonify({
                'success': False,
                'message': f'{filename} was not approved'
            })
    except Exception as e:
        print(f"Error unapproving chunks: {e}")
        return jsonify({"error": str(e)}), 500

# ==================== BACKUP ROUTES ====================

@app.route('/api/backup/search-history', methods=['POST'])
def backup_search_history():
    """Save search history backup to server"""
    try:
        data = request.get_json()
        history_data = data.get('history', [])
        
        if not history_data:
            return jsonify({"error": "No history data provided"}), 400
        
        script_dir = Path(__file__).parent
        backups_dir = script_dir / 'backups'
        backups_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'search_history_backup_{timestamp}.json'
        file_path = backups_dir / filename
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(history_data, f, indent=2, ensure_ascii=False)
        
        return jsonify({
            'success': True,
            'message': f'Backup saved: {filename}',
            'filename': filename,
            'path': str(file_path.relative_to(script_dir))
        })
    except Exception as e:
        print(f"Error backing up search history: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/backup/draft-history', methods=['POST'])
def backup_draft_history():
    """Save draft history backup to server"""
    try:
        data = request.get_json()
        history_data = data.get('history', [])
        
        if not history_data:
            return jsonify({"error": "No history data provided"}), 400
        
        script_dir = Path(__file__).parent
        backups_dir = script_dir / 'backups'
        backups_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'draft_history_backup_{timestamp}.json'
        file_path = backups_dir / filename
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(history_data, f, indent=2, ensure_ascii=False)
        
        return jsonify({
            'success': True,
            'message': f'Backup saved: {filename}',
            'filename': filename,
            'path': str(file_path.relative_to(script_dir))
        })
    except Exception as e:
        print(f"Error backing up draft history: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Load schema indices first
    load_schema_indices()
    
    # Load ChromaDB
    chromadb_loaded = load_chromadb()
    
    # Load dataset on startup (still needed for metadata and source tracking)
    if load_dataset():
        print("Dataset loaded successfully")
        print(f"Available sources: {[s['name'] for s in available_sources]}")
        if not chromadb_loaded:
            raise RuntimeError("ChromaDB initialization failed. Please run migrate_to_chroma.py first.")
        print("✅ Using ChromaDB for vector search (fast mode)")
        print("Starting Flask app on http://localhost:5001")
        app.run(debug=True, port=5001, host='127.0.0.1')
    else:
        print("Failed to load dataset")