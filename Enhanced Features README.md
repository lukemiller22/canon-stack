# Enhanced AI Theological Research Assistant

A compact, Logos Bible Software-inspired UI for intelligent theological research with source selection, search history, and citation tracking.

## 🚀 New Features

### 1. **Compact Logos-like Design**
- Smaller fonts, reduced padding, more information density
- Professional gray-based color scheme
- Efficient use of screen space for research workflows

### 2. **Source Stack Selection**
- Choose "All Sources" or "Custom Selection"
- Select specific sources to include in your search
- Real-time source count display
- Persistent source selection preferences

### 3. **Search History & Persistence**
- Save your research searches with full context
- Browse previous queries with timestamps
- Reload past searches with original source selections
- Local storage persistence (up to 50 searches)
- One-click history clearing

### 4. **Enhanced Citation System**
- Clickable numbered citations [1], [2], etc.
- Smooth scrolling to source references
- Temporary highlighting of cited sources
- Rich metadata tooltips on hover

## 📁 File Structure

```
enhanced_research_assistant/
├── enhanced_app.py           # Main Flask application
├── enhanced_index.html       # Enhanced UI with new features
├── requirements.txt          # Python dependencies
├── theological_chunks_with_embeddings.jsonl  # Dataset (required)
└── .env                     # Environment variables
```

## 🛠️ Setup Instructions

### 1. **Install Dependencies**
```bash
pip install -r requirements.txt
```

### 2. **Environment Configuration**
Create a `.env` file with your OpenAI API key:
```bash
OPENAI_API_KEY=your_openai_api_key_here
```

### 3. **Dataset Requirements**
Ensure you have the theological dataset file:
- `theological_chunks_with_embeddings.jsonl`
- Should contain chunks with embeddings, metadata, and source information

### 4. **Run the Application**
```bash
python enhanced_app.py
```

### 5. **Access the Interface**
Open your browser to: `http://localhost:5001`

## 🎯 Usage Guide

### **Basic Research Workflow**
1. **Select Sources**: Choose "All Sources" or customize your source stack
2. **Enter Query**: Type your theological research question
3. **Review Results**: Read the AI-generated summary with citations
4. **Explore Sources**: Click citations to see supporting source material
5. **Save Research**: Save important searches for future reference

### **Source Selection**
- **All Sources**: Include all available theological texts
- **Custom Selection**: 
  - Select "Custom Selection" from dropdown
  - Choose specific sources from the sidebar
  - Apply selection and search

### **Search History**
- **Save Searches**: Click "Save" after getting results
- **Browse History**: Click "History" to view past searches
- **Reload Research**: Click any history item to restore that search
- **Clear History**: Use "Clear All" to remove all saved searches

### **Citation Navigation**
- **Click Citations**: Click any [1], [2] etc. in the summary
- **Auto-scroll**: Automatically scrolls to the referenced source
- **Metadata Tooltips**: Hover over the "ⓘ" icon for detailed metadata

## 🔧 Technical Features

### **AI-Powered Analysis**
- Intelligent query analysis and classification
- Automatic metadata filtering based on query type
- Combined vector similarity + metadata relevance scoring

### **Search Strategy**
- OpenAI embeddings for semantic similarity
- Metadata boosting for theological relevance
- Source filtering for focused research

### **Data Storage**
- Local storage for search history
- JSON-based persistence
- Automatic cleanup of old searches

## 📊 Interface Layout

```
┌─────────────────────────────────────────────────────────────┐
│ AI Theological Research Assistant                           │
├─────────────────────────────────────────────────────────────┤
│ [Search Box] [Research] | Sources: [Dropdown] | [History]   │
├─────────────────┬─────────────────┬─────────────────────────┤
│ Research Summary│ Sources & Citat.│ History / Source Select │
│                 │                 │                         │
│ • AI-generated  │ [1] Source Name │ • Saved Searches       │
│   summary with  │ Author, Location│ • Source Selection     │
│   clickable     │ Full chunk text │ • Quick Navigation     │
│   citations [1] │ Relevance info  │                         │
│                 │                 │                         │
│ • Search        │ [2] Source Name │                         │
│   strategy      │ ...             │                         │
│   transparency  │                 │                         │
└─────────────────┴─────────────────┴─────────────────────────┘
```

## 🎨 Design Philosophy

The enhanced UI follows **Logos Bible Software** design principles:

- **Information Density**: More content visible without scrolling
- **Professional Typography**: Clean, readable fonts at smaller sizes
- **Efficient Navigation**: Quick access to tools and history
- **Contextual Actions**: Save, reload, and navigate seamlessly
- **Metadata Integration**: Rich tooltips and structured information display

## 🔄 API Endpoints

### **POST /search**
Search with source filtering and query analysis
```json
{
  "query": "What does the Bible say about the deity of Christ?",
  "sources": ["orthodoxy_chesterton", "source_id_2"]
}
```

### **GET /api/sources**
Get available sources for selection
```json
[
  {
    "id": "orthodoxy_chesterton",
    "name": "Orthodoxy by G.K. Chesterton",
    "author": "Gilbert K. Chesterton",
    "chunkCount": 150
  }
]
```

## 🚀 Performance Optimizations

- **Efficient Rendering**: Minimal DOM updates
- **Smart Caching**: Local storage for history and preferences
- **Responsive Design**: Adapts to different screen sizes
- **Lazy Loading**: Only load what's visible

## 🐛 Troubleshooting

### **Common Issues**

1. **Dataset Not Found**
   - Ensure `theological_chunks_with_embeddings.jsonl` exists
   - Check file permissions and path

2. **API Key Issues**
   - Verify OpenAI API key in `.env` file
   - Check API key permissions and billing

3. **Search Not Working**
   - Check browser console for JavaScript errors
   - Verify Flask server is running on port 5001

4. **History Not Saving**
   - Check browser local storage permissions
   - Clear browser cache if corrupted

### **Debug Mode**
Run with debug output:
```bash
python enhanced_app.py --debug
```

## 📄 License

This enhanced research assistant is designed for theological research and educational use. Please ensure proper attribution when citing sources and summaries.

---

**Built for efficient theological research with modern AI and classical wisdom.**