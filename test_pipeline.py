"""
End-to-End Pipeline Verification Script for AUTOSAR HLD Document Analysis Assistant.
Tests all backend modules in sequence without requiring live network APIs.
"""

import os
import sys
from pathlib import Path

# Ensure root directory is on PYTHONPATH
ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))

from app.backend.database import (
    init_db,
    save_document_metadata,
    get_all_documents,
    get_document_by_id,
    update_finding_review_status,
    get_query_audit_logs,
    get_review_audit_logs
)
from app.backend.pdf_parser import extract_text_from_pdf
from app.backend.chunker import chunk_document
from app.backend.vector_store import index_chunks, query_relevant_chunks
from app.backend.rag_engine import perform_rag_query
from app.backend.entity_extractor import extract_architecture_entities
from app.backend.inconsistency_checker import run_inconsistency_analysis
from app.backend.document_comparator import compare_hld_revisions
from app.backend.graph_analyzer import analyze_component_impact, generate_cypher_export


def run_verification():
    print("=" * 70)
    print("[START] AUTOSAR HLD ANALYZER PIPELINE VERIFICATION")
    print("=" * 70)

    # 1. Initialize SQLite Database
    print("\n[Step 1] Initializing SQLite Database...")
    init_db()
    print("[OK] SQLite database initialized successfully.")

    # 2. Check Sample PDFs
    v1_pdf = ROOT_DIR / "app/sample_docs/sample_autosar_hld_v1.pdf"
    v2_pdf = ROOT_DIR / "app/sample_docs/sample_autosar_hld_v2.pdf"
    
    assert v1_pdf.exists(), f"Missing {v1_pdf}"
    assert v2_pdf.exists(), f"Missing {v2_pdf}"
    print("[OK] Sample HLD PDFs (V1 Baseline and V2 Revision) verified.")

    # 3. Test PDF Extraction & Chunking for V1
    print("\n[Step 2] Testing PDF Parser & Section-Aware Chunker (V1)...")
    parsed_v1 = extract_text_from_pdf(str(v1_pdf))
    print(f"   Pages Extracted: {parsed_v1['page_count']}, Total Characters: {parsed_v1['total_chars']}")
    assert parsed_v1["page_count"] >= 3, "V1 PDF should have at least 3 pages"

    doc1_id = "doc_test_v1_baseline"
    chunks_v1 = chunk_document(doc_id=doc1_id, parsed_pdf=parsed_v1)
    print(f"   Generated Chunks: {len(chunks_v1)}")
    assert len(chunks_v1) >= 3, "Should have created multiple chunks with provenance"

    # Save V1 metadata to DB
    save_document_metadata(
        doc_id=doc1_id,
        filename="sample_autosar_hld_v1.pdf",
        doc_title="Powertrain & Chassis Control Domain (V1)",
        version_label="1.0",
        page_count=parsed_v1["page_count"],
        chunk_count=len(chunks_v1),
        file_path=str(v1_pdf),
        file_size_kb=round(os.path.getsize(v1_pdf)/1024, 2)
    )
    print("[OK] V1 Document metadata saved in SQLite.")

    # 4. Test ChromaDB Vector Indexing & Semantic Retrieval
    print("\n[Step 3] Testing ChromaDB Vector Store Indexing & Retrieval...")
    indexed_count = index_chunks(doc_id=doc1_id, chunks=chunks_v1)
    print(f"   Indexed {indexed_count} chunks in ChromaDB collection 'doc_{doc1_id}'")

    retrieved = query_relevant_chunks(doc_id=doc1_id, query_text="What interfaces does BrakeControlSWC expose?", top_k=3)
    print(f"   Retrieved {len(retrieved)} relevant chunks. Top chunk from Page {retrieved[0]['page_number']}")
    assert len(retrieved) > 0, "Retrieval returned 0 chunks"
    print("[OK] Semantic vector retrieval verified.")

    # 5. Test Grounded RAG Query
    print("\n[Step 4] Testing Grounded RAG Q&A Engine with Page Citations...")
    rag_result = perform_rag_query(
        doc_id=doc1_id,
        question="What interfaces does BrakeControlSWC expose?",
        engineer_name="Lead Systems Architect",
        top_k=3
    )
    print("   RAG Answer Generated:")
    print("   " + "\n   ".join(rag_result["answer"].split("\n")[:4]) + "...")
    print(f"   Citations: {rag_result['citations']}")
    print(f"   Latency: {rag_result['latency_ms']} ms")
    assert len(rag_result["answer"]) > 20, "RAG answer is empty"
    print("[OK] Grounded RAG answering with page citations verified.")

    # 6. Test Architecture Entity Extractor
    print("\n[Step 5] Testing Architecture Entity Extractor...")
    entities = extract_architecture_entities(doc1_id, force_refresh=True)
    comps = entities.get("components", [])
    flat = entities.get("flattened_table", [])
    print(f"   Extracted {len(comps)} Software Components and {len(flat)} Port/Signal rows.")
    for c in comps:
        print(f"   - {c['name']} ({c['type']}, {c['safety_level']}, {len(c.get('ports', []))} ports, Page {c['page']})")
    assert len(comps) >= 4, "Should have extracted at least 4 SWCs"
    print("[OK] Architecture entity extraction & provenance verified.")

    # 7. Test Deterministic Inconsistency Checker
    print("\n[Step 6] Testing Deterministic Inconsistency Detection Engine...")
    findings = run_inconsistency_analysis(doc1_id, force_refresh=True)
    print(f"   Detected {len(findings)} architectural defects in V1:")
    for f in findings:
        print(f"   [{f['severity']}] {f['issue_type']} in {f['component_name']} (Page {f['evidence_page']}): {f['summary']}")
    assert len(findings) >= 2, "Should have flagged known intentional inconsistencies"
    print("[OK] Deterministic inconsistency detection verified.")

    # 8. Test Human Review Workflow
    print("\n[Step 7] Testing Human-in-the-Loop Review Status Transition...")
    target_finding_id = findings[0]["id"]
    success = update_finding_review_status(
        finding_id=target_finding_id,
        new_status="ACCEPTED",
        reviewer_name="Hrishikesh Kali",
        reviewer_notes="Confirmed requirement defect: SteeringAngleSensorSWC must be declared."
    )
    assert success, "Failed to update review status"
    review_logs = get_review_audit_logs(limit=5)
    print(f"   Review audit recorded: {review_logs[0]['finding_id']} -> {review_logs[0]['new_status']} by {review_logs[0]['reviewer_name']}")
    print("[OK] Human review workflow & audit log verified.")

    # 9. Ingest V2 Document and Test Revision Comparison
    print("\n[Step 8] Ingesting V2 PDF and Testing Revision Comparator...")
    parsed_v2 = extract_text_from_pdf(str(v2_pdf))
    doc2_id = "doc_test_v2_revision"
    chunks_v2 = chunk_document(doc_id=doc2_id, parsed_pdf=parsed_v2)
    save_document_metadata(
        doc_id=doc2_id,
        filename="sample_autosar_hld_v2.pdf",
        doc_title="Powertrain & Chassis Control Domain (V2 Revision)",
        version_label="2.0",
        page_count=parsed_v2["page_count"],
        chunk_count=len(chunks_v2),
        file_path=str(v2_pdf),
        file_size_kb=round(os.path.getsize(v2_pdf)/1024, 2)
    )
    index_chunks(doc_id=doc2_id, chunks=chunks_v2)
    extract_architecture_entities(doc2_id, force_refresh=True)

    diff = compare_hld_revisions(doc_id_v1=doc1_id, doc_id_v2=doc2_id)
    print(f"   Comparison Summary: {diff['summary']}")
    print(f"   Added Components: {[c['name'] for c in diff['added_components']]}")
    print(f"   Modified Components: {[c['name'] for c in diff['modified_components']]}")
    assert len(diff["added_components"]) >= 1, "V2 should have added components like LaneKeepAssistSWC"
    print("[OK] Revision comparator verified.")

    # 10. Test Graph Dependency & Blast Radius Impact Analysis
    print("\n[Step 9] Testing Graph Topology & Impact Traversal...")
    impact = analyze_component_impact(doc_id=doc2_id, target_component="SteeringAngleSensorSWC")
    print(f"   Target: {impact['target_component']}")
    print(f"   Downstream Blast Radius: {impact['downstream_impact']}")
    cypher = generate_cypher_export(doc_id=doc2_id)
    print(f"   Generated Cypher Script ({len(cypher.splitlines())} lines).")
    print("[OK] Architecture graph & impact analysis verified.")

    # 11. Test Query Audit Logs
    print("\n[Step 10] Testing Query Audit History...")
    q_logs = get_query_audit_logs(limit=5)
    print(f"   Logged Queries count: {len(q_logs)}. Latest: '{q_logs[0]['question']}' (Latency: {q_logs[0]['latency_ms']}ms)")
    assert len(q_logs) >= 1, "Audit log should have at least 1 entry"
    print("[OK] Governance & Query audit verified.")

    print("\n" + "=" * 70)
    print("[SUCCESS] ALL 10 PIPELINE VERIFICATION TESTS PASSED SUCCESSFULLY!")
    print("=" * 70)


if __name__ == "__main__":
    run_verification()
