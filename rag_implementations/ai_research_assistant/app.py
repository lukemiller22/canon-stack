from flask import Flask, render_template, request, jsonify
import json
import openai
from openai import OpenAI
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import re
from typing import List, Dict, Any
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file (look in parent directories too)
env_path = Path(__file__).parent.parent.parent / '.env'
load_dotenv(env_path)

app = Flask(__name__)

# Initialize OpenAI client
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY not found. Please set it in your .env file.")
client = OpenAI(api_key=api_key)

# Global variable to store the dataset
dataset = []

def load_dataset():
    """Load the theological chunks dataset from deployed sources."""
    global dataset
    from pathlib import Path
    
    dataset = []
    
    # Get the path to deployed sources (relative to this file)
    script_dir = Path(__file__).parent
    deployed_dir = script_dir.parent.parent / 'theological_processing' / '05_deployed'
    
    if not deployed_dir.exists():
        print(f"Error: Deployed directory not found: {deployed_dir}")
        return False
    
    try:
        # Load all JSONL files from the deployed directory
        jsonl_files = list(deployed_dir.glob('*.jsonl'))
        
        if not jsonl_files:
            print(f"Warning: No JSONL files found in {deployed_dir}")
            return False
        
        for jsonl_file in jsonl_files:
            print(f"Loading {jsonl_file.name}...")
            with open(jsonl_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        chunk = json.loads(line.strip())
                        dataset.append(chunk)
        
        print(f"Loaded {len(dataset)} chunks from {len(jsonl_files)} file(s)")
        return True
    except Exception as e:
        print(f"Error loading dataset: {e}")
        return False

def get_query_embedding(query: str) -> List[float]:
    """Get embedding for the query using OpenAI."""
    try:
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=query
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"Error getting query embedding: {e}")
        return None

def cosine_similarity_score(vec1: List[float], vec2: List[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    try:
        return cosine_similarity([vec1], [vec2])[0][0]
    except:
        return 0.0

def analyze_query(query: str) -> Dict[str, Any]:
    """Analyze the query to determine search strategy and filters."""
    
    analysis_prompt = f"""
You are a research assistant. Analyze this query and determine the best search strategy using the available metadata filters.

Query: "{query}"

Available metadata filters:
- Topics: Various theological topics (format: "Concept/Topic", e.g., "Apologetics/Personal vs Systematic")
- Concepts: Abstract concepts (e.g., "Apologetics", "Faith", "Theology")
- Terms: Key theological terms and phrases (e.g., "sanctification", "justification by faith", "divine sovereignty")
- Discourse Elements: Rhetorical functions (format: "Category/Element", e.g., "Symbolic/Metaphor", "Logical/Claim", "Personal/Intention")
- Scripture References: Biblical references (e.g., "John 3:16", "John 1")
- Named Entities: Names and entities (format: "Class/Entity", e.g., "Person/Gilbert K. Chesterton", "Work/Heretics")
- Structure Path: Document structure (e.g., "Chapter I > I. INTRODUCTION IN DEFENCE OF EVERYTHING ELSE")
- Authors: Source authors (e.g., "Gilbert K. Chesterton", "John Calvin")

Analyze the query and respond with a JSON object containing:
1. "query_type": The type of question (definition, comparison, historical, doctrinal, exegetical, etc.)
2. "theological_concepts": List of theological concepts identified
3. "search_strategy": Description of how to search (vector similarity + specific filters)
4. "recommended_filters": Object with specific filter recommendations
5. "reasoning": Explanation of why these filters were chosen

IMPORTANT: Be intelligent about detecting metadata matches:
- If the query mentions discourse element types (metaphors, claims, definitions, narratives, etc.) → filter by discourse_elements (e.g., "Symbolic/Metaphor", "Logical/Claim")
- If the query mentions specific authors (Calvin, Luther, Chesterton, etc.) → filter by authors
- If the query mentions biblical books/passages → filter by scripture_references
- If the query asks about specific theological topics → filter by topics (format: "Concept/Topic")
- If the query asks about concepts like "sanctification", "justification", "trinity" → filter by concepts (e.g., "Sanctification", "Justification", "Trinity")
- If the query mentions specific theological terms or phrases → filter by terms (e.g., "justification by faith", "divine sovereignty")
- If the query mentions people, works, places → filter by named_entities (format: "Class/Entity")

Example responses:

For "What are some metaphors for sanctification?":
{{
    "query_type": "doctrinal",
    "theological_concepts": ["sanctification", "spiritual growth", "transformation"],
    "search_strategy": "Search for chunks about sanctification using vector similarity, then filter by discourse_elements containing Symbolic/Metaphor to find metaphorical language",
    "recommended_filters": {{
        "discourse_elements": ["Symbolic/Metaphor"],
        "concepts": ["Sanctification", "Spiritual Growth"],
        "topics": ["Sanctification/Spiritual Growth", "Spiritual Growth/Transformation"]
    }},
    "reasoning": "The query specifically asks for metaphors, so I'm prioritizing discourse_elements with Symbolic/Metaphor to find sources with metaphorical language about sanctification."
}}

For "What does Calvin say about predestination?":
{{
    "query_type": "historical",
    "theological_concepts": ["predestination", "election", "divine sovereignty"],
    "search_strategy": "Search for chunks about predestination using vector similarity, then filter by Calvin as author and topics related to predestination",
    "recommended_filters": {{
        "authors": ["John Calvin"],
        "topics": ["Predestination/Divine Sovereignty", "Election/Predestination"],
        "concepts": ["Divine Sovereignty", "Election"]
    }},
    "reasoning": "The query specifically asks about Calvin's views, so I'm filtering by Calvin as author and topics/concepts related to predestination."
}}

For "What are the logical arguments for the Trinity?":
{{
    "query_type": "doctrinal",
    "theological_concepts": ["trinity", "three persons", "one God"],
    "search_strategy": "Search for chunks about the Trinity using vector similarity, then filter by discourse_elements containing Logical/Claim to find argumentative content",
    "recommended_filters": {{
        "discourse_elements": ["Logical/Claim"],
        "topics": ["Trinity/Doctrine", "God/Trinity"],
        "concepts": ["God", "Trinity"]
    }},
    "reasoning": "The query asks for logical arguments, so I'm prioritizing discourse_elements with Logical/Claim to find sources with argumentative content about the Trinity."
}}

For "What passages from Augustine's Confessions talk about John 14:6?":
{{
    "query_type": "exegetical",
    "theological_concepts": ["Jesus Christ", "Incarnation", "Scripture"],
    "search_strategy": "Search for chunks about John 14:6 using vector similarity, then filter by Augustine as author and scripture_references containing John 14:6",
    "recommended_filters": {{
        "authors": ["St. Augustine", "Augustine"],
        "scripture_references": ["John 14:6"],
        "topics": ["Jesus Christ/Mediator", "Incarnation/Word Made Flesh"],
        "concepts": ["Jesus Christ", "Scripture"]
    }},
    "reasoning": "The query specifically asks about John 14:6 in Augustine's Confessions, so I'm filtering by scripture_references containing John 14:6 and by Augustine as the author to find relevant passages."
}}

Respond with only the JSON object, no other text.
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": analysis_prompt}],
            temperature=0.3
        )
        
        # Extract JSON from response
        content = response.choices[0].message.content.strip()
        # Remove any markdown formatting
        if content.startswith("```json"):
            content = content[7:]
        if content.endswith("```"):
            content = content[:-3]
        
        return json.loads(content)
    except Exception as e:
        print(f"Error analyzing query: {e}")
        return {
            "query_type": "general",
            "theological_concepts": [],
            "search_strategy": "General vector similarity search",
            "recommended_filters": {},
            "reasoning": "Error in analysis, using general search"
        }

def search_with_filters(query: str, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Search the dataset using hybrid approach: exact phrase matching + vector similarity + metadata filters."""
    
    # Get query embedding
    query_embedding = get_query_embedding(query)
    if not query_embedding:
        return []
    
    # Extract key phrases from query for exact matching
    query_lower = query.lower()
    key_phrases = extract_key_phrases(query_lower)
    
    # Search results
    search_results = []
    recommended_filters = analysis.get("recommended_filters", {})
    
    # Debug logging for filter extraction
    if recommended_filters:
        print(f"DEBUG: Recommended filters from query analysis: {json.dumps(recommended_filters, indent=2)}")
        if 'scripture_references' in recommended_filters:
            print(f"DEBUG: Scripture references filter: {recommended_filters['scripture_references']}")
    else:
        print("DEBUG: No recommended filters found in query analysis")
    
    for chunk in dataset:
        chunk_text = chunk.get("text", "").lower()
        chunk_metadata = chunk.get("metadata", {})
        
        # Calculate scores
        exact_match_score = 0
        vector_similarity_score = 0
        filter_match_score = 0
        
        # 1. Exact phrase matching
        for phrase in key_phrases:
            if phrase in chunk_text:
                exact_match_score += 1
        
        # 2. Vector similarity
        if chunk.get("embedding"):
            vector_similarity_score = cosine_similarity_score(query_embedding, chunk["embedding"])
        
        # 3. Metadata filtering
        if recommended_filters:
            for filter_type, filter_values in recommended_filters.items():
                # Map filter type names to metadata field names
                metadata_field_map = {
                    'function': 'discourse_elements',  # Legacy name compatibility
                    'authors': None,  # Handled at top level, not in metadata
                    'topics': 'topics',
                    'concepts': 'concepts',
                    'terms': 'terms',
                    'scripture_references': 'scripture_references',
                    'structure_paths': 'structure_path',
                    'discourse_elements': 'discourse_elements',
                    'named_entities': 'named_entities'
                }
                
                # Check author filter (top-level field)
                if filter_type == 'authors':
                    chunk_author = chunk.get("author", "")
                    for filter_val in filter_values:
                        if filter_val.lower() in chunk_author.lower():
                            filter_match_score += 1
                            break
                else:
                    # Get the actual metadata field name
                    metadata_field = metadata_field_map.get(filter_type, filter_type)
                    
                    if metadata_field and metadata_field in chunk_metadata:
                        chunk_values = chunk_metadata[metadata_field]
                        
                        # Handle discourse_elements specially - use discourse_tags if available (more efficient)
                        if metadata_field == 'discourse_elements':
                            # First try discourse_tags (direct tag matching - faster and more reliable)
                            discourse_tags = chunk_metadata.get('discourse_tags', [])
                            if discourse_tags and isinstance(discourse_tags, list):
                                for filter_val in filter_values:
                                    filter_lower = filter_val.lower()
                                    # Exact match or namespace match (e.g., "Symbolic" matches "Symbolic" and "Symbolic/Metaphor")
                                    for tag in discourse_tags:
                                        tag_lower = tag.lower()
                                        if tag_lower == filter_lower or (not '/' in filter_lower and tag_lower.startswith(filter_lower + '/')):
                                            filter_match_score += 1
                                            break
                                    if filter_match_score > 0:  # Already matched, no need to continue
                                        break
                            # Fallback: extract from discourse_elements strings (for backward compatibility)
                            else:
                                if isinstance(chunk_values, list):
                                    for chunk_val in chunk_values:
                                        # Extract category/element from format "[[Category/Element]] description"
                                        element_match = re.search(r'\[\[([^\]]+)\]\]', chunk_val)
                                        if element_match:
                                            element = element_match.group(1)
                                            for filter_val in filter_values:
                                                filter_lower = filter_val.lower()
                                                element_lower = element.lower()
                                                if filter_lower == element_lower or (not '/' in filter_lower and element_lower.startswith(filter_lower + '/')):
                                                    filter_match_score += 1
                                                    break
                        # Handle scripture_references with exact or normalized matching
                        elif metadata_field == 'scripture_references':
                            if isinstance(chunk_values, list):
                                for filter_val in filter_values:
                                    filter_lower = filter_val.lower().strip()
                                    # Normalize scripture references (remove extra spaces, handle variations)
                                    filter_normalized = re.sub(r'\s+', ' ', filter_lower)
                                    matched = False
                                    for chunk_val in chunk_values:
                                        chunk_val_str = str(chunk_val).lower().strip()
                                        chunk_normalized = re.sub(r'\s+', ' ', chunk_val_str)
                                        # Debug logging for scripture references
                                        if 'john 14:6' in filter_normalized or 'john 14:6' in chunk_normalized:
                                            print(f"DEBUG scripture_references: Filter='{filter_normalized}', Chunk='{chunk_normalized}', Match={filter_normalized == chunk_normalized}")
                                        # Exact match (preferred)
                                        if filter_normalized == chunk_normalized:
                                            filter_match_score += 1
                                            matched = True
                                            if 'john 14:6' in filter_normalized:
                                                print(f"DEBUG: Exact match found for {filter_normalized}")
                                            break
                                        # If filter is a verse (has ':'), match exact verse or parent chapter
                                        elif ':' in filter_normalized:
                                            filter_chapter = filter_normalized.split(':')[0]
                                            # Match if chunk starts with same chapter (e.g., "John 10:1" matches "John 10" or "John 10:1-7")
                                            if chunk_normalized.startswith(filter_chapter):
                                                filter_match_score += 1
                                                matched = True
                                                if 'john 14:6' in filter_normalized:
                                                    print(f"DEBUG: Chapter match found - Filter chapter: {filter_chapter}, Chunk: {chunk_normalized}")
                                                break
                                        # If filter is a chapter (no ':'), match any verse in that chapter
                                        elif ':' in chunk_normalized:
                                            chunk_chapter = chunk_normalized.split(':')[0]
                                            if chunk_chapter == filter_normalized:
                                                filter_match_score += 1
                                                matched = True
                                                if 'john 14' in filter_normalized:
                                                    print(f"DEBUG: Chapter-to-verse match found - Filter: {filter_normalized}, Chunk: {chunk_normalized}")
                                                break
                                    if matched:  # Already matched, no need to check other filter values
                                        break
                        elif isinstance(chunk_values, list):
                            # Regular list matching
                            for chunk_val in chunk_values:
                                for filter_val in filter_values:
                                    if filter_val.lower() in str(chunk_val).lower():
                                        filter_match_score += 1
                                        break
                        elif isinstance(chunk_values, str):
                            # Handle string fields like structure_path
                            for filter_val in filter_values:
                                if filter_val.lower() in chunk_values.lower():
                                    filter_match_score += 1
                                    break
        else:
            # If no specific filters, give all chunks a base filter score
            filter_match_score = 0.5
        
        # Calculate combined score
        # Weight exact matches heavily, then vector similarity, then filters (increased from 0.5 to 2.0)
        # This ensures chunks with perfect filter matches rank higher
        combined_score = (exact_match_score * 2.0) + (vector_similarity_score * 1.5) + (filter_match_score * 2.0)
        
        # Boost chunks that match any filters (prioritize filter matches)
        if filter_match_score > 0:
            combined_score += 1.0  # Additional boost for filter matches
        
        # Only include chunks with some relevance
        if combined_score > 0.1 or exact_match_score > 0:
            chunk["similarity_score"] = combined_score
            chunk["exact_match_score"] = exact_match_score
            chunk["vector_score"] = vector_similarity_score
            chunk["filter_score"] = filter_match_score
            search_results.append(chunk)
    
    # Sort by combined score
    search_results.sort(key=lambda x: x.get("similarity_score", 0), reverse=True)
    
    # Return top 15 results (increased from 10 to catch more relevant material)
    return search_results[:15]

def extract_key_phrases(query: str) -> List[str]:
    """Extract key phrases from the query for exact matching."""
    # Remove common words and extract meaningful phrases
    common_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 'what', 'how', 'why', 'when', 'where', 'who', 'which', 'that', 'this', 'these', 'those'}
    
    # Split into words and filter out common words
    words = query.split()
    meaningful_words = [word.strip('.,!?;:"()[]{}') for word in words if word.lower() not in common_words]
    
    # Create phrases of 1-3 words
    phrases = []
    for i in range(len(meaningful_words)):
        # Single words
        phrases.append(meaningful_words[i])
        # Two-word phrases
        if i < len(meaningful_words) - 1:
            phrases.append(f"{meaningful_words[i]} {meaningful_words[i+1]}")
        # Three-word phrases
        if i < len(meaningful_words) - 2:
            phrases.append(f"{meaningful_words[i]} {meaningful_words[i+1]} {meaningful_words[i+2]}")
    
    # Remove duplicates and return
    return list(set(phrases))

def generate_research_summary(query: str, analysis: Dict[str, Any], chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate a research summary with citations."""
    
    # Prepare chunks for the AI
    chunks_text = ""
    for i, chunk in enumerate(chunks, 1):
        source = chunk.get("source", "Unknown")
        author = chunk.get("author", "Unknown")
        # structure_path is now a string in metadata (format: "[[Chapter I > Section]]")
        structure_path = chunk.get("metadata", {}).get("structure_path", "")
        # Remove brackets if present
        if structure_path.startswith("[["):
            structure_path = structure_path[2:]
        if structure_path.endswith("]]"):
            structure_path = structure_path[:-2]
        structure = structure_path if structure_path else "Unknown"
        
        text = chunk.get("text", "")
        
        chunk_id = chunk.get("id", f"chunk_{i}")
        chunks_text += f"""
[Source {i}]
Chunk ID: {chunk_id}
Source: {source}
Author: {author}
Location: {structure}
Text: {text}
Similarity Score: {chunk.get("similarity_score", 0):.3f}
---
"""
    
    synthesis_prompt = f"""
You are a research assistant. Based on the query analysis and retrieved chunks, provide a comprehensive research summary.

Query: "{query}"

Query Analysis:
- Type: {analysis.get('query_type', 'general')}
- Concepts: {', '.join(analysis.get('theological_concepts', []))}
- Strategy: {analysis.get('search_strategy', '')}
- Reasoning: {analysis.get('reasoning', '')}

Retrieved Chunks:
{chunks_text}

Instructions:
1. Write a comprehensive summary that directly addresses the query
2. Use numbered citations [1], [2], etc. for each source
3. Synthesize information from multiple sources when relevant
4. Be specific and cite particular claims or arguments - use direct quotes and specific details from the sources
5. Pay special attention to exact phrases and key terms found in the sources
6. If information is limited, acknowledge this and work with what's available
7. Maintain accuracy and nuance appropriate to the domain
8. CRITICAL: Don't paraphrase key concepts - use the exact language from the sources when it's more precise
9. IMPORTANT: Fully utilize the content from each retrieved chunk - don't just mention sources in passing, but engage deeply with their arguments and examples

Format your response as JSON:
{{
    "summary": "Your comprehensive research summary with numbered citations",
    "sources_used": [
        {{
            "number": 1,
            "chunk_id": "ORTHODOX_CHESTE_0",
            "source": "Source Name",
            "author": "Author Name", 
            "location": "Structure Path",
            "relevance": "Brief explanation of why this source was relevant"
        }}
    ],
    "reasoning_transparency": "Explanation of the search strategy and filter choices made"
}}

IMPORTANT: Include the "chunk_id" field exactly as shown in [Source X] for each source you reference.

CRITICAL CITATION RULES:
1. The citation numbers in your summary MUST correspond exactly to the source numbers in your sources_used array
2. If you have 3 sources numbered 1, 2, 3, you can ONLY use citations [1], [2], [3] in your summary
3. Do NOT skip numbers or use numbers that don't exist in your sources_used array
4. Do NOT use citations like [9], [10], [11], [13] unless those exact numbers exist in your sources_used array
5. Count your sources_used array first, then use only those numbers in your citations

Respond with only the JSON object, no other text.
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": synthesis_prompt}],
            temperature=0.3
        )
        
        content = response.choices[0].message.content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.endswith("```"):
            content = content[:-3]
        
        result = json.loads(content)
        
        # Validate and fix citation mismatches
        sources_used = result.get("sources_used", [])
        summary = result.get("summary", "")
        
        # FIRST: Find which sources are actually cited in the summary
        import re
        citation_pattern = re.compile(r'\[(\d+)\]')
        citations_in_summary = set(int(num) for num in citation_pattern.findall(summary) if num.isdigit())
        
        # Keep all sources but will renumber them sequentially
        # Sort by original number to preserve order
        sources_used.sort(key=lambda s: s.get("number", 999))
        
        # Renumber sources sequentially (1, 2, 3, ...) and create mapping from old to new
        old_to_new_mapping = {}
        for new_num, source in enumerate(sources_used, start=1):
            old_num = source.get("number")
            if old_num:
                old_to_new_mapping[int(old_num)] = new_num
            source["number"] = new_num
        
        # Map source numbers from AI to actual chunk indices
        # The AI sees chunks as [Source 1], [Source 2], etc. where 1 = chunks[0], 2 = chunks[1], etc.
        # We need to match the AI's source numbers to the actual chunks array
        for source in sources_used:
            source_num = source.get("number")
            chunk_index = None
            
            # First try: Match by chunk_id if provided (most reliable)
            chunk_id = source.get("chunk_id")
            if chunk_id:
                for i, chunk in enumerate(chunks):
                    if chunk.get("id") == chunk_id:
                        chunk_index = i
                        break
            
            # Second try: Match by source number (AI numbering corresponds to chunks array order)
            if chunk_index is None and source_num and source_num > 0 and source_num <= len(chunks):
                # AI numbers sources starting from 1, chunks array is 0-indexed
                chunk_index = source_num - 1
            
            # Third try: Match by source/author/location
            if chunk_index is None:
                source_name = source.get("source", "")
                source_author = source.get("author", "")
                source_location = source.get("location", "")
                
                for i, chunk in enumerate(chunks):
                    chunk_source = chunk.get("source", "Unknown")
                    chunk_author = chunk.get("author", "Unknown")
                    chunk_structure = chunk.get("metadata", {}).get("structure_path", "")
                    # Remove brackets if present
                    if chunk_structure.startswith("[["):
                        chunk_structure = chunk_structure[2:]
                    if chunk_structure.endswith("]]"):
                        chunk_structure = chunk_structure[:-2]
                    chunk_structure = chunk_structure if chunk_structure else "Unknown"
                    
                    # Match location more flexibly (check if location is contained in structure_path)
                    location_match = True
                    if source_location and source_location != "Unknown":
                        location_match = source_location in chunk_structure or chunk_structure in source_location
                    
                    if (chunk_source == source_name and 
                        chunk_author == source_author and
                        (not source_location or location_match)):
                        chunk_index = i
                        break
            
            if chunk_index is not None and chunk_index < len(chunks):
                source["_chunk_index"] = chunk_index
            else:
                # Log warning for debugging
                print(f"⚠️  Warning: Could not map source {source_num} (ID: {chunk_id}) to chunk index. Source: {source.get('source')}, Author: {source.get('author')}, Location: {source.get('location')}")
        
        # Update all citations in summary to match new sequential numbering
        citation_matches = list(citation_pattern.finditer(summary))
        fixed_summary = summary
        
        # Replace from end to start to preserve string positions
        for match in reversed(citation_matches):
            old_citation_num = int(match.group(1))
            if old_citation_num in old_to_new_mapping:
                new_citation_num = old_to_new_mapping[old_citation_num]
                start_pos = match.start()
                end_pos = match.end()
                fixed_summary = fixed_summary[:start_pos] + f'[{new_citation_num}]' + fixed_summary[end_pos:]
            else:
                # Citation doesn't map to any source - remove it
                start_pos = match.start()
                end_pos = match.end()
                fixed_summary = fixed_summary[:start_pos] + fixed_summary[end_pos:]
                print(f"⚠️  Removed unmapped citation [{old_citation_num}]")
        
        # Update the summary with fixed citations
        result["summary"] = fixed_summary
        
        # Log the renumbering
        if old_to_new_mapping and len(old_to_new_mapping) > 0:
            print(f"📝 Renumbered citations sequentially: {old_to_new_mapping}")
        
        return result
    except Exception as e:
        print(f"Error generating summary: {e}")
        return {
            "summary": "Error generating research summary.",
            "sources_used": [],
            "reasoning_transparency": "Error in synthesis process"
        }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        
        if not query:
            return jsonify({"error": "Query is required"}), 400
        
        if not dataset:
            return jsonify({"error": "Dataset not loaded"}), 500
        
        # Step 1: Analyze the query
        analysis = analyze_query(query)
        
        # Step 2: Search with filters
        chunks = search_with_filters(query, analysis)
        
        # Step 3: Generate research summary
        result = generate_research_summary(query, analysis, chunks)
        
        # Add the analysis and chunks to the result
        result["query_analysis"] = analysis
        result["chunks"] = chunks
        
        return jsonify(result)
        
    except Exception as e:
        print(f"Error in search: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Load dataset on startup
    if load_dataset():
        print("Dataset loaded successfully")
        print("Starting Flask app on http://localhost:5001")
        app.run(debug=True, port=5001, host='127.0.0.1')
    else:
        print("Failed to load dataset")
