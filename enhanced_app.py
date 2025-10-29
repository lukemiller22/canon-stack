import json
import re
from flask import Flask, request, jsonify
from openai import OpenAI
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import os
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

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

def load_dataset():
    """Load the theological chunks dataset from deployed sources"""
    global dataset, available_sources
    
    # Get the path to deployed sources (relative to this file)
    script_dir = Path(__file__).parent
    deployed_dir = script_dir / 'theological_processing' / '05_deployed'
    
    if not deployed_dir.exists():
        print(f"Error: Deployed directory not found: {deployed_dir}")
        return False
    
    try:
        dataset = []
        sources_map = {}
        
        # Load all JSONL files from the deployed directory
        jsonl_files = list(deployed_dir.glob('*.jsonl'))
        
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
        print(f"✅ Loaded {len(dataset)} chunks from {len(available_sources)} sources")
        return True
    except Exception as e:
        print(f"Error loading dataset: {e}")
        return False

def get_embedding(text):
    """Get embedding for a text using OpenAI API"""
    try:
        response = client.embeddings.create(
            input=text,
            model="text-embedding-3-small"
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"Error getting embedding: {e}")
        return None

def analyze_query(query):
    """Use AI to analyze the theological query and determine search strategy"""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "system",
                "content": """You are an expert theological research assistant. Analyze queries to determine the best search strategy and filters.

For each query, identify:
1. Query type (doctrinal, exegetical, historical, biographical, comparative, practical, etc.)
2. Key theological concepts involved
3. Suggested metadata filters to use (topics, concepts, functions, scripture references, etc.)
4. Search strategy explanation

Respond in JSON format:
{
    "query_type": "doctrinal|exegetical|historical|biographical|comparative|practical|other",
    "theological_concepts": ["concept1", "concept2"],
    "suggested_filters": {
        "topics": ["topic1", "topic2"],
        "concepts": ["concept1", "concept2"],
        "functions": ["function1", "function2"],
        "scripture_references": ["ref1", "ref2"]
    },
    "search_strategy": "Explanation of why these filters and approach were chosen"
}"""
            }, {
                "role": "user",
                "content": f"Analyze this theological query: {query}"
            }],
            temperature=0.3
        )
        
        analysis = json.loads(response.choices[0].message.content)
        return analysis
    except Exception as e:
        print(f"Error analyzing query: {e}")
        return {
            "query_type": "general",
            "theological_concepts": [],
            "suggested_filters": {},
            "search_strategy": "Using basic vector similarity search"
        }

def search_with_filters(query, analysis, selected_sources=None):
    """Perform intelligent search combining vector similarity with metadata filtering"""
    try:
        # Get query embedding
        query_embedding = get_embedding(query)
        if not query_embedding:
            return []
        
        # Filter dataset by selected sources
        filtered_dataset = dataset
        if selected_sources and len(selected_sources) > 0:
            filtered_dataset = []
            for chunk in dataset:
                source_key = f"{chunk.get('source', 'Unknown')}_{chunk.get('author', 'Unknown')}"
                source_id = source_key.lower().replace(' ', '_').replace('.', '').replace('/', '_')
                if source_id in selected_sources:
                    filtered_dataset.append(chunk)
        
        if not filtered_dataset:
            return []
        
        # Calculate similarities
        query_embedding_array = np.array([query_embedding])
        chunk_embeddings = []
        valid_chunks = []
        
        for chunk in filtered_dataset:
            if 'embedding' in chunk and chunk['embedding']:
                chunk_embeddings.append(chunk['embedding'])
                valid_chunks.append(chunk)
        
        if not chunk_embeddings:
            return []
        
        embeddings_array = np.array(chunk_embeddings)
        similarities = cosine_similarity(query_embedding_array, embeddings_array)[0]
        
        # Score chunks with similarity + metadata boost
        scored_chunks = []
        for i, chunk in enumerate(valid_chunks):
            base_score = similarities[i]
            metadata_boost = calculate_metadata_boost(chunk, analysis)
            final_score = base_score + metadata_boost
            
            scored_chunks.append({
                **chunk,
                'similarity_score': float(base_score),
                'metadata_boost': float(metadata_boost),
                'final_score': float(final_score)
            })
        
        # Sort by final score and return top results
        scored_chunks.sort(key=lambda x: x['final_score'], reverse=True)
        return scored_chunks[:15]  # Return top 15 chunks
        
    except Exception as e:
        print(f"Error in search: {e}")
        return []

def calculate_metadata_boost(chunk, analysis):
    """Calculate metadata-based relevance boost"""
    boost = 0.0
    metadata = chunk.get('metadata', {})
    suggested = analysis.get('suggested_filters', {})
    
    # Topic matching
    chunk_topics = metadata.get('topics', [])
    suggested_topics = suggested.get('topics', [])
    if chunk_topics and suggested_topics:
        topic_overlap = len(set(chunk_topics) & set(suggested_topics))
        boost += topic_overlap * 0.1
    
    # Concept matching
    chunk_concepts = metadata.get('concepts', [])
    suggested_concepts = suggested.get('concepts', [])
    if chunk_concepts and suggested_concepts:
        concept_overlap = len(set(chunk_concepts) & set(suggested_concepts))
        boost += concept_overlap * 0.08
    
    # Function type relevance
    chunk_functions = metadata.get('discourse_elements', [])
    if chunk_functions:
        # Boost logical/argumentative content for doctrinal queries
        if analysis.get('query_type') == 'doctrinal':
            logical_patterns = ['Logical/', 'Claim/', 'Argument/']
            for func in chunk_functions:
                if any(pattern in func for pattern in logical_patterns):
                    boost += 0.05
        
        # Boost historical/narrative content for historical queries
        if analysis.get('query_type') == 'historical':
            historical_patterns = ['Historical/', 'Narrative/', 'Event/']
            for func in chunk_functions:
                if any(pattern in func for pattern in historical_patterns):
                    boost += 0.05
    
    return min(boost, 0.3)  # Cap boost at 0.3

def generate_research_summary(query, analysis, chunks):
    """Generate comprehensive research summary with proper citations"""
    try:
        if not chunks:
            return {
                "summary": "No relevant sources found for this query.",
                "sources_used": [],
                "reasoning_transparency": analysis.get('search_strategy', 'No search strategy available')
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

Guidelines:
- Use citations frequently to support statements
- Maintain respectful tone for all theological traditions
- Be comprehensive but concise
- Include multiple perspectives when sources differ
- Make clear distinctions between biblical text, historical positions, and theological interpretations"""
            }, {
                "role": "user",
                "content": f"""Research question: {query}

Available sources:
{context_text}

Create a comprehensive research summary with proper numbered citations."""
            }],
            temperature=0.5,
            max_tokens=1500
        )
        
        summary = response.choices[0].message.content
        
        # Extract citations and create source list
        citation_pattern = re.compile(r'\[(\d+)\]')
        cited_numbers = set()
        for match in citation_pattern.finditer(summary):
            try:
                cited_numbers.add(int(match.group(1)))
            except ValueError:
                continue
        
        # Build sources list with explanations
        sources_used = []
        for i, chunk in enumerate(chunks[:10], 1):
            if i in cited_numbers:
                source_entry = {
                    'source': chunk.get('source', 'Unknown Source'),
                    'author': chunk.get('author', 'Unknown Author'),
                    'location': chunk.get('metadata', {}).get('structure_path', 'Unknown'),
                    'relevance_explanation': f"Similarity: {chunk.get('similarity_score', 0):.3f}, Relevance: {chunk.get('final_score', 0):.3f}",
                    'chunk_id': chunk.get('id', ''),
                    '_chunk_index': chunk.get('_chunk_index', i-1),
                    'metadata': chunk.get('metadata', {})
                }
                sources_used.append(source_entry)
        
        # Renumber citations to be sequential
        old_to_new_mapping = {}
        for new_num, old_num in enumerate(sorted(cited_numbers), 1):
            old_to_new_mapping[old_num] = new_num
        
        # Update sources list to match new numbering
        renumbered_sources = []
        for old_num in sorted(cited_numbers):
            chunk_index = old_num - 1
            if chunk_index < len(chunks):
                chunk = chunks[chunk_index]
                source_entry = {
                    'source': chunk.get('source', 'Unknown Source'),
                    'author': chunk.get('author', 'Unknown Author'),
                    'location': chunk.get('metadata', {}).get('structure_path', 'Unknown'),
                    'relevance_explanation': f"Provides relevant content with similarity score {chunk.get('similarity_score', 0):.3f}",
                    'chunk_id': chunk.get('id', ''),
                    '_chunk_index': chunk.get('_chunk_index', chunk_index),
                    'metadata': chunk.get('metadata', {})
                }
                renumbered_sources.append(source_entry)
        
        # Fix citations in summary
        citation_matches = list(citation_pattern.finditer(summary))
        fixed_summary = summary
        
        for match in reversed(citation_matches):
            old_citation_num = int(match.group(1))
            if old_citation_num in old_to_new_mapping:
                new_citation_num = old_to_new_mapping[old_citation_num]
                start_pos = match.start()
                end_pos = match.end()
                fixed_summary = fixed_summary[:start_pos] + f'[{new_citation_num}]' + fixed_summary[end_pos:]
        
        return {
            "summary": fixed_summary,
            "sources_used": renumbered_sources,
            "reasoning_transparency": analysis.get('search_strategy', 'No search strategy available')
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
        
        # Step 1: Analyze the query
        analysis = analyze_query(query)
        
        # Step 2: Search with filters and source selection
        chunks = search_with_filters(query, analysis, selected_sources)
        
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
        print(f"Available sources: {[s['name'] for s in available_sources]}")
        print("Starting Flask app on http://localhost:5001")
        app.run(debug=True, port=5001, host='127.0.0.1')
    else:
        print("Failed to load dataset")