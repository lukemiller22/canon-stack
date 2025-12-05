# Implementation Guide: Discourse Graph Framework
## Integrating Enhanced Retrieval into Canon-Stack

---

## Phase 1: Quick Start (Week 1)

### Goal: Add basic enhanced elements without breaking existing system

### Step 1: Extend Annotation Prompt

Add new sections to your existing annotation prompt:

```markdown
## NEW: Computational Elements (Optional)
If the chunk contains computational operations, tag with:
- [[Computational/Classification]] - Categorization schemes
- [[Computational/Comparison]] - Explicit contrasts
- [[Computational/Algorithm]] - Step-by-step procedures
... (see Index: Discourse-Elements-Extended.md)

## NEW: Rhetorical Elements (Optional)
If the chunk makes argumentative moves, tag with:
- [[Rhetorical/Thesis]] - Main argument
- [[Rhetorical/Refutation]] - Rebuttal
... (see Index: Discourse-Elements-Extended.md)

## NEW: Query Intent Tags (Optional)
Tag what kind of questions this chunk answers:
- [[Query/Definitional]] - "What is X?"
- [[Query/Comparative]] - "How does X compare to Y?"
... (see Index: Discourse-Elements-Extended.md)
```

**Key:** Start with just these 3 new categories (39 new elements total).

### Step 2: Test on Small Sample

1. Choose 10 diverse chunks from your existing corpus
2. Manually annotate with enhanced elements
3. Store in `theological_processing/06_enhanced/` directory
4. Verify the annotations make sense

### Step 3: Update Storage Schema

Modify your ChromaDB metadata schema:

```python
# enhanced_app.py
def store_chunk_enhanced(chunk_text, metadata):
    """Store chunk with enhanced metadata"""

    # Original metadata (preserve)
    base_metadata = {
        "concepts": metadata.get("concepts", []),
        "topics": metadata.get("topics", []),
        "terms": metadata.get("terms", []),
        "discourse_elements": metadata.get("discourse_elements", []),
    }

    # NEW: Enhanced metadata
    enhanced_metadata = base_metadata.copy()

    # Add new element categories
    enhanced_metadata["computational_elements"] = metadata.get("computational_elements", [])
    enhanced_metadata["rhetorical_elements"] = metadata.get("rhetorical_elements", [])
    enhanced_metadata["query_intents"] = metadata.get("query_intents", [])

    # Add to ChromaDB
    collection.add(
        documents=[chunk_text],
        metadatas=[enhanced_metadata],
        ids=[f"chunk_{uuid.uuid4()}"]
    )
```

**Backward compatibility:** Old chunks still work, new chunks have extra metadata.

---

## Phase 2: Add Graph Relationships (Week 2)

### Goal: Build discourse graph with chunk relationships

### Step 1: Define Relationship Schema

Create a relationships table/collection:

```python
# discourse_graph.py
import sqlite3

# Create graph database (simple SQLite approach)
conn = sqlite3.connect('discourse_graph.db')
cursor = conn.cursor()

cursor.execute('''
    CREATE TABLE IF NOT EXISTS relationships (
        source_chunk_id TEXT,
        target_chunk_id TEXT,
        relation_type TEXT,
        weight REAL,
        metadata TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (source_chunk_id, target_chunk_id, relation_type)
    )
''')
```

### Step 2: Identify Relationships

Start with easiest relationships:

1. **Structure-based:**
   - Chunks in same section: `related_to`
   - Next chunk in sequence: `follows`

2. **Citation-based:**
   - Chunk cites another: `quotes`
   - Chunk references concept defined elsewhere: `refers_to`

3. **Manual annotation** (later automate):
   - Expert adds `supports`, `contradicts`, `refutes`

### Step 3: Graph Traversal

```python
def get_supporting_evidence(chunk_id, max_depth=2):
    """Find all chunks that support this one"""
    query = """
        WITH RECURSIVE support_chain AS (
            SELECT target_chunk_id, 1 as depth
            FROM relationships
            WHERE source_chunk_id = ? AND relation_type = 'supports'

            UNION ALL

            SELECT r.target_chunk_id, sc.depth + 1
            FROM relationships r
            JOIN support_chain sc ON r.source_chunk_id = sc.target_chunk_id
            WHERE r.relation_type = 'supports' AND sc.depth < ?
        )
        SELECT DISTINCT target_chunk_id FROM support_chain
    """
    cursor.execute(query, (chunk_id, max_depth))
    return [row[0] for row in cursor.fetchall()]
```

---

## Phase 3: Intent-Aware Retrieval (Week 3)

### Goal: Use query intent to improve retrieval

### Step 1: Simple Intent Classifier

```python
from discourse_graph_retrieval import IntentClassifier

classifier = IntentClassifier()

# User query
query = "What are the main arguments for God's existence?"

# Classify intent
intents = classifier.classify(query)
# Returns: [(QueryIntent.EVALUATIVE, 0.6), (QueryIntent.COMPARATIVE, 0.3)]
```

### Step 2: Intent-Driven Filtering

```python
# Map intent to preferred discourse elements
INTENT_ELEMENTS = {
    QueryIntent.DEFINITIONAL: ["Semantic/Definition", "Semantic/Description"],
    QueryIntent.EVALUATIVE: ["Logical/Claim", "Logical/Evidence", "Rhetorical/Thesis"],
    # ... etc
}

def retrieve_with_intent(query, intents):
    """Retrieve chunks matching query intent"""

    # Get preferred elements for top intent
    top_intent, confidence = intents[0]
    preferred_elements = INTENT_ELEMENTS.get(top_intent, [])

    # Build filter for ChromaDB
    where_filter = {
        "$or": [
            {"discourse_elements": {"$contains": elem}}
            for elem in preferred_elements
        ]
    }

    # Query with filter
    results = collection.query(
        query_texts=[query],
        n_results=10,
        where=where_filter
    )

    return results
```

### Step 3: Test & Refine

Create test queries with known expected results:

```python
TEST_CASES = [
    {
        "query": "What is grace?",
        "expected_intent": QueryIntent.DEFINITIONAL,
        "expected_elements": ["Semantic/Definition"],
        "expected_chunks": ["lewis_mc_grace_definition"]
    },
    {
        "query": "How does Lewis argue for theism?",
        "expected_intent": QueryIntent.EVALUATIVE,
        "expected_elements": ["Rhetorical/Thesis", "Logical/Claim"],
        "expected_chunks": ["lewis_mc_moral_argument"]
    }
]

# Run tests
for test in TEST_CASES:
    results = retrieve_with_intent(test["query"])
    assert test["expected_chunks"][0] in [r['id'] for r in results[:5]]
```

---

## Phase 4: Full Discourse Graph Retrieval (Week 4)

### Goal: Multi-stage retrieval with graph expansion

### Step 1: Integrate Full Pipeline

```python
from discourse_graph_retrieval import DiscourseGraphRetriever

retriever = DiscourseGraphRetriever(chroma_client)

# Simple usage
results = retriever.retrieve(
    query="What are arguments for and against infant baptism?",
    k=10,
    use_graph_expansion=True
)

# Results include discourse context
for result in results:
    print(f"Score: {result['combined_score']}")
    print(f"  Semantic: {result['semantic_score']}")
    print(f"  Discourse: {result['discourse_score']}")
    print(f"  Content: {result['content'][:100]}...")
```

### Step 2: Build Answer with Structure

```python
def build_structured_answer(query, results):
    """Construct answer using discourse structure"""

    # Group results by discourse pattern
    definitions = [r for r in results if "Semantic/Definition" in r['metadata'].get('discourse_elements', [])]
    claims = [r for r in results if "Logical/Claim" in r['metadata'].get('discourse_elements', [])]
    evidence = [r for r in results if "Logical/Evidence" in r['metadata'].get('discourse_elements', [])]

    # Build structured response
    answer = []

    if definitions:
        answer.append("## Definition")
        answer.extend([d['content'] for d in definitions[:2]])

    if claims:
        answer.append("\n## Main Arguments")
        answer.extend([f"- {c['content'][:200]}..." for c in claims[:5]])

    if evidence:
        answer.append("\n## Supporting Evidence")
        answer.extend([f"- {e['content'][:200]}..." for e in evidence[:3]])

    return "\n".join(answer)
```

### Step 3: Add Confidence Weighting

```python
def retrieve_with_confidence(query, min_confidence=0.7):
    """Only return high-confidence metadata"""

    results = retriever.retrieve(query)

    # Filter by confidence
    filtered = []
    for result in results:
        # Check if discourse elements have high confidence
        elements = result['metadata'].get('discourse_elements', [])
        high_conf_elements = [
            e for e in elements
            if e.get('confidence', 0) >= min_confidence
        ]

        if high_conf_elements:
            result['high_confidence_elements'] = high_conf_elements
            filtered.append(result)

    return filtered
```

---

## Phase 5: Compositional Queries (Future)

### Goal: Allow complex boolean queries over metadata

```python
# Query DSL
query_dsl = {
    "concepts": {"$in": ["Authority", "Scripture"]},
    "discourse": {
        "$and": [
            {"$contains": "Logical/Claim"},
            {"$contains": "Rhetorical/Thesis"}
        ]
    },
    "query_intent": {"$in": ["Evaluative", "Comparative"]},
    "facets.period": "Reformation",
    "confidence": {"$gte": 0.8}
}

# Execute
results = retriever.query(query_dsl)
```

---

## Testing Strategy

### Unit Tests

```python
def test_intent_classification():
    """Test intent classifier accuracy"""
    classifier = IntentClassifier()

    test_cases = [
        ("What is grace?", QueryIntent.DEFINITIONAL),
        ("How do I pray?", QueryIntent.PROCEDURAL),
        ("Why did God create the world?", QueryIntent.CAUSAL),
    ]

    for query, expected in test_cases:
        intents = classifier.classify(query)
        assert intents[0][0] == expected, f"Failed for: {query}"

def test_discourse_scoring():
    """Test discourse element matching"""
    metadata = {
        "discourse_elements": ["Logical/Claim", "Rhetorical/Thesis"]
    }
    preferred = ["Logical/Claim", "Logical/Evidence"]

    score = calculate_discourse_score(metadata, preferred)
    assert 0.4 <= score <= 0.6  # Should match 1 out of 2

def test_graph_traversal():
    """Test relationship traversal"""
    graph = DiscourseGraphBuilder()
    # ... add test chunks and relationships
    supports = graph.find_supporting_evidence("chunk_1")
    assert "chunk_2" in supports
```

### Integration Tests

```python
def test_full_retrieval_pipeline():
    """Test end-to-end retrieval"""

    query = "What are the arguments for God's existence?"

    # Should return chunks with:
    # - Concepts: God, Existence, Apologetics
    # - Discourse: Rhetorical/Thesis, Logical/Claim
    # - Intent: Evaluative

    results = retriever.retrieve(query, k=5)

    assert len(results) > 0
    assert any("God" in r['metadata'].get('concepts', []) for r in results)
    assert any("Rhetorical/Thesis" in r['metadata'].get('discourse_elements', []) for r in results)
```

### User Acceptance Tests

Create test queries from real usage:

```python
REAL_USER_QUERIES = [
    "What does Augustine say about the nature of evil?",
    "How do different traditions view the Eucharist?",
    "What are the main criticisms of natural theology?",
    "Can you explain the doctrine of the Trinity?",
]

for query in REAL_USER_QUERIES:
    results = retriever.retrieve(query)
    # Manual inspection: Are these good results?
    print(f"\n{'='*80}")
    print(f"Query: {query}")
    print('='*80)
    for i, r in enumerate(results[:3], 1):
        print(f"\n{i}. {r['content'][:300]}...")
        print(f"   Concepts: {r['metadata'].get('concepts')}")
        print(f"   Discourse: {r['metadata'].get('discourse_elements')[:3]}")
```

---

## Migration Path

### Option 1: Gradual (Recommended)

1. **Keep existing system running** (`enhanced_app.py`)
2. **Create parallel pipeline** for enhanced chunks
3. **Annotate new chunks** with full metadata
4. **Backfill** old chunks incrementally (10% per week)
5. **Switch over** when 80%+ of corpus is enhanced

### Option 2: Big Bang

1. Pause new annotations
2. Run batch enhancement on all existing chunks
3. Deploy new system
4. Resume with enhanced pipeline

**Recommendation:** Option 1 - less risky, allows iteration

---

## Performance Considerations

### Indexing
- **ChromaDB:** Good for semantic search, basic metadata filtering
- **PostgreSQL:** Better for complex relationship queries
- **Neo4j:** Ideal for graph traversal (if graph becomes large)

### Caching
```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_related_chunks(chunk_id, relation_type):
    """Cache frequently accessed relationships"""
    return query_relationships(chunk_id, relation_type)
```

### Batch Processing
```python
def batch_enhance_chunks(chunk_ids, batch_size=100):
    """Enhance multiple chunks in parallel"""
    from concurrent.futures import ThreadPoolExecutor

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = []
        for i in range(0, len(chunk_ids), batch_size):
            batch = chunk_ids[i:i+batch_size]
            futures.append(executor.submit(enhance_batch, batch))

        results = [f.result() for f in futures]
    return results
```

---

## Monitoring & Evaluation

### Metrics to Track

1. **Retrieval Quality**
   - Precision@k: Are top-k results relevant?
   - Recall@k: Did we find the relevant chunks?
   - MRR (Mean Reciprocal Rank): Where is first relevant result?

2. **Discourse Scoring**
   - % of queries where discourse score > 0.5
   - Correlation between semantic and discourse scores

3. **Graph Utilization**
   - % of queries using graph expansion
   - Average # of relationships traversed

4. **Intent Classification**
   - Intent classification confidence
   - % of queries with clear dominant intent

### Logging

```python
import logging

logger = logging.getLogger("discourse_graph")

def retrieve_with_logging(query, k=10):
    """Retrieval with detailed logging"""

    logger.info(f"Query: {query}")

    # Intent classification
    intents = classifier.classify(query)
    logger.info(f"Intents: {intents}")

    # Discourse filtering
    preferred_elements = get_preferred_elements(intents)
    logger.info(f"Preferred elements: {preferred_elements}")

    # Retrieval
    results = collection.query(query_texts=[query], n_results=k)
    logger.info(f"Retrieved {len(results['ids'][0])} chunks")

    # Graph expansion
    if use_graph_expansion:
        expanded = expand_via_graph(results)
        logger.info(f"Expanded to {len(expanded)} chunks via graph")

    return results
```

---

## Common Issues & Solutions

### Issue 1: Intent Classifier Low Accuracy
**Solution:** Collect more training data, use better model (fine-tuned BERT)

### Issue 2: Discourse Elements Too Sparse
**Solution:** Start with broader elements, gradually specialize

### Issue 3: Graph Too Large
**Solution:** Prune low-weight edges, use sampling for traversal

### Issue 4: Slow Retrieval
**Solution:** Add caching, pre-compute common paths, use approximate graph algorithms

---

## Next Steps

1. **Read** the full `DISCOURSE_GRAPH_FRAMEWORK.md`
2. **Run** the example code in `discourse_graph_retrieval.py`
3. **Annotate** 10-20 chunks using `EXAMPLE_ENHANCED_ANNOTATION.md` as guide
4. **Test** retrieval on those chunks
5. **Iterate** on element definitions based on what you find

**Start small, iterate fast, scale gradually.**

The beauty of this framework is that **every piece adds value independently** - you don't need to implement everything to see benefits.
