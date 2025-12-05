# Example: Enhanced Discourse Graph Annotation

## Source Text Chunk

**Source:** C.S. Lewis, *Mere Christianity*

**Chunk:**
> I am trying here to prevent anyone saying the really foolish thing that people often say about Him: "I'm ready to accept Jesus as a great moral teacher, but I don't accept His claim to be God." That is the one thing we must not say. A man who was merely a man and said the sort of things Jesus said would not be a great moral teacher. He would either be a lunatic—on a level with the man who says he is a poached egg—or else he would be the Devil of Hell. You must make your choice. Either this man was, and is, the Son of God: or else a madman or something worse. You can shut Him up for a fool, you can spit at Him and kill Him as a demon; or you can fall at His feet and call Him Lord and God. But let us not come with any patronizing nonsense about His being a great human teacher. He has not left that open to us. He did not intend to.

---

## BASIC METADATA (Original Framework)

### Concepts
- [[Jesus Christ]]
- [[Authority]]
- [[Truth]]
- [[Logic]]

### Topics
- [[Jesus Christ/Divinity and Deity]]
- [[Jesus Christ/Identity Claims]]
- [[Logic/Trilemma Arguments]]
- [[Apologetics/Defense of Orthodoxy]]

### Terms
- "Lord, Liar, or Lunatic"
- "trilemma"
- "deity of Christ"
- "moral teacher"
- "great human teacher"
- "Son of God"

### Scripture References
- (None directly cited, but alludes to Gospel claims)

### Named Entities
- [[Person/Jesus Christ]]

### Structure Path
- [[Book 2: What Christians Believe > Chapter 3: The Shocking Alternative]]

---

## ENHANCED METADATA (Discourse Graph Framework)

### Discourse Elements

#### Semantic Elements
- **[[Semantic/Concept]]**: "Three mutually exclusive categories for Jesus' identity"
  - *Confidence:* DEFINITIVE

#### Logical Elements
- **[[Logical/Claim]]**: "Jesus cannot be merely a great moral teacher given his claims"
  - *Confidence:* DEFINITIVE
- **[[Logical/Warrant]]**: "A mere man making divine claims would be either deluded or evil"
  - *Confidence:* DEFINITIVE
- **[[Logical/Conditional]]**: "If Jesus claimed divinity, then he must be evaluated as such"
  - *Confidence:* DEFINITIVE

#### Computational Elements
- **[[Computational/Classification]]**: "Three categories: Divine, Lunatic, or Demonic"
  - *Confidence:* DEFINITIVE
- **[[Computational/Validation]]**: "Tests the coherence of 'good teacher but not God' position"
  - *Confidence:* DEFINITIVE
- **[[Computational/Inference]]**: "From Jesus' claims, we can deduce limited identity options"
  - *Confidence:* DEFINITIVE

#### Rhetorical Elements
- **[[Rhetorical/Thesis]]**: "The 'Lord, Liar, or Lunatic' trilemma"
  - *Confidence:* DEFINITIVE
- **[[Rhetorical/Refutation]]**: "Refutes the 'great moral teacher only' position"
  - *Confidence:* DEFINITIVE
- **[[Rhetorical/Appeal-Logos]]**: "Uses logical elimination to force a choice"
  - *Confidence:* DEFINITIVE
- **[[Rhetorical/Amplification]]**: "Vivid language ('poached egg', 'Devil of Hell') emphasizes absurdity"
  - *Confidence:* PROBABLE

#### Practical Elements
- **[[Practical/Principle]]**: "Cannot compartmentalize Jesus' moral teaching from his identity claims"
  - *Confidence:* DEFINITIVE
- **[[Practical/Imperative]]**: "You must make your choice"
  - *Confidence:* DEFINITIVE

### Query Intent Tags
- [[Query/Evaluative]] - Evaluates the coherence of a position
- [[Query/Comparative]] - Compares three alternative interpretations
- [[Query/Diagnostic]] - Diagnoses the logical flaw in a common view

---

## DISCOURSE RELATIONSHIPS (Graph Edges)

### Supports (Evidence For)
- `supports` → **lewis_mc_book2_ch1_p2** *(Claims about Jesus' divine authority)*
  - Weight: 0.95
  - Note: "This trilemma builds on establishing what Jesus actually claimed"

### Elaborates (Expands On)
- `elaborates` → **lewis_mc_book2_ch3_p1** *(Introduction to the chapter)*
  - Weight: 0.9
  - Note: "Provides the detailed argument for the chapter's main point"

### Refutes (Argues Against)
- `refutes` → **modernist_jesus_as_teacher** *(Liberal Protestant 'Jesus as moral teacher' view)*
  - Weight: 0.85
  - Note: "Directly targets this specific theological position"

### Exemplifies (Instance Of)
- `exemplifies` → **Concept: [[Apologetics]]**
  - Weight: 1.0
  - Note: "Classic example of apologetic argumentation"

- `exemplifies` → **Concept: [[Logic]]**
  - Weight: 0.95
  - Note: "Textbook case of elimination argument"

### Alludes To
- `alludes_to` → **Gospel Claims of Divinity**
  - Weight: 0.7
  - Note: "Presupposes Gospel accounts without citing them directly"

### Applied By
- `applied_by` → **christian_apologetics_literature** *(Later apologetic works)*
  - Weight: 0.9
  - Note: "This trilemma has been widely adopted in apologetic discourse"

---

## FACETED CLASSIFICATION

```yaml
facets:
  domain_concepts:
    - Jesus Christ
    - Apologetics
    - Logic
    - Authority

  discourse_type:
    - Argument
    - Refutation
    - Classification

  traditions:
    - Anglican
    - Broad Christian

  period:
    - Modern (20th Century)

  genre:
    - Apologetics
    - Popular Theology

  audience_level:
    - Popular
    - Educated Layperson

  rhetorical_mode:
    - Logos (Logical)
    - Direct/Confrontational

  argument_pattern:
    - Trilemma
    - Elimination
    - False Dilemma Refutation
```

---

## AGENT AFFORDANCES (What can AI agents DO with this chunk?)

```yaml
affordances:
  use_as_argument_for:
    - "Deity of Christ"
    - "Coherence of Christian orthodoxy"
    - "Against liberal Christology"

  use_as_refutation_of:
    - "Jesus as merely moral teacher"
    - "Non-divine Jesus views"

  extract_principle:
    - "Identity claims cannot be separated from moral teaching"
    - "Logical coherence matters in theological evaluation"

  extract_pattern:
    - template: "Trilemma Argument"
      structure: "If A claims X, then A is either Y, Z, or W. Not Y, not Z, therefore W."

  generate_similar_argument:
    - domain: "Any figure making extraordinary claims"
    - pattern: "Apply trilemma to other self-proclaimed divine figures"

  use_in_comparison_with:
    - "Other religious founders' claims"
    - "Other apologetic arguments for divinity"

  classify_as:
    - argument_type: "Elimination"
    - fallacy_risk: "False Trilemma (if there are other options)"
    - strength: "High (if premises accepted)"
```

---

## ENHANCED TERM CLUSTERS

```yaml
term_clusters:
  core_argument:
    formal: ["Lord, Liar, or Lunatic", "trilemma argument", "Christological argument"]
    colloquial: ["Jesus was either God or crazy", "can't be just a good teacher"]
    critical: ["Lewis's trilemma", "false trilemma objection"]

  divinity_language:
    formal: ["deity of Christ", "divine nature", "Son of God"]
    colloquial: ["God in the flesh", "God become man"]
    biblical: ["Son of God", "Lord and God"]

  alternative_views:
    liberal: ["moral teacher", "great human teacher", "ethical exemplar"]
    orthodox: ["Lord and God", "divine Savior"]

  logical_terminology:
    formal: ["mutual exclusivity", "exhaustive categories", "elimination"]
    colloquial: ["only three options", "can't have it both ways"]
```

---

## CONFIDENCE SCORING EXAMPLE

```yaml
metadata_confidence:
  # High confidence (explicitly stated)
  - element: [[Rhetorical/Thesis]]
    content: "Lord, Liar, or Lunatic trilemma"
    confidence: DEFINITIVE (1.0)
    reason: "Explicitly and clearly stated"

  - element: [[Computational/Classification]]
    content: "Three categories for Jesus"
    confidence: DEFINITIVE (1.0)
    reason: "Directly enumerated in text"

  # Medium confidence (strongly implied)
  - element: [[Rhetorical/Amplification]]
    content: "Vivid language emphasizes absurdity"
    confidence: PROBABLE (0.8)
    reason: "Rhetorical strategy is clear but not explicitly stated"

  - element: [[Query/Diagnostic]]
    content: "Diagnoses flaw in common view"
    confidence: PROBABLE (0.8)
    reason: "Query intent inferred from argumentative structure"

  # Lower confidence (interpretive)
  - relationship: alludes_to Gospel Claims
    confidence: POSSIBLE (0.7)
    reason: "Presupposes Gospel accounts but doesn't cite them"
```

---

## COMPOSITIONAL QUERY EXAMPLES

### Query 1: Find logical arguments for Christ's divinity
```
concepts: [[Jesus Christ]] AND [[Apologetics]]
discourse: [[Logical/Claim]] AND [[Rhetorical/Thesis]]
query_intent: [[Query/Evaluative]]
```
**Result:** This chunk would rank highly (direct match)

### Query 2: Find refutations of liberal theology
```
discourse: [[Rhetorical/Refutation]]
relationships: refutes
facets.traditions: [Liberal, Modernist]
```
**Result:** This chunk matches (refutes modernist view)

### Query 3: Find classification arguments
```
discourse: [[Computational/Classification]]
discourse: [[Logical/Warrant]]
NOT fallacy: [[Logical/Fallacy]]
```
**Result:** This chunk matches (trilemma is classification)

### Query 4: Find apologetic arguments using logic appeals
```
concepts: [[Apologetics]]
discourse: [[Rhetorical/Appeal-Logos]]
facets.audience_level: [Popular, Educated Layperson]
confidence >= PROBABLE
```
**Result:** Strong match

---

## COMPARATIVE ANNOTATION: Before & After

### TRADITIONAL RAG SYSTEM
```json
{
  "chunk_id": "lewis_mc_b2c3p2",
  "text": "[chunk text]",
  "embedding": [0.123, -0.456, ...],
  "metadata": {
    "source": "Mere Christianity",
    "author": "C.S. Lewis",
    "page": 52
  }
}
```
**Retrieval:** Purely semantic similarity
**Limitation:** Can't distinguish argument types, intentions, or logical structure

### DISCOURSE GRAPH SYSTEM
```json
{
  "chunk_id": "lewis_mc_b2c3p2",
  "text": "[chunk text]",
  "embedding": [0.123, -0.456, ...],
  "metadata": {
    "source": "Mere Christianity",
    "author": "C.S. Lewis",

    "concepts": ["Jesus Christ", "Apologetics", "Logic"],
    "topics": ["Jesus Christ/Divinity", "Apologetics/Defense"],

    "discourse_elements": [
      {"type": "Logical/Claim", "confidence": 1.0},
      {"type": "Rhetorical/Thesis", "confidence": 1.0},
      {"type": "Computational/Classification", "confidence": 1.0}
    ],

    "query_intents": ["Evaluative", "Comparative", "Diagnostic"],

    "relationships": [
      {"type": "supports", "target": "lewis_mc_b2c1p2", "weight": 0.95},
      {"type": "refutes", "target": "modernist_view", "weight": 0.85}
    ],

    "facets": {
      "discourse_type": ["Argument", "Refutation"],
      "argument_pattern": ["Trilemma", "Elimination"],
      "audience_level": ["Popular"]
    }
  }
}
```

**Retrieval:** Multi-stage
1. Intent classification: "Evaluative + Comparative"
2. Discourse matching: Prioritize Logical/Claim + Computational/Classification
3. Graph expansion: Include supporting evidence via `supports` edges
4. Re-ranking: Combine semantic + discourse scores

**Advantage:** Returns this chunk for questions about:
- "Arguments for Jesus' divinity" (via concepts + rhetorical thesis)
- "Logical problems with Jesus as teacher view" (via refutation relationship)
- "Examples of apologetic trilemmas" (via argument pattern facet)

---

## IMPLEMENTATION NOTES

1. **Backward Compatible:** All original metadata preserved
2. **Incremental Adoption:** Can add new elements gradually
3. **Confidence Levels:** Allows agents to reason about certainty
4. **Graph Relationships:** Enable multi-hop reasoning
5. **Query Intents:** Power intent-driven retrieval
6. **Facets:** Enable multi-dimensional filtering

This enhanced annotation turns a simple text chunk into a **rich knowledge node** in a discourse graph, enabling far more sophisticated retrieval and reasoning than semantic search alone.
