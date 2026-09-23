# AUTOSAR HLD Document Analysis Assistant
### AI-Powered Architecture Ingestion, Grounded RAG, Inconsistency Detection & Revision Diffs

> **Tata Technologies | Automotive AI Platform Case Study Demo**  
> Built for automotive software architects and systems engineers to analyze High-Level Design (HLD) specifications, verify AUTOSAR Classic/Adaptive compliance, identify cross-component interface defects, and track architectural migrations with verified page-level citations.

---

## 🏎️ Key Capabilities

1. **Section-Aware Ingestion & OCR Fallback**:
   - Extracts page text, headers, and port tables using **PyMuPDF (`fitz`)**.
   - Automatic **Tesseract OCR fallback** for scanned/image-based pages.
   - Preserves exact source page and section provenance across all downstream steps.

2. **Grounded RAG Q&A with Explicit Citations**:
   - Semantic retrieval via **ChromaDB** and local **Sentence-Transformers (`all-MiniLM-L6-v2`)**.
   - Strict context-only grounding prompt ensuring answers cite exact sources (e.g. `[Source: p. 1, Section 2]`).
   - Collapsible inspection of raw context chunks and similarity scores.

3. **Architecture Entity Extraction**:
   - Structured decomposition of Software Components (SWCs), Interfaces, Port Prototypes (Require/Provide), Signals, Data Types, Periodicity, ASIL ratings, and Functional Flows.
   - Interactive data tables with column filtering and one-click **CSV export**.

4. **Deterministic Inconsistency Engine & Human-in-the-Loop Review**:
   - **Rule-based architectural validator**: Detects undefined component dependencies, orphaned require ports, and signal/data-type mismatches (`float32` vs `uint16`) deterministically.
   - **LLM Explanation**: Clarifies engineering safety impacts and recommends remediations.
   - **Human Governance**: Status workflow (`AI_FLAGGED`, `UNDER_REVIEW`, `ACCEPTED`, `REJECTED`) with reviewer notes and audit logging. *Explicitly emphasizes that AI findings require human engineering sign-off.*

5. **Document Revision Comparison (Diff Engine)**:
   - Compares baseline HLD (V1.0) against revised HLD (V2.0).
   - Highlights Added Components (e.g. `LaneKeepAssistSWC`), Modified Data Types, and Interface updates.

6. **Topological Graph & Impact Analysis**:
   - In-memory **NetworkX** directed architecture graph.
   - Calculates upstream dependencies and downstream **blast radius** when modifying a component or signal.
   - Generates ready-to-run **Neo4j Cypher** export scripts.

7. **Full Audit Trail & Governance**:
   - Logs every query, timestamp, engineer identity, retrieved chunk, and generated answer in local **SQLite**.

---

## 🛠️ Technology Stack

| Layer | Technology |
|---|---|
| **Backend Framework** | Python 3.11+, FastAPI, Uvicorn |
| **Frontend UI** | Streamlit (Custom automotive dark/light styling) |
| **Vector Database** | ChromaDB (Local, persistent disk storage) |
| **Embeddings** | Sentence-Transformers (`all-MiniLM-L6-v2`, local, no API cost) |
| **PDF Extraction** | PyMuPDF (`fitz`) + Tesseract OCR fallback |
| **Audit & Cache Storage** | SQLite (`autosar_analysis.db`) |
| **Graph Analysis** | NetworkX + Neo4j Cypher Export |
| **LLM Service** | Abstract provider interface supporting **OpenAI**, **Anthropic**, **Local/Ollama**, and **Mock Fallback** |

---

## 🚀 Quick Start Guide

### 1. Clone & Setup Virtual Environment
```bash
# Clone repository
git clone https://github.com/DotHrishi/unified-code-review.git
cd AUTOSAR-HLD-Analyzer

# Create and activate virtual environment
python -m venv venv

# On Windows:
.\venv\Scripts\activate

# On Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables (Optional)
Copy `.env.example` to `.env`. By default, `LLM_PROVIDER=mock` is enabled for instant 100% offline testing without external API keys:
```bash
cp .env.example .env
```
To use live models, set your API key in `.env`:
```ini
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```

### 3. Generate Sample AUTOSAR HLD PDFs
```bash
python app/sample_docs/generate_sample_hld.py
```
This generates:
- `sample_autosar_hld_v1.pdf`: Baseline with intentional architectural flaws.
- `sample_autosar_hld_v2.pdf`: Revision 2.0 with fixes and ADAS components.

---

## 🏃 Running the Application

### Option A: Run Pipeline Verification Test
Verify all 10 layers in the terminal:
```bash
python test_pipeline.py
```

### Option B: Run Full Interactive Web Application

**Terminal 1 — Start FastAPI Backend:**
```bash
uvicorn app.backend.main:app --host 127.0.0.1 --port 8000 --reload
```
API Documentation will be available at: `http://127.0.0.1:8000/docs`

**Terminal 2 — Start Streamlit Frontend:**
```bash
streamlit run app/frontend/app.py
```
Open your browser at: `http://localhost:8501`

---

## 🎬 5-Minute Live Presentation Runbook

| Step | Action in UI | What to Highlight |
|---|---|---|
| **1. Ingest Baseline** | In **Tab 1**, click **"Load Baseline HLD V1.0"**. | Show fast PyMuPDF extraction, chunking, and ChromaDB indexing. |
| **2. Grounded Q&A** | In **Tab 2**, click sample query: *"What interfaces does BrakeControlSWC expose?"* | Show grounded answer citing `[Source: p. 1, Section 2]` with expandable evidence chunks. |
| **3. Entity Explorer** | In **Tab 3**, filter by `BrakeControlSWC` and click **"Export Entities to CSV"**. | Show structured SWCs, Ports, Signals, and Data Types with page provenance. |
| **4. Inconsistencies** | In **Tab 4**, observe the 3 flagged architectural issues. Update a finding status to `ACCEPTED` with an engineering note. | Show deterministic schema validation (missing `SteeringAngleSensorSWC`, data type mismatch `float32` vs `uint16`) and human review governance. |
| **5. Version Diff** | In **Tab 1**, load **HLD V2.0**. Go to **Tab 5** and click **"Compare Versions"**. | Show instant diff: `LaneKeepAssistSWC` added, `TransmissionControlSWC` data type corrected. |
| **6. Blast Radius** | In **Tab 6**, select `SteeringAngleSensorSWC` and click **"Calculate Blast Radius Impact"**. | Show graph traversal identifying downstream consumers and copyable Neo4j Cypher script. |
| **7. Audit Trail** | In **Tab 7**, inspect query logs and human reviewer actions. | Emphasize enterprise compliance and auditability in SQLite. |

---

## 📂 Project Structure

```
AUTOSAR-HLD-Analyzer/
├── app/
│   ├── backend/
│   │   ├── config.py                # Environment & directory configs
│   │   ├── database.py              # SQLite schema: docs, audits, findings, reviews
│   │   ├── pdf_parser.py            # PyMuPDF + Tesseract OCR fallback
│   │   ├── chunker.py               # Section & page-aware chunker
│   │   ├── vector_store.py          # ChromaDB + sentence-transformers (all-MiniLM-L6-v2)
│   │   ├── llm_service.py           # Unified LLM provider (OpenAI, Anthropic, Local, Mock)
│   │   ├── rag_engine.py            # Grounded RAG with strict citations
│   │   ├── entity_extractor.py      # SWCs, ports, signals, flows extractor
│   │   ├── inconsistency_checker.py # Deterministic rule engine + human review
│   │   ├── document_comparator.py   # Semantic & structural diffs (V1 vs V2)
│   │   ├── graph_analyzer.py        # NetworkX graph + Neo4j Cypher export
│   │   └── main.py                  # FastAPI REST endpoints
│   ├── frontend/
│   │   ├── api_client.py            # REST client for backend
│   │   └── app.py                   # Streamlit UI workbench
│   ├── data/                        # Persistent ChromaDB collections and SQLite database
│   └── sample_docs/
│       ├── generate_sample_hld.py   # Sample HLD PDF generator
│       ├── sample_autosar_hld_v1.pdf # Baseline PDF
│       └── sample_autosar_hld_v2.pdf # Revision PDF
├── test_pipeline.py                 # End-to-end verification script
├── Dockerfile                       # Multi-service container specification
├── requirements.txt                 # Dependencies
├── .env.example                     # Environment template
└── README.md                        # Documentation & Runbook
```

---

## 🛡️ License & Disclaimers
This prototype is developed for technical demonstration purposes in automotive software architecture analysis. Fictional sample components and ports comply with AUTOSAR 4.4 and ISO 26262 conceptual patterns.
#   A U T O S A R - H L D - A n a l y z e r  
 