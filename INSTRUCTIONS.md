# Enterprise RAG System - Simple Instructions

## 🚀 Quick Start (2 Steps)

### 1. Install & Run Server
```bash
pip install -r requirements.txt
cd C:\Users\sanat\CascadeProjects\windsurf-project\enterprise_rag
python -m uvicorn main:app --reload --port 8000
```

### 2. Open Frontend
Open `frontend/index.html` in your browser

**That's it!** The system will auto-ingest 4 sample documents on startup.

---

## 📊 System Architecture (Based on Your Diagram)

### **OFFLINE LAYER (Data Preparation)**
Runs in background - no user interaction

| Component | Technology Used | Purpose |
|-----------|----------------|----------|
| **Mock SharePoint** | `mock_sharepoint/api.py` | Simulates document source |
| **PII Detection & Redaction** | `staging/pii_detector.py` | Removes sensitive data (emails, phones, SSN) |
| **Audit Logging** | `staging/audit_logger.py` | Tracks all redactions |
| **Smart Chunking** | `processing/smart_chunker.py` | Splits docs into 400-600 token chunks |
| **Metadata Enrichment** | `processing/metadata_enricher.py` | Adds doc_id, client, sensitivity tags |
| **CRM Enrichment** | `ingestion/metadata_enricher.py` + `crm/mock_crm_api.py` | Enriches docs with CRM opportunity data (value, status, partner) |
| **Document Versioning** | `ingestion/document_versioning.py` | Tracks changes over time |

### **KNOWLEDGE GRAPH (3 Storage Systems)**
Stores processed chunks for fast retrieval

| Component | Technology Used | Purpose |
|-----------|----------------|----------|
| **Vector Store** | `storage/vector_store.py` + ChromaDB | Semantic similarity search |
| **Keyword Index** | `storage/keyword_index.py` + Whoosh | BM25 keyword matching |
| **Knowledge Graph** | `storage/knowledge_graph.py` + NetworkX | Entity relationships |

### **ONLINE ARCHITECTURE (Query Processing)**
Runs when user asks a question

| Component | Technology Used | Purpose |
|-----------|----------------|----------|
| **Hybrid Retriever** | `retrieval/hybrid_retriever.py` | Combines vector + keyword + graph (weighted 0.5 + 0.3 + 0.2) |
| **Evidence Builder** | `reasoning/evidence_builder.py` | Packages chunks with metadata |
| **Guardrails (Pre)** | `guardrails/guardrails.py` | Blocks bad queries before LLM |
| **RAG Pipeline** | `reasoning/openai_llm.py` | **Maker** → **Checker** → **Judge** (3-stage validation) |
| **Consultant Mode** | `reasoning/consultant_llm.py` | Strategic recommendations like a management consultant |
| **Agentic Layer** | `reasoning/agent.py` | Multi-step reasoning with ReAct + Web Search (5 iterations) |
| **Orchestrator** | `reasoning/agent_orchestrator.py` | Chooses RAG vs Agentic based on complexity |
| **Guardrails (Post)** | `guardrails/guardrails.py` | Checks LLM output for PII/toxicity |
| **FastAPI Server** | `main.py` | REST API endpoints |
| **Frontend** | `frontend/index.html` | KPMG Blue corporate UI |

### **LLM Integration**

| Component | Technology Used | Cost |
|-----------|----------------|------|
| **OpenAI GPT-4o** | `gpt-4o` via OpenAI API | $5/1M input tokens, $15/1M output tokens |
| **Embedding Service** | `utils/embeddings.py` + OpenAI | `text-embedding-3-small` (1536 dim) |
| **CRM API** | `crm/mock_crm_api.py` | 23 opportunities with values $500K-$10M |

---

## 🎯 Query Modes

| Mode | API Calls | Speed | Cost | Best For |
|------|-----------|-------|------|----------|
| **RAG** | 1 | Fast (1-2s) | $0.002-0.01 | Simple factual questions |
| **Consultant** | 1 | Fast (2-3s) | $0.01-0.02 | Strategic recommendations |
| **Agentic** | 5 | Slow (5-10s) | $0.01-0.05 | Complex queries + web search |
| **Auto** | 1-5 | Variable | $0.002-0.05 | System decides based on complexity |

---

## 🔌 API Endpoints

### Query Endpoints
```bash
POST /query          # RAG mode (fast)
POST /query/agentic  # Agentic mode (thorough)
POST /query/auto     # Auto mode (smart selection)
```

**Example Request:**
```json
{
  "query": "What is Flipkart's expansion strategy?",
  "top_k": 5
}
```

**Example Response:**
```json
{
  "status": "success",
  "mode": "AGENTIC",
  "answer": "Flipkart's expansion strategy for FY2024...",
  "sources": [...],
  "confidence": 0.92,
  "api_calls": 5,
  "cost_estimate": 0.0124,
  "input_tokens": 2495,
  "output_tokens": 1460,
  "total_tokens": 3955,
  "reasoning_steps": [...]
}
```

### Admin Endpoints
```bash
POST /ingest                  # Ingest all documents
GET /debug/audit              # View PII redaction logs
GET /debug/ingestion          # Ingestion stats
GET /debug/storage-stats      # Storage stats
GET /health                   # Health check
```

---

## ✨ Key Features

### 1. **Data Governance**
- PII automatically redacted at ingestion (emails, phones, SSN, credit cards)
- All redactions logged in `logs/audit_logs.jsonl`
- Chunks stored **already redacted** - LLM never sees original PII

### 2. **Hybrid Retrieval (3 Systems)**
- **Vector Search** (50% weight): Semantic similarity via embeddings
- **Keyword Search** (30% weight): BM25 ranking for exact matches
- **Knowledge Graph** (20% weight): Entity relationships

### 3. **3-Stage LLM Pipeline (RAG Mode)**
- **MAKER**: Generates answer using only retrieved evidence
- **CHECKER**: Validates answer is grounded in evidence
- **JUDGE**: Approves/rejects based on confidence threshold

### 4. **Agentic Reasoning (Agentic Mode)**
- **ReAct Pattern**: Think → Act → Observe → Repeat (5 iterations)
- **Tools**: Search vector, search keyword, search graph, retrieve entity, compare chunks
- **Synthesis**: Combines all observations into final answer

### 5. **Guardrails (2 Stages)**
- **Pre-Generation**: Blocks restricted keywords, detects PII in query
- **Post-Generation**: Checks LLM output for PII leakage, toxicity, hallucinations

### 6. **Real Cost Tracking**
- Tracks actual input/output tokens from Grok API
- Calculates real cost: $2 per 1M input tokens, $6 per 1M output tokens
- Displays token counts and cost in every response

---

## 📁 Sample Data

4 documents in `sample_documents/`:

| File | Client | Content | PII Included |
|------|--------|---------|-------------|
| `flipkart_proposal.txt` | Flipkart | Strategic expansion proposal FY2024 | ✅ Email, Phone |
| `hdfc_technology.txt` | HDFC Bank | Technology roadmap | ✅ Email, Phone |
| `airtel_operations.txt` | Airtel | Operations efficiency report | ✅ Email, Phone |
| `apollo_financial.txt` | Apollo Hospitals | Financial analysis | ✅ Email, Phone |

All PII is automatically redacted during ingestion.

---

## 📂 Project Structure

```
enterprise_rag/
├── main.py                          # FastAPI server (START HERE)
├── config.py                        # All configuration
├── requirements.txt                 # Dependencies
├── INSTRUCTIONS.md                  # This file
│
├── frontend/
│   └── index.html                   # KPMG Blue UI
│
├── sample_documents/                # 4 sample docs with PII
│
├── mock_sharepoint/
│   └── api.py                       # Document source simulation
│
├── staging/                         # OFFLINE: PII redaction
│   ├── pii_detector.py
│   ├── audit_logger.py
│   └── staging_pipeline.py
│
├── processing/                      # OFFLINE: Chunking
│   ├── smart_chunker.py
│   └── metadata_enricher.py
│
├── storage/                         # KNOWLEDGE GRAPH: 3 systems
│   ├── vector_store.py              # ChromaDB
│   ├── keyword_index.py             # Whoosh
│   └── knowledge_graph.py           # NetworkX
│
├── ingestion/                       # OFFLINE: Orchestration
│   ├── ingestion_service.py
│   ├── ingestion_registry.py
│   └── document_versioning.py
│
├── retrieval/                       # ONLINE: Search
│   └── hybrid_retriever.py
│
├── reasoning/                       # ONLINE: LLM processing
│   ├── grok_llm.py                  # RAG: Maker→Checker→Judge
│   ├── agent.py                     # Agentic: ReAct pattern
│   ├── agent_orchestrator.py        # Auto mode selector
│   └── evidence_builder.py
│
├── guardrails/                      # ONLINE: Safety
│   └── guardrails.py
│
├── utils/
│   └── embeddings.py
│
├── tests_and_demos/                 # All test/demo scripts
│   ├── check_storage.py
│   ├── demo*.py
│   ├── test*.py
│   └── ...
│
└── detailed_docs/                   # Detailed guides
    ├── AGENTIC_LAYER_GUIDE.md
    ├── CHAT_ORCHESTRATOR_EXPLAINED.md
    ├── CHUNK_LINKING_EXPLAINED.md
    └── ENTERPRISE_DEPLOYMENT_GUIDE.md
```

---

## ⚙️ Configuration

Edit `config.py` to customize:

```python
# Chunking (Smart Chunker)
PDF: 400-600 tokens
PPT: 200-400 tokens  
Word: 400-700 tokens

# Retrieval Weights
vector_weight = 0.5
keyword_weight = 0.3
graph_weight = 0.2

# Grok API
model = "grok-4-latest"
api_key = "xai-..."  # In main.py
input_cost = $2.00 per 1M tokens
output_cost = $6.00 per 1M tokens
```

---

## 🚀 Production Deployment

For production:

1. **Mock SharePoint** → Real SharePoint Graph API
2. **Hash Embeddings** → OpenAI `text-embedding-3-small` or Hugging Face
3. **ChromaDB** → Already using ChromaDB (production-ready)
4. **Grok API** → Already integrated (production-ready)
5. **File Logging** → Centralized logging (ELK, Datadog)
6. **No Auth** → Add API keys + RBAC
7. **Frontend** → Deploy to Netlify/Vercel
8. **Backend** → Deploy to AWS/Azure/GCP

---

## 🧪 Testing

All test/demo scripts moved to `tests_and_demos/`:

```bash
python tests_and_demos/demo.py                    # Full system demo-
python tests_and_demos/redaction_demo.py          # PII redaction demo
python tests_and_demos/test_chunk_linking.py      # Verifies chunks are properly linked across all 3 storage systems
python tests_and_demos/check_storage.py           # Current state of vector store, keyword index, knowledge graph
```

---

## 📊 Monitoring

```bash
# Health check
curl http://localhost:8000/health

# Ingestion stats
curl http://localhost:8000/debug/ingestion

# PII redaction audit logs
curl http://localhost:8000/debug/audit

# Storage stats (vector, keyword, graph)
curl http://localhost:8000/debug/storage-stats
```

---

## 🎯 Key Design Principles

1. **PII Redacted at Source** - Chunks stored already redacted, LLM never sees original PII
2. **Hybrid Retrieval** - 3 complementary systems (vector + keyword + graph)
3. **Evidence-Only Answers** - LLM restricted to retrieved chunks
4. **3-Stage Validation** - Maker → Checker → Judge prevents hallucinations
5. **Dual Guardrails** - Pre-generation (query check) + Post-generation (response check)
6. **Real Cost Tracking** - Actual token usage and Grok API pricing
7. **Agentic Reasoning** - Multi-step ReAct pattern for complex queries

---

## 🔧 Troubleshooting

**Server won't start:**
```bash
pip install --user chromadb
python -m uvicorn main:app --reload --port 8000
```

**0 chunks ingested:**
- Check `sample_documents/` folder exists with 4 .txt files
- Check logs in `logs/ingestion_registry.jsonl`

**500 errors on queries:**
- Check server logs for actual error
- Verify Grok API key in `main.py`

**Frontend not working:**
- Open `frontend/index.html` directly in browser (not via file://)
- Or use: `python -m http.server 3000` and visit `http://localhost:3000/frontend/`

---

## 📚 Documentation

- **This file**: Quick start and architecture
- **`detailed_docs/`**: In-depth guides on agentic layer, orchestrator, deployment
- **API Docs**: http://localhost:8000/docs (when server running)

---

**Version**: 2.0.0  
**Status**: Production-Ready with Grok Integration  
**Last Updated**: 2026-04-17



FAQ
Q1 How does Mock Sharepoint Work

Location: @/C:/Users/sanat/CascadeProjects/windsurf-project/enterprise_rag/mock_sharepoint/api.py:28-70

How it works:

python
def _generate_sample_documents(self):
    # Loads REAL files from disk (sample_documents/)
    documents = []
    for filename in os.listdir("./sample_documents"):
        if filename.endswith('.txt'):
            with open(f"./sample_documents/{filename}", 'r') as f:
                content = f.read()
            # Creates SharePointDocument object
            documents.append(SharePointDocument(...))
Answer:

✅ It creates 4 fixed .txt files from sample_documents/ folder
Files: flipkart_proposal.txt, hdfc_technology.txt, airtel_operations.txt, apollo_financial.txt
Each file has hardcoded PII (emails, phones) for demo purposes
On server startup, main.py calls ingestion_service.ingest_all_documents() which reads these files

Q2 How can I view Full flow from Ingestion to query

Step 1: Show Ingestion (Backend)
# Terminal 1: Start server (watch logs)
python -m uvicorn main:app --reload --port 8000

# You'll see:
# ✓ Startup ingestion: 4 documents, 16 chunks

Step 2: Show PII Redaction Logs
# Terminal 2: View audit logs
curl http://localhost:8000/debug/audit | python -m json.tool

# Shows:
# - Original text with PII
# - Redacted text with [REDACTED_EMAIL], [REDACTED_PHONE]
# - Timestamp, document_id

Step 3: Show Storage Stats
curl http://localhost:8000/debug/storage-stats | python -m json.tool

# Shows:
# - Vector store: 16 chunks
# - Keyword index: 16 chunks
# - Knowledge graph: X entities, Y relationships


Step 4: View Ingestion Registry
# View ingestion logs (API)
curl http://localhost:8000/debug/ingestion

# OR view raw log file:
cat logs/ingestion_registry.jsonl
# OR on Windows:
type logs\ingestion_registry.jsonl

Step 5: Show Frontend Query
Open frontend/index.html in browser
Select Agentic mode (to see reasoning steps)
Ask: "What is Flipkart's expansion strategy?"
Watch:
Retrieval: Searches vector + keyword + graph
Reasoning Steps: 5 iterations of Think→Act→Observe
Final Answer: Synthesized response
Cost: Real token usage and cost

Step 5: Show Guardrails in Action
# Try a query with PII
curl -X POST http://localhost:8000/query/agentic \
  -H "Content-Type: application/json" \
  -d '{"query": "Email me at test@example.com about Flipkart"}'

# Response will show:
# "status": "blocked"
# "reason": "Query contains PII"



Q3 Explain the Hybrid Retrieval & how search actually happens

Code Location: @/C:/Users/sanat/CascadeProjects/windsurf-project/enterprise_rag/retrieval/hybrid_retriever.py:43-80



How It Works:
Query: "What is Flipkart's expansion strategy?"



Vector Search:     ████████████████████ (finds "growth strategy", "market expansion")
Keyword Search:    ████████████ (finds exact "Flipkart", "expansion")
Graph Search:      ████████ (finds Flipkart entity + related chunks)
                   ↓
Combined Score:    ████████████████ (best of all 3)

Step 1: Three Parallel Searches
# 1. Vector Search (Semantic)
vector_results = vector_store.search(query_embedding)
# Returns: Chunks semantically similar to query
# Example: Finds "strategic expansion", "growth plan" even if exact words differ

# 2. Keyword Search (Exact Match)
keyword_results = keyword_index.search(query_text)
# Returns: Chunks with exact word matches "Flipkart", "expansion", "strategy"
# Uses BM25 ranking (like Google search)

# 3. Graph Search (Entity Relationships)
graph_results = knowledge_graph.search_by_entity("Flipkart")
# Returns: Chunks linked to "Flipkart" entity
# Example: Finds all chunks mentioning Flipkart + related entities

Step 2: Weighted Scoring
# Each chunk gets 3 scores:
chunk_score = (vector_score * 0.5) + (keyword_score * 0.3) + (graph_score * 0.2)

# Example:
# Chunk A: (0.9 * 0.5) + (0.7 * 0.3) + (0.8 * 0.2) = 0.82
# Chunk B: (0.6 * 0.5) + (0.9 * 0.3) + (0.5 * 0.2) = 0.67
# → Chunk A ranked higher

Why These Weights?

Vector (50%): Most important - captures meaning/intent
Keyword (30%): Important - ensures exact term matches
Graph (20%): Bonus - adds entity context

Q What is the Current Agentic Framework
Location: @/C:/Users/sanat/CascadeProjects/windsurf-project/enterprise_rag/reasoning/agent.py:95-161

def think_and_act(self, query: str):
    for iteration in range(5):  # Max 5 iterations
        
        # THINK: Ask Grok "what should I do next?"
        thought, action = self._think(query, context, iteration)
        # Grok returns: "I should search for Flipkart strategy"
        
        # ACT: Execute the tool
        observation = self._act(action)
        # Calls: hybrid_retriever.retrieve("Flipkart strategy")
        
        # OBSERVE: Get results
        context += observation.result
        # Adds: "Found 3 chunks about Flipkart expansion..."
        
        # Check if done
        if action.tool == ToolType.FINISH:
            break
    
    # SYNTHESIZE: Combine all observations
    final_answer = self._synthesize(query, context)
    return final_answer

    Custom class
    class ToolType(Enum):
    SEARCH_VECTOR = "search_vector"      # Calls hybrid_retriever
    SEARCH_KEYWORD = "search_keyword"    # Calls hybrid_retriever
    SEARCH_GRAPH = "search_graph"        # Calls knowledge_graph
    RETRIEVE_ENTITY = "retrieve_entity"  # Calls knowledge_graph
    COMPARE_CHUNKS = "compare_chunks"    # Custom logic
    FINISH = "finish"                    # Ends loop

    Comparison with Langchain
    Feature	Our Implementation	LangChain
ReAct Loop	Custom think_and_act()	AgentExecutor
Tools	Custom ToolType enum	@tool decorator
Prompts	Direct Grok API calls	PromptTemplate
Memory	Context string	ConversationBufferMemory
Cost	Real token tracking	Callbacks
Complexity	~300 lines	+5 dependencies