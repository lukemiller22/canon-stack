from flask import Flask, render_template, request, jsonify
import json
import openai
from openai import OpenAI
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import re
from typing import List, Dict, Any
import os

app = Flask(__name__)

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Global variable to store the dataset
dataset = []

def load_dataset():
    """Load the theological chunks dataset."""
    global dataset
    try:
        with open('theological_chunks_with_embeddings.jsonl', 'r', encoding='utf-8') as f:
            dataset = []
            for line in f:
                if line.strip():
                    chunk = json.loads(line.strip())
                    dataset.append(chunk)
        print(f"Loaded {len(dataset)} chunks")
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
- Topics: Various theological topics (e.g., "Topic/Jesus Christ", "Topic/Deity of Christ")
- Concepts: Abstract concepts (e.g., "Concept/God", "Concept/Being", "Concept/Truth")
- Themes: Thematic elements (e.g., "Divine Word", "Life and Light")
- Function: Rhetorical functions (e.g., "Symbolic/Metaphor", "Logical/Claim", "Narrative/Origin")
- Scripture References: Biblical references (e.g., "John 1:1", "Deuteronomy 6:4")
- Proper Nouns: Names and proper nouns (e.g., "Jesus", "Calvin", "Luther")
- Structure Path: Document structure (e.g., "The Scriptures > John > John 1:1-14")
- Authors: Source authors (e.g., "John Calvin", "Charles Spurgeon")

Analyze the query and respond with a JSON object containing:
1. "query_type": The type of question (definition, comparison, historical, doctrinal, exegetical, etc.)
2. "theological_concepts": List of theological concepts identified
3. "search_strategy": Description of how to search (vector similarity + specific filters)
4. "recommended_filters": Object with specific filter recommendations
5. "reasoning": Explanation of why these filters were chosen

IMPORTANT: Be intelligent about detecting metadata matches:
- If the query mentions function types (metaphors, claims, definitions, narratives, etc.) → filter by relevant function types
- If the query mentions specific authors (Calvin, Luther, Lewis, etc.) → filter by those authors
- If the query mentions biblical books/passages → filter by scripture_references
- If the query asks about specific theological topics → filter by relevant topics
- If the query asks about concepts like "sanctification", "justification", "trinity" → filter by concepts
- If the query asks about themes like "divine love", "spiritual growth" → filter by themes

Example responses:

For "What are some metaphors for sanctification?":
{{
    "query_type": "doctrinal",
    "theological_concepts": ["sanctification", "spiritual growth", "transformation"],
    "search_strategy": "Search for chunks about sanctification using vector similarity, then filter by Symbolic/Metaphor function to find metaphorical language",
    "recommended_filters": {{
        "function": ["Symbolic/Metaphor"],
        "concepts": ["Concept/Spiritual Growth", "Concept/Transformation"],
        "topics": ["Topic/Sanctification", "Topic/Spiritual Life"]
    }},
    "reasoning": "The query specifically asks for metaphors, so I'm prioritizing Symbolic/Metaphor function metadata to find sources with metaphorical language about sanctification."
}}

For "What does Calvin say about predestination?":
{{
    "query_type": "historical",
    "theological_concepts": ["predestination", "election", "divine sovereignty"],
    "search_strategy": "Search for chunks about predestination using vector similarity, then filter by Calvin as author and topics related to predestination",
    "recommended_filters": {{
        "authors": ["John Calvin"],
        "topics": ["Topic/Predestination", "Topic/Election"],
        "concepts": ["Concept/Divine Sovereignty", "Concept/Election"]
    }},
    "reasoning": "The query specifically asks about Calvin's views, so I'm filtering by Calvin as author and topics/concepts related to predestination."
}}

For "What are the logical arguments for the Trinity?":
{{
    "query_type": "doctrinal",
    "theological_concepts": ["trinity", "three persons", "one God"],
    "search_strategy": "Search for chunks about the Trinity using vector similarity, then filter by Logical/Claim function to find argumentative content",
    "recommended_filters": {{
        "function": ["Logical/Claim", "Logical/Argument"],
        "topics": ["Topic/Trinity", "Topic/God"],
        "concepts": ["Concept/God", "Concept/Trinity"]
    }},
    "reasoning": "The query asks for logical arguments, so I'm prioritizing Logical/Claim function metadata to find sources with argumentative content about the Trinity."
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
                if filter_type in chunk_metadata:
                    chunk_values = chunk_metadata[filter_type]
                    if isinstance(chunk_values, list):
                        for chunk_val in chunk_values:
                            for filter_val in filter_values:
                                if filter_val.lower() in chunk_val.lower():
                                    filter_match_score += 1
                                    break
        else:
            # If no specific filters, give all chunks a base filter score
            filter_match_score = 0.5
        
        # Calculate combined score
        # Weight exact matches heavily, then vector similarity, then filters
        combined_score = (exact_match_score * 2.0) + (vector_similarity_score * 1.5) + (filter_match_score * 0.5)
        
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
        structure_path = chunk.get("metadata", {}).get("structure_path", ["Unknown"])
        structure = structure_path[0] if structure_path else "Unknown"
        
        text = chunk.get("text", "")
        
        chunks_text += f"""
[Source {i}]
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
            "source": "Source Name",
            "author": "Author Name", 
            "location": "Structure Path",
            "relevance": "Brief explanation of why this source was relevant"
        }}
    ],
    "reasoning_transparency": "Explanation of the search strategy and filter choices made"
}}

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
        
        # Get available source numbers
        available_numbers = [str(source.get("number", "")) for source in sources_used]
        
        # Find all citations in the summary
        import re
        citations_in_summary = re.findall(r'\[(\d+)\]', summary)
        
        # Check for mismatched citations and fix them
        fixed_summary = summary
        for i, citation in enumerate(citations_in_summary):
            if citation not in available_numbers:
                # Map to the next available source number
                if i < len(available_numbers):
                    new_citation = available_numbers[i]
                    fixed_summary = fixed_summary.replace(f'[{citation}]', f'[{new_citation}]')
        
        # Update the summary with fixed citations
        result["summary"] = fixed_summary
        
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
        app.run(debug=True, port=5000)
    else:
        print("Failed to load dataset")
