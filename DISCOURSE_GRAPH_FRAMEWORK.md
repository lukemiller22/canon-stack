# The Discourse Graph Framework (DGF)
## An Extension for AI Agent Retrieval Systems

**Built on:** Luke Miller's Knowledge Elements Framework (113 elements, 8 categories)
**Designed for:** Agentic RAG systems, compositional queries, graph-based reasoning

---

## Core Philosophy

Your original framework excels at **human-centered annotation** - capturing what a text *contains*. This extension adds **agent-centered metadata** - capturing what a text *enables* an AI to do.

### Key Innovations

1. **Three New Element Categories** (adding to your 8)
   - **Computational Elements** - What cognitive operations does this chunk support?
   - **Rhetorical Elements** - What argumentative moves does it make?
   - **Query Intent Elements** - What kinds of questions does it answer?

2. **Discourse Relationships** (Graph Layer)
   - Move from flat tags to typed relationships between chunks
   - Enable graph traversal and multi-hop reasoning

3. **Multi-Stage Retrieval Architecture**
   - Intent Classification → Concept Space → Discourse Patterns → Semantic Search
   - Combine symbolic and neural approaches

4. **Confidence Scoring**
   - Metadata includes certainty levels (definitive, probable, speculative)
   - Agents can reason about reliability

5. **Compositional Query Language**
   - Boolean logic over discourse elements
   - Example: `(Logical/Claim AND Practical/Solution) NOT Logical/Fallacy`

---

## Extended Framework: 11 Categories, 175+ Elements

### **Category 9: Computational Elements** (15 elements)

These capture *what cognitive operations* a chunk enables an agent to perform:

1. **Algorithm**
   : A step-by-step procedure or method described in the text that can be followed to accomplish a specific task
   // recipes, proof strategies, decision trees, workflows

2. **Transformation**
   : A mapping or conversion process that changes one form of input into a different output
   // data conversion, perspective shifts, reformulations, translations

3. **Validation**
   : Criteria, tests, or methods for verifying the correctness, truth, or quality of something
   // truth conditions, verification procedures, quality checks, acceptance criteria

4. **Aggregation**
   : Methods for combining, synthesizing, or integrating multiple pieces of information
   // summation rules, consensus methods, integration strategies, holistic views

5. **Inference**
   : Logical derivations or conclusions that can be drawn from the presented information
   // deductions, implications, consequences, corollaries

6. **Classification**
   : Categorization schemes or taxonomic frameworks for organizing concepts
   // typologies, taxonomies, classification systems, decision boundaries

7. **Extraction**
   : Information that can be pulled out and used independently from its context
   // key facts, data points, quotable insights, extractable principles

8. **Generation**
   : Templates, patterns, or frameworks that enable creating new content
   // generative patterns, templates, schemas, creative frameworks

9. **Comparison**
   : Explicit contrasts, similarities, or evaluative frameworks between multiple items
   // similarity measures, contrast structures, trade-off analyses, benchmarks

10. **Decomposition**
    : Breaking down complex concepts into constituent parts or simpler elements
    // analytical breakdowns, component analysis, factorization, deconstruction

11. **Composition**
    : Building up complex ideas from simpler building blocks
    // synthetic construction, assembly patterns, combination rules

12. **Optimization**
    : Methods or criteria for improving, maximizing, or finding the best solution
    // efficiency strategies, improvement heuristics, optimization criteria

13. **Prediction**
    : Frameworks for forecasting, anticipating, or projecting future states
    // predictive models, trend extrapolation, forecasting methods

14. **Diagnosis**
    : Methods for identifying problems, causes, or root issues
    // troubleshooting frameworks, causal analysis, root cause identification

15. **Evaluation**
    : Frameworks for assessing, judging, or measuring value or quality
    // assessment criteria, evaluation rubrics, scoring systems

---

### **Category 10: Rhetorical Elements** (12 elements)

These capture *argumentative structure and persuasive moves*:

1. **Thesis**
   : The central claim or position being advanced in an argument
   // main argument, core position, central proposition

2. **Antithesis**
   : A contrasting or opposing viewpoint presented for dialectical purposes
   // opposing view, counterposition, alternative perspective

3. **Dialectic**
   : A synthesis emerging from the tension between thesis and antithesis
   // reconciliation, higher-order integration, middle way

4. **Stipulation**
   : Definitions or assumptions explicitly stated as ground rules for discussion
   // working definitions, agreed premises, boundary conditions

5. **Concession**
   : Acknowledgment of valid points in opposing arguments
   // granted points, acknowledged limitations, fair admissions

6. **Amplification**
   : Expansion, elaboration, or intensification of a point for emphasis
   // extended development, detailed elaboration, emphatic restatement

7. **Qualification**
   : Nuancing, limiting, or adding conditions to a claim to make it more precise
   // hedging, scope limitation, precision refinement

8. **Appeal-Logos**
   : Logical reasoning and rational argumentation
   // logical proofs, rational arguments, evidence-based reasoning

9. **Appeal-Ethos**
   : Credibility, authority, or character-based persuasion
   // credentialing, expertise claims, trustworthiness signals

10. **Appeal-Pathos**
    : Emotional engagement and affective persuasion
    // emotional appeals, affective engagement, empathetic connection

11. **Refutation**
    : Direct rebuttal or dismantling of opposing arguments
    // counterargument, disproof, debunking

12. **Commonplace**
    : Appeal to shared beliefs, values, or cultural assumptions
    // cultural touchstones, shared values, common ground

---

### **Category 11: Query Intent Elements** (12 elements)

These tag chunks by *what kinds of questions they answer* - crucial for intent-based retrieval:

1. **Definitional**
   : Answers "What is X?" questions
   // concept explanations, term definitions, essence statements

2. **Procedural**
   : Answers "How do I do X?" questions
   // instructions, methods, step-by-step guides

3. **Causal**
   : Answers "Why does X happen?" or "What causes X?" questions
   // explanations of causes, mechanisms, reasons

4. **Comparative**
   : Answers "How does X compare to Y?" questions
   // contrasts, similarities, relative assessments

5. **Evaluative**
   : Answers "Is X good/true/valuable?" questions
   // judgments, assessments, appraisals

6. **Historical**
   : Answers "What happened?" or "When did X occur?" questions
   // chronological accounts, historical narratives, timelines

7. **Predictive**
   : Answers "What will happen?" or "What are the consequences?" questions
   // forecasts, implications, projected outcomes

8. **Diagnostic**
   : Answers "What's wrong?" or "What's the problem?" questions
   // problem identification, root cause analysis, troubleshooting

9. **Prescriptive**
   : Answers "What should be done?" questions
   // recommendations, imperatives, action items

10. **Interpretive**
    : Answers "What does X mean?" questions
    // meaning-making, significance, interpretation

11. **Exemplary**
    : Answers "Can you give me an example?" questions
    // illustrations, case studies, concrete instances

12. **Synthetic**
    : Answers "How does it all fit together?" questions
    // integrative overviews, big-picture connections, synthesis

---

## Discourse Relationships (Graph Layer)

Instead of just tagging chunks, we create **typed relationships** between them:

### Logical Relationships
- `supports(chunk_a, chunk_b)` - A provides evidence for B
- `contradicts(chunk_a, chunk_b)` - A is incompatible with B
- `refutes(chunk_a, chunk_b)` - A explicitly argues against B
- `assumes(chunk_a, chunk_b)` - A presupposes B
- `implies(chunk_a, chunk_b)` - A logically entails B

### Structural Relationships
- `exemplifies(chunk_a, concept_x)` - A is an instance of X
- `defines(chunk_a, term_x)` - A gives the definition of X
- `elaborates(chunk_a, chunk_b)` - A expands on B
- `summarizes(chunk_a, chunk_b)` - A condenses B
- `prerequisite(chunk_a, chunk_b)` - A must be understood before B

### Rhetorical Relationships
- `responds_to(chunk_a, chunk_b)` - A addresses B
- `concedes_to(chunk_a, chunk_b)` - A grants a point from B
- `qualifies(chunk_a, chunk_b)` - A adds nuance to B
- `applies(chunk_a, domain_x)` - A shows X in practice

### Cross-Reference Relationships
- `alludes_to(chunk_a, source_x)` - A references X indirectly
- `quotes(chunk_a, source_x)` - A cites X directly
- `synthesizes(chunk_a, [chunk_b, chunk_c])` - A combines B and C

---

## Enhanced Metadata Schema

```yaml
# Basic Metadata (your original system)
concepts: [[Concept1]], [[Concept2]]
topics: [[Concept1/Topic1]], [[Concept2/Topic2]]
terms: [[Term1]], [[Term2]]
scripture_references: [[Book Chapter]], [[Book Chapter:Verse]]
named_entities: [[Person/Name]], [[Place/Location]]
structure_path: [[Section > Subsection]]

# Discourse Elements (extended)
discourse_elements:
  semantic:
    - element: [[Semantic/Definition]]
      content: "God is that than which no greater can be conceived"
      confidence: definitive
  logical:
    - element: [[Logical/Claim]]
      content: "Human reason alone cannot reach God"
      confidence: probable
  rhetorical:
    - element: [[Rhetorical/Thesis]]
      content: "Faith and reason are complementary, not contradictory"
      confidence: definitive
  computational:
    - element: [[Computational/Classification]]
      content: "Three types of theology: dogmatic, moral, practical"
      confidence: definitive
  query_intent:
    - [[Query/Definitional]]  # Answers "What is X?"
    - [[Query/Comparative]]   # Answers "How does X compare to Y?"

# Discourse Relationships (graph edges)
relationships:
  supports:
    - chunk_id: "lewis_mere_christianity_ch1_p3"
      weight: 0.9
  contradicts:
    - chunk_id: "nietzsche_genealogy_ch2_p5"
      weight: 0.7
  prerequisite:
    - chunk_id: "lewis_mere_christianity_ch1_p1"
      weight: 1.0
  exemplifies:
    - concept: [[Apologetics]]
      weight: 0.95

# Agent Affordances (what can an agent DO with this chunk?)
affordances:
  - use_as_definition: [[God]]
  - use_in_argument_for: [[Faith and Reason/Complementarity]]
  - use_as_counterexample_to: [[Rationalism/Self-Sufficiency]]
  - extract_principle: "Divine transcendence requires humility in theology"
  - generate_from_template: null
```

---

## Multi-Stage Retrieval Architecture

### Stage 1: Intent Classification
**Input:** User query
**Process:** Classify query into intent categories
**Example:**
- Query: "What is the relationship between faith and reason?"
- Intent: `Definitional` (60%) + `Comparative` (40%)

### Stage 2: Concept Space Retrieval
**Input:** Intent + Query
**Process:** Identify relevant concepts from your fixed Concepts index
**Example:**
- Concepts: `[[Faith]]`, `[[Reason]]`, `[[Knowledge]]`, `[[Revelation]]`

### Stage 3: Discourse Pattern Matching
**Input:** Concepts + Intent
**Process:** Filter chunks by discourse elements that match the intent
**Example:**
- For `Definitional` intent: Prioritize chunks with `Semantic/Definition`, `Semantic/Description`
- For `Comparative` intent: Prioritize chunks with `Computational/Comparison`, `Logical/Claim`

### Stage 4: Graph Traversal
**Input:** Initial candidate chunks
**Process:** Expand via discourse relationships
**Example:**
- Find chunk defining "faith"
- Traverse `elaborates` edges to get fuller explanation
- Traverse `exemplifies` edges to get concrete examples

### Stage 5: Semantic Search
**Input:** Expanded candidate set
**Process:** Re-rank using embedding similarity
**Output:** Top-k chunks with discourse context

### Stage 6: Answer Synthesis
**Input:** Retrieved chunks + metadata
**Process:** Construct answer using discourse structure
**Example:**
- Lead with `Semantic/Definition` chunks
- Support with `Logical/Evidence` chunks
- Qualify with `Logical/Conditional` chunks
- Conclude with `Practical/Application` chunks

---

## Compositional Query Language

Allow agents to query using **boolean logic over discourse elements**:

```python
# Find all claims about salvation that have supporting evidence but no fallacies
query = """
  concepts: [[Salvation]]
  AND discourse: [[Logical/Claim]]
  AND discourse: [[Logical/Evidence]]
  NOT discourse: [[Logical/Fallacy]]
"""

# Find practical applications of theological concepts
query = """
  concepts: [[Theology]]
  AND discourse: [[Practical/Application]]
  AND query_intent: [[Query/Prescriptive]]
"""

# Find definitions that are contested (have objections)
query = """
  discourse: [[Semantic/Definition]]
  AND relationships: has_objection
"""

# Find arguments that synthesize multiple traditions
query = """
  discourse: [[Rhetorical/Dialectic]]
  AND relationships: synthesizes[count >= 2]
  AND named_entities: [[Period/*]]  # Multiple historical periods
"""
```

---

## Confidence Scoring System

Not all metadata is equally certain. Add confidence levels:

- **definitive** (1.0): Explicitly stated, unambiguous
- **probable** (0.7-0.9): Strongly implied, highly likely
- **possible** (0.4-0.6): Plausible interpretation, uncertain
- **speculative** (0.1-0.3): Weak inference, questionable

**Example:**
```yaml
discourse_elements:
  - element: [[Logical/Claim]]
    content: "God exists"
    confidence: definitive  # Explicitly stated
  - element: [[Logical/Assumption]]
    content: "The author assumes metaphysical realism"
    confidence: probable  # Strongly implied but not stated
  - element: [[Personal/Emotion]]
    content: "Hints at frustration with skeptics"
    confidence: possible  # Interpretive
```

This allows agents to reason about reliability and hedge appropriately.

---

## Rethinking Concept/Topic/Term Implementation

### Current System (Hierarchical)
```
Concept (fixed) → Topic (flexible) → Term (flexible)
[[Authority]] → [[Authority/Scripture vs Tradition]] → "biblical warrant"
```

**Limitation:** Single hierarchy, can't capture cross-cutting concerns

### **Proposed: Faceted Classification**

Instead of strict hierarchy, use **multiple orthogonal facets**:

#### Facet 1: Domain Concept (from your fixed list)
`[[Authority]]`, `[[Scripture]]`, `[[Tradition]]`

#### Facet 2: Discourse Type
`[[Question]]`, `[[Debate]]`, `[[Principle]]`, `[[Application]]`

#### Facet 3: Theological Tradition
`[[Reformed]]`, `[[Catholic]]`, `[[Orthodox]]`, `[[Anabaptist]]`

#### Facet 4: Historical Period
`[[Patristic]]`, `[[Medieval]]`, `[[Reformation]]`, `[[Modern]]`

#### Facet 5: Scholarly Level
`[[Academic]]`, `[[Popular]]`, `[[Devotional]]`

**Example Chunk:**
```yaml
facets:
  domain_concepts: [[Authority]], [[Scripture]], [[Tradition]]
  discourse_type: [[Debate]]
  traditions: [[Reformed]], [[Catholic]]
  period: [[Reformation]]
  level: [[Academic]]
```

**Benefits:**
- Multi-dimensional filtering: "Show me Popular-level discussions of Scripture/Tradition debate in the Reformation period"
- Cross-cutting queries: "Find all Debates across any tradition"
- Flexible composition: Add new facets without restructuring

### **Enhanced Term System: Semantic Clusters**

Instead of flat term list, create **semantic clusters**:

```yaml
term_clusters:
  authority_language:
    formal: ["ecclesiastical authority", "magisterium", "apostolic succession"]
    colloquial: ["church says", "official teaching", "what we believe"]
    critical: ["institutional control", "power structures", "authority claims"]

  scripture_language:
    formal: ["biblical inerrancy", "divine inspiration", "canonical text"]
    colloquial: ["what the Bible says", "God's Word", "Scripture teaches"]
    metaphorical: ["lamp unto my feet", "living Word", "sword of the Spirit"]

  technical_terms:
    latin: ["sola scriptura", "prima scriptura", "regula fidei"]
    greek: ["theopneustos", "graphe", "logos"]
    hebrew: ["torah", "tanakh"]
```

**Benefits:**
- Captures **register** (formal vs colloquial)
- Captures **stance** (neutral vs critical)
- Captures **language family** (Latin vs vernacular)
- Enables smarter search: User searches "what the Bible says" → matches formal "biblical authority" chunks

---

## Implementation Priorities

### Phase 1: Core Extensions (Week 1)
- [ ] Add 3 new element categories to framework
- [ ] Design graph relationship schema
- [ ] Create confidence scoring system

### Phase 2: Retrieval Pipeline (Week 2)
- [ ] Implement intent classifier
- [ ] Build discourse-aware retrieval
- [ ] Create graph traversal engine

### Phase 3: Query Language (Week 3)
- [ ] Design compositional query DSL
- [ ] Implement query parser
- [ ] Build execution engine

### Phase 4: Tooling (Week 4)
- [ ] Update annotation prompts
- [ ] Create validation tools
- [ ] Build visualization dashboard

---

## Example: How It All Works Together

**User Query:** "What are the main arguments for and against sola scriptura?"

### Traditional RAG (Semantic Search Only)
1. Embed query
2. Find similar chunks
3. Return top-k
**Problem:** May miss counterarguments, lack structure

### Discourse Graph Framework
1. **Intent Classification:** `Comparative` (0.8) + `Argumentative` (0.7)
2. **Concept Retrieval:** `[[Scripture]]`, `[[Authority]]`, `[[Tradition]]`
3. **Discourse Pattern:** Find chunks with:
   - `[[Rhetorical/Thesis]]` + concept:`[[Scripture]]`
   - `[[Rhetorical/Antithesis]]` + concept:`[[Authority]]`
   - `[[Logical/Claim]]` + `[[Logical/Evidence]]`
4. **Graph Traversal:**
   - Find "sola scriptura" definition chunk
   - Follow `supports` edges to get pro arguments
   - Follow `contradicts` edges to get con arguments
   - Follow `concedes_to` edges to get nuanced positions
5. **Semantic Re-ranking:** Within each category
6. **Answer Synthesis:**
   ```
   Definition: [Chunk with Semantic/Definition]

   Arguments For:
   - [Chunk with Rhetorical/Thesis + supports(sola_scriptura)]
   - [Evidence chunks via supports edges]

   Arguments Against:
   - [Chunk with Rhetorical/Antithesis + contradicts(sola_scriptura)]
   - [Evidence chunks]

   Nuanced Positions:
   - [Chunks with Rhetorical/Dialectic or Concession]
   ```

**Result:** Structured, balanced, discourse-aware answer with explicit argumentative structure.

---

## Next Steps

This framework is **fully compatible** with your existing system - it's pure extension, not replacement. You can:

1. **Start small:** Add just Computational elements first
2. **Add relationships gradually:** Begin with `supports`/`contradicts`
3. **Enhance queries incrementally:** Start with simple intent classification

The beauty is that **every enhancement adds value independently** - you don't need to implement everything at once.

Ready to build this? I'll create the implementation files next.
