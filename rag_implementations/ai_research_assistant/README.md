# AI Theological Research Assistant

An intelligent research assistant that uses AI to analyze queries, intelligently filter theological texts, and synthesize comprehensive research summaries with proper citations.

## Features

- **Intelligent Query Analysis**: AI analyzes theological concepts and query types
- **Metadata-Aware Filtering**: Uses topics, concepts, functions, Scripture references, and other metadata
- **Vector Search**: Combines semantic similarity with intelligent filtering
- **Research Synthesis**: Generates comprehensive summaries with numbered citations
- **Source Transparency**: Shows all sources used with clickable citations
- **Reasoning Transparency**: Explains search strategy and filter choices

## Quick Start

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the Application**:
   ```bash
   python app.py
   ```

3. **Open in Browser**:
   Navigate to `http://localhost:5000`

## How It Works

1. **Query Analysis**: AI analyzes your question to identify:
   - Query type (doctrinal, exegetical, historical, etc.)
   - Theological concepts involved
   - Best search strategy and filters to use

2. **Intelligent Search**: Combines vector similarity with metadata filtering:
   - Uses OpenAI embeddings for semantic similarity
   - Applies intelligent filters based on query analysis
   - Ranks results by relevance

3. **Research Synthesis**: AI generates a comprehensive summary:
   - Synthesizes information from multiple sources
   - Includes numbered citations [1], [2], etc.
   - Maintains theological accuracy and nuance

4. **Source Panel**: Shows all sources used:
   - Organized by source with metadata
   - Clickable citations that scroll to relevant sources
   - Relevance explanations for each source

## Example Queries

- "What does the Bible say about the deity of Christ?"
- "How do Calvin and Luther differ on justification?"
- "What are the key metaphors used to describe God's relationship with Israel?"
- "Explain the doctrine of the Trinity from Scripture and church history"

## Technical Details

- **Backend**: Flask with OpenAI API integration
- **Frontend**: Clean HTML/CSS/JavaScript interface
- **Search**: Vector similarity + metadata filtering
- **AI Model**: GPT-4o-mini for analysis and synthesis
- **Embeddings**: OpenAI text-embedding-3-small

## Dataset

Uses the theological chunks dataset with rich metadata including:
- Topics, Concepts, Themes
- Function types (Logical/Claim, Symbolic/Metaphor, etc.)
- Scripture references and proper nouns
- Structure paths and author information
