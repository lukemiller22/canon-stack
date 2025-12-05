#!/usr/bin/env python3
"""
Discourse Graph Framework - Interactive Demo
Compares traditional RAG vs enhanced discourse-aware retrieval
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Tuple
from dataclasses import dataclass
from enum import Enum

# Add parent directory to path to import discourse_graph_retrieval
sys.path.insert(0, str(Path(__file__).parent.parent))

# Simple in-memory implementation for demo (not using ChromaDB)
class QueryIntent(Enum):
    DEFINITIONAL = "definitional"
    PROCEDURAL = "procedural"
    CAUSAL = "causal"
    COMPARATIVE = "comparative"
    EVALUATIVE = "evaluative"
    HISTORICAL = "historical"
    PREDICTIVE = "predictive"
    DIAGNOSTIC = "diagnostic"
    PRESCRIPTIVE = "prescriptive"
    INTERPRETIVE = "interpretive"
    EXEMPLARY = "exemplary"
    SYNTHETIC = "synthetic"


class SimpleIntentClassifier:
    """Simple intent classifier for demo"""

    INTENT_KEYWORDS = {
        QueryIntent.DEFINITIONAL: ["what is", "define", "meaning of", "definition"],
        QueryIntent.PROCEDURAL: ["how to", "how do I", "steps", "method"],
        QueryIntent.CAUSAL: ["why", "cause", "reason", "because"],
        QueryIntent.COMPARATIVE: ["compare", "difference", "versus", "vs"],
        QueryIntent.EVALUATIVE: ["is it good", "should I", "evaluate"],
        QueryIntent.DIAGNOSTIC: ["problem", "issue", "wrong"],
        QueryIntent.PRESCRIPTIVE: ["should", "must", "recommend"],
        QueryIntent.INTERPRETIVE: ["means", "interpret", "significance"],
        QueryIntent.EXEMPLARY: ["example", "instance", "case"],
        QueryIntent.SYNTHETIC: ["overview", "summary", "big picture"]
    }

    def classify(self, query: str) -> List[Tuple[QueryIntent, float]]:
        """Classify query into intents"""
        query_lower = query.lower()
        scores = {}

        for intent, keywords in self.INTENT_KEYWORDS.items():
            for keyword in keywords:
                if keyword in query_lower:
                    scores[intent] = scores.get(intent, 0) + 1.0

        if not scores:
            return []

        total = sum(scores.values())
        scores = {k: v/total for k, v in scores.items()}

        return sorted(scores.items(), key=lambda x: x[1], reverse=True)


class TraditionalRAG:
    """Traditional semantic-only RAG retrieval"""

    def __init__(self, chunks: List[Dict]):
        self.chunks = chunks

    def search(self, query: str, k: int = 3) -> List[Dict]:
        """Simple keyword-based search (simulating semantic similarity)"""
        query_lower = query.lower()
        query_words = set(query_lower.split())

        results = []
        for chunk in self.chunks:
            text_lower = chunk['text'].lower()
            text_words = set(text_lower.split())

            # Simple overlap score
            overlap = len(query_words & text_words)
            score = overlap / len(query_words) if query_words else 0

            results.append({
                'chunk': chunk,
                'score': score,
                'reason': 'Semantic similarity (keyword overlap)'
            })

        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:k]


class DiscourseGraphRAG:
    """Enhanced discourse-aware retrieval"""

    def __init__(self, chunks: List[Dict]):
        self.chunks = chunks
        self.intent_classifier = SimpleIntentClassifier()

        # Map intents to preferred discourse elements
        self.intent_discourse_map = {
            QueryIntent.DEFINITIONAL: [
                "Semantic/Definition", "Semantic/Description", "Semantic/Concept"
            ],
            QueryIntent.EVALUATIVE: [
                "Logical/Claim", "Rhetorical/Thesis", "Computational/Evaluation"
            ],
            QueryIntent.COMPARATIVE: [
                "Computational/Comparison", "Rhetorical/Antithesis"
            ],
            QueryIntent.DIAGNOSTIC: [
                "Computational/Diagnosis", "Practical/Problem"
            ],
            QueryIntent.PRESCRIPTIVE: [
                "Practical/Strategy", "Practical/Solution"
            ]
        }

    def search(self, query: str, k: int = 3) -> Dict:
        """Multi-stage discourse-aware search"""

        # Stage 1: Intent Classification
        intents = self.intent_classifier.classify(query)

        # Stage 2: Get preferred discourse elements
        preferred_elements = []
        if intents:
            top_intent = intents[0][0]
            preferred_elements = self.intent_discourse_map.get(top_intent, [])

        # Stage 3: Semantic search with discourse scoring
        query_lower = query.lower()
        query_words = set(query_lower.split())

        results = []
        for chunk in self.chunks:
            text_lower = chunk['text'].lower()
            text_words = set(text_lower.split())

            # Semantic score
            overlap = len(query_words & text_words)
            semantic_score = overlap / len(query_words) if query_words else 0

            # Discourse score
            chunk_elements = chunk['metadata'].get('discourse_elements', [])
            chunk_comp = chunk['metadata'].get('computational_elements', [])
            chunk_rhet = chunk['metadata'].get('rhetorical_elements', [])
            all_elements = chunk_elements + chunk_comp + chunk_rhet

            discourse_matches = sum(1 for elem in all_elements if elem in preferred_elements)
            discourse_score = discourse_matches / len(preferred_elements) if preferred_elements else 0

            # Query intent score
            chunk_intents = chunk['metadata'].get('query_intents', [])
            intent_match = any(intent.value in [i.lower() for i in chunk_intents] for intent, _ in intents)
            intent_score = 1.0 if intent_match else 0.0

            # Combined score (weighted)
            combined_score = (
                0.4 * semantic_score +
                0.4 * discourse_score +
                0.2 * intent_score
            )

            results.append({
                'chunk': chunk,
                'score': combined_score,
                'semantic_score': semantic_score,
                'discourse_score': discourse_score,
                'intent_score': intent_score,
                'matched_elements': [e for e in all_elements if e in preferred_elements],
                'reason': f'Intent: {intents[0][0].value if intents else "none"}, Discourse: {discourse_matches} matches'
            })

        results.sort(key=lambda x: x['score'], reverse=True)

        return {
            'intents': intents,
            'preferred_elements': preferred_elements,
            'results': results[:k]
        }


def print_header(text: str):
    """Print formatted header"""
    print(f"\n{'='*80}")
    print(f"{text:^80}")
    print('='*80)


def print_result(result: Dict, rank: int, mode: str):
    """Print a single result"""
    chunk = result['chunk']

    print(f"\n{'-'*80}")
    print(f"RANK #{rank} | Score: {result['score']:.3f}")
    print('-'*80)

    print(f"Source: {chunk['source']} by {chunk['author']}")
    print(f"\nText: {chunk['text'][:300]}...")

    if mode == 'discourse':
        print(f"\n📊 Scoring Breakdown:")
        print(f"  • Semantic: {result['semantic_score']:.3f}")
        print(f"  • Discourse: {result['discourse_score']:.3f}")
        print(f"  • Intent: {result['intent_score']:.3f}")
        if result.get('matched_elements'):
            print(f"  • Matched Elements: {', '.join(result['matched_elements'][:3])}")

    print(f"\n💡 Reason: {result['reason']}")


def run_comparison(query: str, chunks: List[Dict]):
    """Run side-by-side comparison"""

    print_header(f"QUERY: {query}")

    # Traditional RAG
    print_header("METHOD 1: TRADITIONAL RAG (Semantic Only)")
    trad_rag = TraditionalRAG(chunks)
    trad_results = trad_rag.search(query, k=3)

    for i, result in enumerate(trad_results, 1):
        print_result(result, i, 'traditional')

    # Discourse Graph RAG
    print_header("METHOD 2: DISCOURSE GRAPH RAG (Enhanced)")
    discourse_rag = DiscourseGraphRAG(chunks)
    discourse_data = discourse_rag.search(query, k=3)

    print(f"\n🎯 Detected Intent: ", end="")
    if discourse_data['intents']:
        intent, conf = discourse_data['intents'][0]
        print(f"{intent.value} ({conf:.0%} confidence)")
    else:
        print("None detected")

    print(f"📝 Prioritizing Discourse Elements: {', '.join(discourse_data['preferred_elements'][:3])}")

    for i, result in enumerate(discourse_data['results'], 1):
        print_result(result, i, 'discourse')

    # Summary
    print_header("COMPARISON SUMMARY")
    print("\n✅ Traditional RAG:")
    print("   • Fast, simple keyword/semantic matching")
    print("   • No understanding of query intent or discourse structure")
    print("   • May miss relevant content with different vocabulary")

    print("\n🚀 Discourse Graph RAG:")
    print("   • Intent-aware: understands what KIND of answer you need")
    print("   • Discourse-aware: prioritizes chunks with relevant patterns")
    print("   • Better precision: finds answers that match your information need")
    print("   • Explainable: shows WHY each result was selected")


def interactive_demo():
    """Run interactive demo"""
    # Load sample data
    data_path = Path(__file__).parent / 'sample_data.json'
    with open(data_path) as f:
        data = json.load(f)

    chunks = data['chunks']

    print("="*80)
    print("DISCOURSE GRAPH FRAMEWORK - INTERACTIVE DEMO".center(80))
    print("="*80)
    print("\nThis demo compares traditional RAG vs enhanced discourse-aware retrieval.")
    print(f"\n📚 Loaded {len(chunks)} sample chunks from:")
    for chunk in chunks:
        print(f"   • {chunk['source']} by {chunk['author']}")

    print("\n" + "="*80)
    print("\nTry these example queries:")
    print("  1. What is faith?")
    print("  2. What is the problem with modern humility?")
    print("  3. How should Christians engage with culture?")
    print("  4. Compare different views on Jesus' identity")
    print("\nOr enter your own query (type 'quit' to exit)")

    while True:
        print("\n" + "="*80)
        query = input("\n🔍 Enter your query: ").strip()

        if query.lower() in ['quit', 'exit', 'q']:
            print("\n👋 Thanks for trying the Discourse Graph Framework demo!")
            break

        if not query:
            continue

        run_comparison(query, chunks)

        print("\n" + "="*80)
        cont = input("\n❓ Try another query? (y/n): ").strip().lower()
        if cont != 'y':
            print("\n👋 Thanks for trying the Discourse Graph Framework demo!")
            break


if __name__ == '__main__':
    try:
        interactive_demo()
    except KeyboardInterrupt:
        print("\n\n👋 Demo interrupted. Thanks for trying it!")
        sys.exit(0)
