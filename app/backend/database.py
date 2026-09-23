"""
SQLite Database manager for document metadata, audit logs,
architecture entity cache, and human review workflow.
"""

import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from app.backend.config import SQLITE_DB_PATH


def get_db_connection():
    """Returns a SQLite connection with row factory enabled."""
    conn = sqlite3.connect(str(SQLITE_DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initializes the database schema if not already created."""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Documents table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                doc_id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                doc_title TEXT,
                version_label TEXT NOT NULL,
                upload_time TEXT NOT NULL,
                page_count INTEGER DEFAULT 0,
                chunk_count INTEGER DEFAULT 0,
                file_path TEXT NOT NULL,
                file_size_kb REAL DEFAULT 0.0
            )
        """)

        # Query Audit Log table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS queries_audit (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                engineer_name TEXT NOT NULL,
                doc_id TEXT NOT NULL,
                doc_name TEXT,
                question TEXT NOT NULL,
                retrieved_chunks_json TEXT,
                answer TEXT NOT NULL,
                latency_ms INTEGER DEFAULT 0,
                FOREIGN KEY (doc_id) REFERENCES documents (doc_id)
            )
        """)

        # Inconsistency Findings & Human Review Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS inconsistency_findings (
                id TEXT PRIMARY KEY,
                doc_id TEXT NOT NULL,
                issue_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                component_name TEXT,
                summary TEXT NOT NULL,
                description TEXT NOT NULL,
                remediation TEXT,
                evidence_page INTEGER,
                evidence_section TEXT,
                status TEXT NOT NULL DEFAULT 'AI_FLAGGED',
                reviewer_name TEXT,
                reviewer_notes TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (doc_id) REFERENCES documents (doc_id)
            )
        """)

        # Review Actions Audit Log
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS review_audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                finding_id TEXT NOT NULL,
                doc_id TEXT NOT NULL,
                old_status TEXT,
                new_status TEXT NOT NULL,
                reviewer_name TEXT NOT NULL,
                action_note TEXT,
                timestamp TEXT NOT NULL
            )
        """)

        # Extracted Architecture Entities Cache
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS extracted_entities (
                doc_id TEXT PRIMARY KEY,
                entities_json TEXT NOT NULL,
                extracted_at TEXT NOT NULL,
                FOREIGN KEY (doc_id) REFERENCES documents (doc_id)
            )
        """)

        conn.commit()


# Database helper operations

def save_document_metadata(
    doc_id: str,
    filename: str,
    doc_title: str,
    version_label: str,
    page_count: int,
    chunk_count: int,
    file_path: str,
    file_size_kb: float
) -> None:
    upload_time = datetime.utcnow().isoformat()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO documents 
            (doc_id, filename, doc_title, version_label, upload_time, page_count, chunk_count, file_path, file_size_kb)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (doc_id, filename, doc_title, version_label, upload_time, page_count, chunk_count, file_path, file_size_kb))
        conn.commit()


def get_all_documents() -> List[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM documents ORDER BY upload_time DESC")
        return [dict(row) for row in cursor.fetchall()]


def get_document_by_id(doc_id: str) -> Optional[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM documents WHERE doc_id = ?", (doc_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def log_query_audit(
    engineer_name: str,
    doc_id: str,
    doc_name: str,
    question: str,
    retrieved_chunks: List[Dict[str, Any]],
    answer: str,
    latency_ms: int
) -> int:
    timestamp = datetime.utcnow().isoformat()
    chunks_json = json.dumps(retrieved_chunks)
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO queries_audit 
            (timestamp, engineer_name, doc_id, doc_name, question, retrieved_chunks_json, answer, latency_ms)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (timestamp, engineer_name, doc_id, doc_name, question, chunks_json, answer, latency_ms))
        conn.commit()
        return cursor.lastrowid


def get_query_audit_logs(limit: int = 100) -> List[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM queries_audit ORDER BY id DESC LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        logs = []
        for row in rows:
            d = dict(row)
            try:
                d['retrieved_chunks'] = json.loads(d['retrieved_chunks_json'])
            except Exception:
                d['retrieved_chunks'] = []
            logs.append(d)
        return logs


def save_extracted_entities(doc_id: str, entities: Dict[str, Any]) -> None:
    now = datetime.utcnow().isoformat()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO extracted_entities (doc_id, entities_json, extracted_at)
            VALUES (?, ?, ?)
        """, (doc_id, json.dumps(entities), now))
        conn.commit()


def get_cached_extracted_entities(doc_id: str) -> Optional[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT entities_json FROM extracted_entities WHERE doc_id = ?", (doc_id,))
        row = cursor.fetchone()
        if row:
            return json.loads(row['entities_json'])
        return None


def save_inconsistency_findings(doc_id: str, findings: List[Dict[str, Any]]) -> None:
    now = datetime.utcnow().isoformat()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        for f in findings:
            finding_id = f.get("id") or f"{doc_id}_{f.get('issue_type')}_{f.get('component_name', 'sys')}"
            cursor.execute("""
                INSERT OR REPLACE INTO inconsistency_findings
                (id, doc_id, issue_type, severity, component_name, summary, description, remediation, evidence_page, evidence_section, status, reviewer_name, reviewer_notes, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, COALESCE((SELECT status FROM inconsistency_findings WHERE id = ?), 'AI_FLAGGED'), COALESCE((SELECT reviewer_name FROM inconsistency_findings WHERE id = ?), NULL), COALESCE((SELECT reviewer_notes FROM inconsistency_findings WHERE id = ?), NULL), ?, ?)
            """, (
                finding_id, doc_id, f.get("issue_type", "GENERAL"), f.get("severity", "MEDIUM"),
                f.get("component_name", "System"), f.get("summary", ""), f.get("description", ""),
                f.get("remediation", ""), f.get("evidence_page", 1), f.get("evidence_section", ""),
                finding_id, finding_id, finding_id, now, now
            ))
        conn.commit()


def get_inconsistency_findings(doc_id: str) -> List[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM inconsistency_findings WHERE doc_id = ? ORDER BY severity DESC, id ASC", (doc_id,))
        return [dict(row) for row in cursor.fetchall()]


def update_finding_review_status(
    finding_id: str,
    new_status: str,
    reviewer_name: str,
    reviewer_notes: Optional[str] = None
) -> bool:
    """
    Updates the status of a finding (AI_FLAGGED, UNDER_REVIEW, ACCEPTED, REJECTED)
    and logs the action in review_audit_log.
    """
    now = datetime.utcnow().isoformat()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM inconsistency_findings WHERE id = ?", (finding_id,))
        row = cursor.fetchone()
        if not row:
            return False
        
        old_status = row['status']
        doc_id = row['doc_id']

        cursor.execute("""
            UPDATE inconsistency_findings
            SET status = ?, reviewer_name = ?, reviewer_notes = ?, updated_at = ?
            WHERE id = ?
        """, (new_status, reviewer_name, reviewer_notes, now, finding_id))

        cursor.execute("""
            INSERT INTO review_audit_log (finding_id, doc_id, old_status, new_status, reviewer_name, action_note, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (finding_id, doc_id, old_status, new_status, reviewer_name, reviewer_notes, now))

        conn.commit()
        return True


def get_review_audit_logs(limit: int = 100) -> List[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM review_audit_log ORDER BY id DESC LIMIT ?", (limit,))
        return [dict(row) for row in cursor.fetchall()]
