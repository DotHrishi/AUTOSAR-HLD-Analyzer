"""
API Client for interacting with the FastAPI Backend from Streamlit.
"""

import os
from typing import Dict, Any, List, Optional
import requests
from dotenv import load_dotenv

load_dotenv()
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")


class APIClient:
    def __init__(self, base_url: str = BACKEND_URL):
        self.base_url = base_url.rstrip('/')

    def check_health(self) -> Dict[str, Any]:
        try:
            resp = requests.get(f"{self.base_url}/api/health", timeout=5)
            return resp.json() if resp.status_code == 200 else {"status": "unreachable"}
        except Exception as e:
            return {"status": "unreachable", "error": str(e)}

    def list_documents(self) -> List[Dict[str, Any]]:
        try:
            resp = requests.get(f"{self.base_url}/api/documents", timeout=10)
            return resp.json() if resp.status_code == 200 else []
        except Exception:
            return []

    def upload_document(self, file_bytes: bytes, filename: str, version_label: str, doc_title: Optional[str] = None) -> Dict[str, Any]:
        files = {"file": (filename, file_bytes, "application/pdf")}
        data = {"version_label": version_label}
        if doc_title:
            data["doc_title"] = doc_title

        resp = requests.post(f"{self.base_url}/api/documents/upload", files=files, data=data, timeout=60)
        if resp.status_code != 200:
            raise Exception(f"Upload failed: {resp.text}")
        return resp.json()

    def query_rag(self, doc_id: str, question: str, engineer_name: str, top_k: int = 4) -> Dict[str, Any]:
        payload = {
            "doc_id": doc_id,
            "question": question,
            "engineer_name": engineer_name,
            "top_k": top_k
        }
        resp = requests.post(f"{self.base_url}/api/query", json=payload, timeout=60)
        if resp.status_code != 200:
            raise Exception(f"Query failed: {resp.text}")
        return resp.json()

    def get_entities(self, doc_id: str, force_refresh: bool = False) -> Dict[str, Any]:
        resp = requests.get(f"{self.base_url}/api/entities/{doc_id}", params={"force_refresh": force_refresh}, timeout=30)
        if resp.status_code != 200:
            raise Exception(f"Entities fetch failed: {resp.text}")
        return resp.json()

    def get_inconsistencies(self, doc_id: str, force_refresh: bool = False) -> List[Dict[str, Any]]:
        resp = requests.get(f"{self.base_url}/api/inconsistencies/{doc_id}", params={"force_refresh": force_refresh}, timeout=30)
        if resp.status_code != 200:
            raise Exception(f"Inconsistency check failed: {resp.text}")
        return resp.json()

    def submit_review_action(self, finding_id: str, status: str, reviewer_name: str, notes: Optional[str] = None) -> Dict[str, Any]:
        payload = {
            "status": status,
            "reviewer_name": reviewer_name,
            "reviewer_notes": notes
        }
        resp = requests.post(f"{self.base_url}/api/inconsistencies/{finding_id}/review", json=payload, timeout=10)
        if resp.status_code != 200:
            raise Exception(f"Review action failed: {resp.text}")
        return resp.json()

    def compare_documents(self, doc_id_v1: str, doc_id_v2: str) -> Dict[str, Any]:
        payload = {"doc_id_v1": doc_id_v1, "doc_id_v2": doc_id_v2}
        resp = requests.post(f"{self.base_url}/api/documents/compare", json=payload, timeout=30)
        if resp.status_code != 200:
            raise Exception(f"Document comparison failed: {resp.text}")
        return resp.json()

    def get_component_impact(self, doc_id: str, component_name: str) -> Dict[str, Any]:
        resp = requests.get(f"{self.base_url}/api/graph/impact/{doc_id}", params={"component_name": component_name}, timeout=10)
        if resp.status_code != 200:
            raise Exception(f"Impact analysis failed: {resp.text}")
        return resp.json()

    def get_cypher_export(self, doc_id: str) -> str:
        resp = requests.get(f"{self.base_url}/api/graph/cypher/{doc_id}", timeout=10)
        if resp.status_code != 200:
            raise Exception(f"Cypher export failed: {resp.text}")
        return resp.json().get("cypher_script", "")

    def get_query_audit(self, limit: int = 100) -> List[Dict[str, Any]]:
        resp = requests.get(f"{self.base_url}/api/audit/queries", params={"limit": limit}, timeout=10)
        return resp.json() if resp.status_code == 200 else []

    def get_review_audit(self, limit: int = 100) -> List[Dict[str, Any]]:
        resp = requests.get(f"{self.base_url}/api/audit/reviews", params={"limit": limit}, timeout=10)
        return resp.json() if resp.status_code == 200 else []
