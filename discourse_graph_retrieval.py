"""
Discourse Graph Framework - Multi-Stage Retrieval System
Extends canon-stack with graph-based, discourse-aware retrieval

Author: Extended by Claude from Luke Miller's canon-stack
Date: 2025-11-27
"""

import chromadb
from dataclasses import dataclass, field
from typing import List, Dict, Set, Tuple, Optional
from enum import Enum
import numpy as np
from collections import defaultdict


class QueryIntent(Enum):
    """Types of user query intents"""
    DEFINITIONAL = "definitional"  # What is X?
    PROCEDURAL = "procedural"  # How do I do X?
    CAUSAL = "causal"  # Why does X happen?
    COMPARATIVE = "comparative"  # How does X compare to Y?
    EVALUATIVE = "evaluative"  # Is X good/true?
    HISTORICAL = "historical"  # What happened?
    PREDICTIVE = "predictive"  # What will happen?
    DIAGNOSTIC = "diagnostic"  # What's wrong?
    PRESCRIPTIVE = "prescriptive"  # What should be done?
    INTERPRETIVE = "interpretive"  # What does X mean?
    EXEMPLARY = "exemplary"  # Give me an example
    SYNTHETIC = "synthetic"  # How does it fit together?


class ConfidenceLevel(Enum):
    """Confidence levels for metadata"""
    DEFINITIVE = 1.0
    PROBABLE = 0.8
    POSSIBLE = 0.5
    SPECULATIVE = 0.2


@dataclass
class DiscourseElement:
    """Enhanced discourse element with confidence"""
    category: str  # e.g., "Logical", "Computational"
    element: str  # e.g., "Claim", "Algorithm"
    content: str  # Description or quote
    confidence: ConfidenceLevel = ConfidenceLevel.PROBABLE


@dataclass
class DiscourseRelationship:
    """Typed relationship between chunks"""
    relation_type: str  # supports, contradicts, elaborates, etc.
    target_chunk_id: str
    weight: float = 1.0  # Strength of relationship
    metadata: Dict = field(default_factory=dict)


@dataclass
class EnhancedMetadata:
    """Complete metadata for a text chunk"""
    # Original framework
    concepts: List[str]
    topics: List[str]
    terms: List[str]
    discourse_elements: List[DiscourseElement]
    scripture_refs: List[str] = field(default_factory=list)
    named_entities: List[str] = field(default_factory=list)
    structure_path: str = ""

    # Extended framework
    query_intents: List[QueryIntent] = field(default_factory=list)
    relationships: List[DiscourseRelationship] = field(default_factory=list)

    # Faceted classification
    facets: Dict[str, List[str]] = field(default_factory=dict)
    # facets = {
    #     "traditions": ["Reformed", "Catholic"],
    #     "period": ["Reformation"],
    #     "level": ["Academic"]
    # }


class IntentClassifier:
    """Classifies user queries into intent categories"""

    # Intent keywords (in practice, use a trained classifier)
    INTENT_KEYWORDS = {
        QueryIntent.DEFINITIONAL: ["what is", "define", "meaning of", "definition"],
        QueryIntent.PROCEDURAL: ["how to", "how do I", "steps", "method", "process"],
        QueryIntent.CAUSAL: ["why", "cause", "reason", "because", "leads to"],
        QueryIntent.COMPARATIVE: ["compare", "difference", "versus", "vs", "contrast"],
        QueryIntent.EVALUATIVE: ["is it good", "should I", "evaluate", "assess"],
        QueryIntent.HISTORICAL: ["when", "history", "timeline", "what happened"],
        QueryIntent.PREDICTIVE: ["will", "predict", "forecast", "future", "consequence"],
        QueryIntent.DIAGNOSTIC: ["problem", "issue", "wrong", "troubleshoot"],
        QueryIntent.PRESCRIPTIVE: ["should", "must", "recommend", "advice"],
        QueryIntent.INTERPRETIVE: ["means", "interpret", "significance", "understand"],
        QueryIntent.EXEMPLARY: ["example", "instance", "case", "illustration"],
        QueryIntent.SYNTHETIC: ["overview", "summary", "big picture", "synthesize"]
    }

    def classify(self, query: str) -> List[Tuple[QueryIntent, float]]:
        """
        Classify query into one or more intents with confidence scores

        Returns:
            List of (intent, confidence) tuples, sorted by confidence
        """
        query_lower = query.lower()
        scores = defaultdict(float)

        # Simple keyword matching (replace with ML model in production)
        for intent, keywords in self.INTENT_KEYWORDS.items():
            for keyword in keywords:
                if keyword in query_lower:
                    scores[intent] += 1.0

        # Normalize scores
        if scores:
            total = sum(scores.values())
            scores = {k: v/total for k, v in scores.items()}

        # Return sorted by confidence
        return sorted(scores.items(), key=lambda x: x[1], reverse=True)


class DiscourseGraphRetriever:
    """Multi-stage retrieval using discourse structure and graph relationships"""

    def __init__(self, chroma_client: chromadb.Client, collection_name: str = "theological_texts"):
        self.client = chroma_client
        self.collection = chroma_client.get_collection(collection_name)
        self.intent_classifier = IntentClassifier()

        # Discourse element priorities for each intent
        self.intent_discourse_map = {
            QueryIntent.DEFINITIONAL: [
                "Semantic/Definition", "Semantic/Description", "Semantic/Concept"
            ],
            QueryIntent.PROCEDURAL: [
                "Practical/Process", "Computational/Algorithm", "Practical/Task"
            ],
            QueryIntent.CAUSAL: [
                "Logical/Evidence", "Logical/Warrant", "Narrative/Event"
            ],
            QueryIntent.COMPARATIVE: [
                "Computational/Comparison", "Semantic/Relationship", "Logical/Claim"
            ],
            QueryIntent.EVALUATIVE: [
                "Computational/Evaluation", "Personal/Taste", "Logical/Claim"
            ],
            QueryIntent.HISTORICAL: [
                "Narrative/Event", "Narrative/Time", "Narrative/Person"
            ],
            QueryIntent.PREDICTIVE: [
                "Computational/Prediction", "Logical/Inference", "Practical/Theory"
            ],
            QueryIntent.DIAGNOSTIC: [
                "Computational/Diagnosis", "Practical/Problem", "Logical/Error"
            ],
            QueryIntent.PRESCRIPTIVE: [
                "Practical/Imperative", "Practical/Solution", "Practical/Principle"
            ],
            QueryIntent.INTERPRETIVE: [
                "Reference/Commentary", "Symbolic/Metaphor", "Semantic/Context"
            ],
            QueryIntent.EXEMPLARY: [
                "Semantic/Example", "Narrative/Story", "Symbolic/Illustration"
            ],
            QueryIntent.SYNTHETIC: [
                "Reference/Synthesis", "Reference/Summary", "Practical/System"
            ]
        }

    def retrieve(
        self,
        query: str,
        k: int = 10,
        use_graph_expansion: bool = True,
        min_confidence: float = 0.5
    ) -> List[Dict]:
        """
        Multi-stage discourse-aware retrieval

        Args:
            query: User query string
            k: Number of results to return
            use_graph_expansion: Whether to expand via graph relationships
            min_confidence: Minimum confidence for metadata filtering

        Returns:
            List of chunk results with discourse context
        """

        # Stage 1: Intent Classification
        intents = self.intent_classifier.classify(query)
        print(f"🎯 Detected intents: {[(i.value, f'{c:.2f}') for i, c in intents[:2]]}")

        # Stage 2: Concept Extraction (simplified - in practice use NER)
        concepts = self._extract_concepts(query)
        print(f"📚 Relevant concepts: {concepts}")

        # Stage 3: Discourse-Aware Filtering
        # Get discourse elements that match the query intent
        preferred_elements = []
        for intent, confidence in intents:
            if intent in self.intent_discourse_map:
                preferred_elements.extend(self.intent_discourse_map[intent])

        print(f"🔍 Prioritizing discourse elements: {preferred_elements[:3]}...")

        # Stage 4: Initial Semantic Retrieval
        # Query ChromaDB with concept and discourse filtering
        where_filter = self._build_where_filter(concepts, preferred_elements, min_confidence)

        results = self.collection.query(
            query_texts=[query],
            n_results=k * 2,  # Get more initially for filtering
            where=where_filter if where_filter else None
        )

        # Stage 5: Graph Expansion (optional)
        if use_graph_expansion and results['ids']:
            results = self._expand_via_graph(results, preferred_elements)

        # Stage 6: Re-rank by discourse structure
        ranked_results = self._rerank_by_discourse(results, intents, preferred_elements)

        return ranked_results[:k]

    def _extract_concepts(self, query: str) -> List[str]:
        """Extract theological concepts from query (simplified)"""
        # In production, use NER or concept extraction model
        # For now, simple keyword matching against concept index
        concept_keywords = {
            "god": "God",
            "faith": "Faith",
            "reason": "Reason",
            "scripture": "Scripture",
            "authority": "Authority",
            "salvation": "Salvation",
            "sin": "Sin",
            "grace": "Grace",
            "church": "Church",
            "truth": "Truth"
        }

        query_lower = query.lower()
        concepts = []
        for keyword, concept in concept_keywords.items():
            if keyword in query_lower:
                concepts.append(concept)

        return concepts or []

    def _build_where_filter(
        self,
        concepts: List[str],
        discourse_elements: List[str],
        min_confidence: float
    ) -> Optional[Dict]:
        """Build ChromaDB where filter for metadata"""
        # This assumes metadata is stored in ChromaDB metadata field
        # Adjust based on actual schema
        filters = []

        if concepts:
            filters.append({"concepts": {"$in": concepts}})

        if discourse_elements:
            filters.append({"discourse_elements": {"$contains": discourse_elements[0]}})

        if filters:
            return {"$and": filters} if len(filters) > 1 else filters[0]

        return None

    def _expand_via_graph(
        self,
        initial_results: Dict,
        preferred_elements: List[str]
    ) -> Dict:
        """Expand results by following graph relationships"""
        # Get chunk IDs from initial results
        chunk_ids = initial_results['ids'][0] if initial_results['ids'] else []

        # For each chunk, find related chunks via relationships
        expanded_ids = set(chunk_ids)

        for chunk_id in chunk_ids[:5]:  # Only expand top 5 to avoid explosion
            # Query metadata to find relationships
            # This is simplified - in practice, maintain a separate graph database
            related = self._get_related_chunks(
                chunk_id,
                relation_types=["supports", "elaborates", "exemplifies"]
            )
            expanded_ids.update(related)

        # Re-query with expanded set
        if len(expanded_ids) > len(chunk_ids):
            print(f"📈 Expanded from {len(chunk_ids)} to {len(expanded_ids)} chunks via graph")

        return initial_results  # Placeholder - implement full expansion

    def _get_related_chunks(
        self,
        chunk_id: str,
        relation_types: List[str]
    ) -> List[str]:
        """Get chunks related via specific relationship types"""
        # Placeholder - implement graph traversal
        return []

    def _rerank_by_discourse(
        self,
        results: Dict,
        intents: List[Tuple[QueryIntent, float]],
        preferred_elements: List[str]
    ) -> List[Dict]:
        """Re-rank results based on discourse structure match"""
        if not results['ids']:
            return []

        chunk_ids = results['ids'][0]
        documents = results['documents'][0]
        metadatas = results['metadatas'][0]
        distances = results['distances'][0]

        ranked = []
        for i, chunk_id in enumerate(chunk_ids):
            # Calculate discourse score
            discourse_score = self._calculate_discourse_score(
                metadatas[i],
                preferred_elements
            )

            # Combine semantic similarity (inverse of distance) with discourse score
            semantic_score = 1.0 / (1.0 + distances[i])
            combined_score = 0.6 * semantic_score + 0.4 * discourse_score

            ranked.append({
                'chunk_id': chunk_id,
                'content': documents[i],
                'metadata': metadatas[i],
                'semantic_score': semantic_score,
                'discourse_score': discourse_score,
                'combined_score': combined_score
            })

        # Sort by combined score
        ranked.sort(key=lambda x: x['combined_score'], reverse=True)

        return ranked

    def _calculate_discourse_score(
        self,
        metadata: Dict,
        preferred_elements: List[str]
    ) -> float:
        """Calculate how well chunk's discourse elements match query intent"""
        if 'discourse_elements' not in metadata:
            return 0.0

        chunk_elements = metadata.get('discourse_elements', [])
        if isinstance(chunk_elements, str):
            chunk_elements = [chunk_elements]

        # Count matches with preferred elements
        matches = sum(1 for elem in chunk_elements if elem in preferred_elements)

        # Normalize by number of preferred elements
        score = matches / len(preferred_elements) if preferred_elements else 0.0

        return score


class DiscourseGraphBuilder:
    """Builds discourse graph from annotated chunks"""

    def __init__(self):
        self.graph = defaultdict(list)  # adjacency list
        self.chunks = {}  # chunk_id -> metadata

    def add_chunk(self, chunk_id: str, metadata: EnhancedMetadata):
        """Add chunk with metadata to graph"""
        self.chunks[chunk_id] = metadata

        # Add relationships as edges
        for rel in metadata.relationships:
            self.graph[chunk_id].append({
                'target': rel.target_chunk_id,
                'type': rel.relation_type,
                'weight': rel.weight
            })

    def find_supporting_evidence(self, chunk_id: str, max_depth: int = 2) -> List[str]:
        """Find all chunks that support this chunk"""
        return self._traverse(chunk_id, "supports", max_depth)

    def find_contradictions(self, chunk_id: str, max_depth: int = 2) -> List[str]:
        """Find all chunks that contradict this chunk"""
        return self._traverse(chunk_id, "contradicts", max_depth)

    def find_elaborations(self, chunk_id: str, max_depth: int = 1) -> List[str]:
        """Find all chunks that elaborate on this chunk"""
        return self._traverse(chunk_id, "elaborates", max_depth)

    def _traverse(
        self,
        start_id: str,
        relation_type: str,
        max_depth: int
    ) -> List[str]:
        """BFS traversal following specific relationship type"""
        visited = set()
        queue = [(start_id, 0)]
        results = []

        while queue:
            current_id, depth = queue.pop(0)

            if current_id in visited or depth > max_depth:
                continue

            visited.add(current_id)

            # Get neighbors with matching relationship type
            for edge in self.graph.get(current_id, []):
                if edge['type'] == relation_type:
                    target = edge['target']
                    if target not in visited:
                        results.append(target)
                        queue.append((target, depth + 1))

        return results


# Example usage
if __name__ == "__main__":
    # Initialize ChromaDB client
    client = chromadb.Client()

    # Create retriever
    retriever = DiscourseGraphRetriever(client)

    # Example query
    query = "What are the main arguments for and against sola scriptura?"

    # Retrieve with discourse awareness
    results = retriever.retrieve(query, k=5, use_graph_expansion=True)

    # Display results
    print("\n" + "="*80)
    print("RESULTS")
    print("="*80 + "\n")

    for i, result in enumerate(results, 1):
        print(f"{i}. Score: {result['combined_score']:.3f}")
        print(f"   Semantic: {result['semantic_score']:.3f} | Discourse: {result['discourse_score']:.3f}")
        print(f"   Content: {result['content'][:200]}...")
        print(f"   Metadata: {result['metadata']}")
        print()
