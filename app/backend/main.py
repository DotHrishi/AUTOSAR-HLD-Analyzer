"""
FastAPI REST Application for AUTOSAR HLD Document Analysis Assistant.
Exposes endpoints for PDF Ingestion, RAG Q&A, Entity Extraction,
Inconsistency Detection with Human Review, Document Revision Comparison,
and Graph Dependency Impact Analysis.
"""

import os
import sys
import json
import shutil
import uuid
from pathlib import Path
from typing import Optional, List, Dict, Any

# Ensure project root is in sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Query, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.backend.config import UPLOAD_DIR, LLM_PROVIDER
from app.backend.database import (
    init_db,
    save_document_metadata,
    get_all_documents,
    get_document_by_id,
    get_query_audit_logs,
    get_review_audit_logs,
    update_finding_review_status
)
from app.backend.pdf_parser import extract_text_from_pdf
from app.backend.chunker import chunk_document
from app.backend.vector_store import index_chunks
from app.backend.rag_engine import perform_rag_query
from app.backend.entity_extractor import extract_architecture_entities
from app.backend.inconsistency_checker import run_inconsistency_analysis
from app.backend.document_comparator import compare_hld_revisions
from app.backend.graph_analyzer import analyze_component_impact, generate_cypher_export

# Initialize Database on startup
init_db()

app = FastAPI(
    title="AUTOSAR HLD Document Analysis Assistant API",
    description="Automotive High-Level Design RAG, Architecture Extraction, Inconsistency Engine & Revision Comparison",
    version="1.0.0"
)

# ---------------------------------------------------------------------------
# CORS — restrict to configured allowed origins (defaults to Streamlit port)
# ---------------------------------------------------------------------------
_raw_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:8501,http://127.0.0.1:8501")
ALLOWED_ORIGINS: List[str] = [o.strip() for o in _raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# API Key Authentication — reads AUTOSAR_API_KEY from environment.
# When the variable is unset or empty the middleware is a no-op so local
# development works out of the box without configuration.
# ---------------------------------------------------------------------------
_API_KEY = os.getenv("AUTOSAR_API_KEY", "").strip()
_UNPROTECTED_PATHS = {"/api/health", "/docs", "/openapi.json", "/redoc"}


@app.middleware("http")
async def api_key_middleware(request: Request, call_next):
    """Enforces API key auth when AUTOSAR_API_KEY is configured."""
    if _API_KEY and request.url.path not in _UNPROTECTED_PATHS:
        provided_key = (
            request.headers.get("X-API-Key")
            or request.query_params.get("api_key")
        )
        if provided_key != _API_KEY:
            return JSONResponse(
                status_code=401,
                content={"detail": "Unauthorized: invalid or missing API key. "
                                   "Pass X-API-Key header or api_key query param."}
            )
    return await call_next(request)


# Request & Response Models
class QueryRequest(BaseModel):
    doc_id: str
    question: str
    engineer_name: str = "Automotive Engineer"
    top_k: int = Field(default=4, ge=1, le=10)


class ReviewActionRequest(BaseModel):
    status: str = Field(..., description="AI_FLAGGED | UNDER_REVIEW | ACCEPTED | REJECTED")
    reviewer_name: str
    reviewer_notes: Optional[str] = None


class CompareRequest(BaseModel):
    doc_id_v1: str
    doc_id_v2: str


# Endpoints

@app.get("/api/health")
def health_check():
    """Health check and active LLM configuration status."""
    return {
        "status": "healthy",
        "service": "AUTOSAR HLD Document Analysis Assistant",
        "llm_provider": LLM_PROVIDER
    }


@app.post("/api/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    version_label: str = Form("1.0"),
    doc_title: Optional[str] = Form(None)
):
    """
    Ingests an AUTOSAR HLD PDF document:
    1. Saves file to local storage.
    2. Parses page text with PyMuPDF (+ Tesseract OCR fallback).
    3. Chunks text with page and section provenance.
    4. Indexes chunks into ChromaDB.
    5. Runs initial entity extraction and deterministic inconsistency check.
    6. Stores metadata in SQLite.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    doc_id = f"doc_{uuid.uuid4().hex[:10]}"
    file_path = UPLOAD_DIR / f"{doc_id}_{file.filename}"

    # Save PDF locally
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    file_size_kb = round(os.path.getsize(file_path) / 1024, 2)

    # 1. Parse PDF
    try:
        parsed_pdf = extract_text_from_pdf(str(file_path))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF parsing error: {str(e)}")

    page_count = parsed_pdf.get("page_count", 0)

    # 2. Chunk text with page provenance
    chunks = chunk_document(doc_id=doc_id, parsed_pdf=parsed_pdf)
    chunk_count = len(chunks)

    # 3. Vector indexing in ChromaDB
    try:
        index_chunks(doc_id=doc_id, chunks=chunks)
    except Exception as e:
        print(f"[API] Warning during Chroma indexing: {e}")

    # 4. Save metadata in SQLite
    title = doc_title or file.filename.replace(".pdf", "")
    save_document_metadata(
        doc_id=doc_id,
        filename=file.filename,
        doc_title=title,
        version_label=version_label,
        page_count=page_count,
        chunk_count=chunk_count,
        file_path=str(file_path),
        file_size_kb=file_size_kb
    )

    # 5. Extract initial entities & run inconsistency checks
    try:
        extract_architecture_entities(doc_id)
        run_inconsistency_analysis(doc_id)
    except Exception as e:
        print(f"[API] Warning during initial analysis: {e}")

    return {
        "message": "Document ingested and indexed successfully",
        "doc_id": doc_id,
        "filename": file.filename,
        "doc_title": title,
        "version_label": version_label,
        "page_count": page_count,
        "chunk_count": chunk_count,
        "file_size_kb": file_size_kb
    }


@app.get("/api/documents")
def list_documents():
    """Lists all ingested documents in the system."""
    return get_all_documents()


@app.get("/api/documents/{doc_id}")
def get_document(doc_id: str):
    """Retrieves metadata for a specific document."""
    doc = get_document_by_id(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@app.post("/api/query")
def query_rag(payload: QueryRequest):
    """
    Executes a grounded RAG query over the document,
    returning structured response with verified source citations.
    """
    try:
        result = perform_rag_query(
            doc_id=payload.doc_id,
            question=payload.question,
            engineer_name=payload.engineer_name,
            top_k=payload.top_k
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


@app.get("/api/entities/{doc_id}")
def get_entities(doc_id: str, force_refresh: bool = Query(False)):
    """Extracts or retrieves cached architecture entities (SWCs, Ports, Signals, Flows)."""
    try:
        return extract_architecture_entities(doc_id, force_refresh=force_refresh)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Entity extraction failed: {str(e)}")


@app.get("/api/inconsistencies/{doc_id}")
def get_inconsistencies(doc_id: str, force_refresh: bool = Query(False)):
    """Runs deterministic inconsistency detection and returns flagged issues with review statuses."""
    try:
        return run_inconsistency_analysis(doc_id, force_refresh=force_refresh)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Inconsistency analysis failed: {str(e)}")


@app.post("/api/inconsistencies/{finding_id}/review")
def review_inconsistency_finding(finding_id: str, payload: ReviewActionRequest):
    """Updates human review status (AI_FLAGGED, UNDER_REVIEW, ACCEPTED, REJECTED) with audit logging."""
    valid_statuses = ["AI_FLAGGED", "UNDER_REVIEW", "ACCEPTED", "REJECTED"]
    if payload.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Status must be one of {valid_statuses}")

    success = update_finding_review_status(
        finding_id=finding_id,
        new_status=payload.status,
        reviewer_name=payload.reviewer_name,
        reviewer_notes=payload.reviewer_notes
    )

    if not success:
        raise HTTPException(status_code=404, detail="Finding ID not found")

    return {
        "message": "Review action recorded successfully",
        "finding_id": finding_id,
        "new_status": payload.status,
        "reviewer_name": payload.reviewer_name
    }


@app.post("/api/documents/compare")
def compare_documents(payload: CompareRequest):
    """Compares two document revisions (e.g. V1 vs V2) and outputs architectural diff."""
    try:
        return compare_hld_revisions(doc_id_v1=payload.doc_id_v1, doc_id_v2=payload.doc_id_v2)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Comparison failed: {str(e)}")


@app.get("/api/graph/impact/{doc_id}")
def get_component_impact(doc_id: str, component_name: str = Query(...)):
    """Performs topological dependency and downstream blast radius impact analysis."""
    try:
        return analyze_component_impact(doc_id=doc_id, target_component=component_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Impact analysis failed: {str(e)}")


@app.get("/api/graph/cypher/{doc_id}")
def get_cypher_export(doc_id: str):
    """Generates Neo4j Cypher statements for exporting the architecture graph."""
    try:
        cypher_code = generate_cypher_export(doc_id=doc_id)
        return {"doc_id": doc_id, "cypher_script": cypher_code}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cypher generation failed: {str(e)}")


@app.get("/api/audit/queries")
def get_audit_queries(limit: int = Query(100, ge=1, le=500)):
    """Fetches the query audit trail."""
    return get_query_audit_logs(limit=limit)


@app.get("/api/audit/reviews")
def get_audit_reviews(limit: int = Query(100, ge=1, le=500)):
    """Fetches the human review actions audit trail."""
    return get_review_audit_logs(limit=limit)


# ---------------------------------------------------------------------------
# Structured Export Endpoints — JSON and serialised formats for downstream
# integration (traceability tools, safety case toolchains, CI pipelines).
# ---------------------------------------------------------------------------

@app.get("/api/export/entities/{doc_id}")
def export_entities_json(doc_id: str, force_refresh: bool = Query(False)):
    """
    Exports all extracted architecture entities for a document as structured JSON.
    Suitable for import into AUTOSAR toolchains, safety-case managers, or CI pipelines.
    """
    try:
        data = extract_architecture_entities(doc_id, force_refresh=force_refresh)
        doc = get_document_by_id(doc_id)
        return {
            "export_format": "autosar_hld_entities_v1",
            "doc_id": doc_id,
            "doc_title": doc.get("doc_title") if doc else doc_id,
            "version_label": doc.get("version_label") if doc else "unknown",
            "component_count": len(data.get("components", [])),
            "components": data.get("components", []),
            "functional_flows": data.get("functional_flows", []),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Entity export failed: {str(e)}")


@app.get("/api/export/inconsistencies/{doc_id}")
def export_inconsistencies_json(doc_id: str):
    """
    Exports all inconsistency findings with review status as structured JSON.
    Suitable for import into issue trackers, FMEA tools, or audit systems.
    """
    try:
        findings = run_inconsistency_analysis(doc_id)
        doc = get_document_by_id(doc_id)
        critical = [f for f in findings if f.get("severity") == "CRITICAL"]
        high = [f for f in findings if f.get("severity") == "HIGH"]
        return {
            "export_format": "autosar_hld_inconsistencies_v1",
            "doc_id": doc_id,
            "doc_title": doc.get("doc_title") if doc else doc_id,
            "version_label": doc.get("version_label") if doc else "unknown",
            "summary": {
                "total": len(findings),
                "critical": len(critical),
                "high": len(high),
                "pending_review": len([f for f in findings if f.get("status") == "AI_FLAGGED"]),
                "accepted": len([f for f in findings if f.get("status") == "ACCEPTED"]),
                "rejected": len([f for f in findings if f.get("status") == "REJECTED"]),
            },
            "findings": findings,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Inconsistency export failed: {str(e)}")
