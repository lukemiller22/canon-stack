#!/usr/bin/env python3
"""
Discourse Graph Framework - Web Demo
Browser-based comparison of traditional RAG vs enhanced retrieval
"""

from flask import Flask, render_template, request, jsonify
import json
import sys
from pathlib import Path

# Import demo logic
sys.path.insert(0, str(Path(__file__).parent))
from demo import TraditionalRAG, DiscourseGraphRAG, QueryIntent

app = Flask(__name__)

# Load sample data
data_path = Path(__file__).parent / 'sample_data.json'
with open(data_path) as f:
    data = json.load(f)

chunks = data['chunks']
trad_rag = TraditionalRAG(chunks)
discourse_rag = DiscourseGraphRAG(chunks)


@app.route('/')
def index():
    """Serve the main demo page"""
    return render_template('index.html', chunks=chunks)


@app.route('/api/search', methods=['POST'])
def search():
    """Compare both retrieval methods"""
    data = request.get_json()
    query = data.get('query', '')
    k = data.get('k', 3)

    if not query:
        return jsonify({'error': 'No query provided'}), 400

    # Traditional RAG
    trad_results = trad_rag.search(query, k=k)

    # Discourse Graph RAG
    discourse_data = discourse_rag.search(query, k=k)

    return jsonify({
        'query': query,
        'traditional': {
            'results': [
                {
                    'rank': i + 1,
                    'score': r['score'],
                    'chunk': {
                        'id': r['chunk']['id'],
                        'text': r['chunk']['text'],
                        'source': r['chunk']['source'],
                        'author': r['chunk']['author'],
                    },
                    'reason': r['reason']
                }
                for i, r in enumerate(trad_results)
            ]
        },
        'discourse': {
            'intents': [
                {'intent': intent.value, 'confidence': conf}
                for intent, conf in discourse_data['intents']
            ],
            'preferred_elements': discourse_data['preferred_elements'],
            'results': [
                {
                    'rank': i + 1,
                    'score': r['score'],
                    'semantic_score': r['semantic_score'],
                    'discourse_score': r['discourse_score'],
                    'intent_score': r['intent_score'],
                    'matched_elements': r.get('matched_elements', []),
                    'chunk': {
                        'id': r['chunk']['id'],
                        'text': r['chunk']['text'],
                        'source': r['chunk']['source'],
                        'author': r['chunk']['author'],
                        'metadata': r['chunk']['metadata']
                    },
                    'reason': r['reason']
                }
                for i, r in enumerate(discourse_data['results'])
            ]
        }
    })


@app.route('/api/chunks')
def get_chunks():
    """Get all available chunks"""
    return jsonify({
        'chunks': [
            {
                'id': c['id'],
                'source': c['source'],
                'author': c['author'],
                'text': c['text'][:200] + '...'
            }
            for c in chunks
        ]
    })


if __name__ == '__main__':
    print("="*80)
    print("DISCOURSE GRAPH FRAMEWORK - WEB DEMO".center(80))
    print("="*80)
    print(f"\n📚 Loaded {len(chunks)} sample chunks")
    print("\n🌐 Starting web server...")
    print("\n✅ Open in browser: http://localhost:5002")
    print("\n" + "="*80 + "\n")

    app.run(debug=True, port=5002, host='127.0.0.1')
