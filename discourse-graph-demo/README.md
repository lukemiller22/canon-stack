# 🚀 Discourse Graph Framework - Interactive Demo

**A standalone demo comparing traditional RAG vs enhanced discourse-aware retrieval**

## What This Demo Shows

This is a **self-contained demonstration** of the Discourse Graph Framework that runs independently from your main canon-stack application. It shows the difference between:

1. **Traditional RAG** - Semantic similarity only
2. **Discourse Graph RAG** - Intent + discourse + semantic combined

## Quick Start

```bash
cd /Users/lukemiller/canon-stack/discourse-graph-demo
python3 demo.py
```

## What's Included

### Sample Data (`sample_data.json`)
5 hand-curated chunks with enhanced metadata:
- C.S. Lewis on faith & the "Lord, Liar, Lunatic" trilemma
- Augustine on the nature of time
- Chesterton on true vs false humility
- D.A. Carson on culture transformation

Each chunk includes:
- ✅ Original metadata (concepts, topics, terms)
- ✅ **NEW:** Computational elements
- ✅ **NEW:** Rhetorical elements
- ✅ **NEW:** Query intent tags
- ✅ **NEW:** Relationship graph edges

### Demo Script (`demo.py`)
Interactive comparison showing:
- Intent classification
- Discourse pattern matching
- Combined scoring
- Side-by-side results
- Explanations for each result

## Try These Queries

1. **Definitional:** "What is faith?"
   - Traditional: keyword matching
   - Discourse Graph: prioritizes `Semantic/Definition` elements

2. **Diagnostic:** "What is the problem with modern humility?"
   - Traditional: finds "humility" mentions
   - Discourse Graph: finds `Computational/Diagnosis` + `Practical/Problem` chunks

3. **Prescriptive:** "How should Christians engage with culture?"
   - Traditional: keyword matching
   - Discourse Graph: prioritizes `Practical/Strategy` elements

4. **Evaluative:** "Compare different views on Jesus' identity"
   - Traditional: finds "Jesus" mentions
   - Discourse Graph: finds `Rhetorical/Thesis` + `Computational/Comparison` chunks

## Key Differences You'll See

### Traditional RAG Output:
```
RANK #1 | Score: 0.234
Source: Mere Christianity by C.S. Lewis
Text: [chunk text]
Reason: Semantic similarity (keyword overlap)
```

### Discourse Graph RAG Output:
```
🎯 Detected Intent: definitional (100% confidence)
📝 Prioritizing: Semantic/Definition, Semantic/Description

RANK #1 | Score: 0.850
Source: Mere Christianity by C.S. Lewis
Text: [chunk text]

📊 Scoring Breakdown:
  • Semantic: 0.234
  • Discourse: 1.000 (matched Semantic/Definition)
  • Intent: 1.000 (matches Definitional query)
  • Matched Elements: Semantic/Definition, Rhetorical/Thesis

💡 Reason: Intent: definitional, Discourse: 2 matches
```

## Why This Matters

The Discourse Graph Framework:
1. **Understands query intent** - "What is X?" vs "Why X?" vs "How X?"
2. **Matches discourse patterns** - Finds definitions when you ask for definitions
3. **Explains results** - Shows WHY each chunk was selected
4. **Better precision** - Combines semantic + structural matching

## No Risk to Your Production System

This demo:
- ✅ Runs completely independently
- ✅ Uses only sample data (not your full corpus)
- ✅ Doesn't touch your existing `enhanced_app.py`
- ✅ No database dependencies (pure Python)

## Next Steps

After trying the demo:

1. **If impressed:** Follow `IMPLEMENTATION_GUIDE.md` to integrate Phase 1
2. **If skeptical:** Try more queries, compare results
3. **If curious:** Read `DISCOURSE_GRAPH_FRAMEWORK.md` for full design

## Architecture Comparison

```
┌─────────────────────────────────────────────────────────────┐
│                    TRADITIONAL RAG                          │
├─────────────────────────────────────────────────────────────┤
│  Query → Embedding → Similarity Search → Top K Results     │
│                                                             │
│  ❌ No intent understanding                                 │
│  ❌ No discourse structure                                  │
│  ❌ Pure semantic similarity                                │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                DISCOURSE GRAPH RAG                          │
├─────────────────────────────────────────────────────────────┤
│  Query → Intent Classification                              │
│       ↓                                                     │
│  Discourse Pattern Matching (prioritize elements)          │
│       ↓                                                     │
│  Semantic Search (with discourse boost)                    │
│       ↓                                                     │
│  Combined Scoring (0.4 semantic + 0.4 discourse + 0.2 intent)│
│       ↓                                                     │
│  Ranked Results with Explanations                          │
│                                                             │
│  ✅ Intent-aware                                            │
│  ✅ Discourse-aware                                         │
│  ✅ Explainable                                             │
│  ✅ Better precision                                        │
└─────────────────────────────────────────────────────────────┘
```

## Questions?

- Read the design: `../DISCOURSE_GRAPH_FRAMEWORK.md`
- See full example: `../EXAMPLE_ENHANCED_ANNOTATION.md`
- Implementation guide: `../IMPLEMENTATION_GUIDE.md`
- Main README: `../README_DISCOURSE_GRAPH.md`

Ready to integrate? Start with Phase 1 (1 week, low risk, immediate value).
