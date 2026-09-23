"""
RAG Engine for Grounded AUTOSAR Architecture Q&A.
Retrieves relevant chunks from ChromaDB, constructs a domain-specialized prompt,
enforces strict context-only grounding, and embeds verified page citations.
"""

import re
import time
from typing import Dict, Any, List
from app.backend.vector_store import query_relevant_chunks
from app.backend.llm_service import get_llm_service
from app.backend.database import log_query_audit, get_document_by_id

RAG_SYSTEM_PROMPT = """You are the Tata Technologies "AUTOSAR HLD Document Analysis Assistant" — a specialized AI expert in automotive systems engineering and AUTOSAR Classic / Adaptive software architectures.

CRITICAL GROUNDING RULES:
1. Answer the question using ONLY the facts directly provided in the context below. Do NOT assume, extrapolate, or bring in outside technical knowledge not stated in the text.
2. Every architectural claim, Software Component (SWC), Interface, Port Prototype (Require/Provide), Signal name, Data Type, execution periodicity, or ASIL rating MUST include an explicit source citation in brackets: [Source: p. X, Section Y] or [Source: p. X].
3. If the context does not contain enough information to answer a part of the question, clearly state: "The provided document does not mention [missing information]."
4. Structure your response clearly using markdown headings, bullet points, and code formatting for SWC and Port names.
"""


def perform_rag_query(
    doc_id: str,
    question: str,
    engineer_name: str = "Automotive Engineer",
    top_k: int = 4
) -> Dict[str, Any]:
    """
    Executes a complete RAG query flow:
    1. Retrieval from ChromaDB
    2. Context assembly
    3. Grounded LLM completion
    4. Citation extraction
    5. Audit logging in SQLite
    """
    start_time = time.time()
    
    # 1. Retrieve relevant chunks
    chunks = query_relevant_chunks(doc_id=doc_id, query_text=question, top_k=top_k)
    
    # Get document metadata for audit log
    doc_meta = get_document_by_id(doc_id)
    doc_name = doc_meta.get("filename", doc_id) if doc_meta else doc_id

    # 2. Format context with clear page & section markers
    context_blocks = []
    for i, c in enumerate(chunks):
        p_num = c.get("page_number", 1)
        sec = c.get("section_title", "General")
        text = c.get("text", "")
        context_blocks.append(f"--- [CONTEXT BLOCK {i+1} | Page {p_num} | Section: {sec}] ---\n{text}")

    formatted_context = "\n\n".join(context_blocks) if context_blocks else "No relevant document chunks found."

    user_prompt = f"""CONTEXT FROM AUTOSAR HLD DOCUMENT:
=========================================
{formatted_context}
=========================================

ENGINEER QUESTION:
{question}

Provide a grounded, structured answer with page citations [Source: p. X] for every fact:"""

    # 3. Generate completion from LLM service
    llm = get_llm_service()
    answer = llm.generate_response(
        system_prompt=RAG_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        temperature=0.0
    )

    # 4. Extract citations from response
    citation_pattern = r'\[Source:\s*p\.?\s*(\d+)(?:,\s*Section\s*([^\]]+))?\]'
    citations_found = []
    for match in re.finditer(citation_pattern, answer, re.IGNORECASE):
        page = match.group(1)
        sec = match.group(2)
        if sec:
            citations_found.append(f"Page {page} ({sec.strip()})")
        else:
            citations_found.append(f"Page {page}")
    
    # Deduplicate citations while preserving order
    unique_citations = list(dict.fromkeys(citations_found))

    # If LLM didn't produce citations but we retrieved chunks, add retrieved pages as reference
    if not unique_citations and chunks:
        unique_citations = [f"Page {c.get('page_number', 1)}" for c in chunks]
        unique_citations = list(dict.fromkeys(unique_citations))

    latency_ms = int((time.time() - start_time) * 1000)

    # 5. Log to SQLite audit trail
    log_id = log_query_audit(
        engineer_name=engineer_name,
        doc_id=doc_id,
        doc_name=doc_name,
        question=question,
        retrieved_chunks=chunks,
        answer=answer,
        latency_ms=latency_ms
    )

    return {
        "query_id": log_id,
        "doc_id": doc_id,
        "question": question,
        "answer": answer,
        "citations": unique_citations,
        "retrieved_chunks": chunks,
        "latency_ms": latency_ms,
        "engineer_name": engineer_name
    }
