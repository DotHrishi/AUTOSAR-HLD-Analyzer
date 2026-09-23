"""
Document Revision Comparator module.
Performs semantic and structural diffs between two HLD document versions,
identifying Added, Removed, and Modified Components, Ports, Interfaces, Signals, and Data Types.
"""

from typing import Dict, Any, List
from app.backend.entity_extractor import extract_architecture_entities
from app.backend.database import get_document_by_id
from app.backend.llm_service import get_llm_service


def compare_hld_revisions(doc_id_v1: str, doc_id_v2: str) -> Dict[str, Any]:
    """
    Compares two HLD document versions (V1 baseline vs V2 revision)
    and computes a structured architectural diff.
    """
    doc1_meta = get_document_by_id(doc_id_v1)
    doc2_meta = get_document_by_id(doc_id_v2)

    if not doc1_meta:
        raise ValueError(f"Baseline document {doc_id_v1} not found.")
    if not doc2_meta:
        raise ValueError(f"Revised document {doc_id_v2} not found.")

    entities_v1 = extract_architecture_entities(doc_id_v1)
    entities_v2 = extract_architecture_entities(doc_id_v2)

    comp_v1 = {c["name"]: c for c in entities_v1.get("components", [])}
    comp_v2 = {c["name"]: c for c in entities_v2.get("components", [])}

    added_components = []
    removed_components = []
    modified_components = []
    unchanged_components = []

    # 1. Check Added in V2
    for name, c2 in comp_v2.items():
        if name not in comp_v1:
            added_components.append({
                "name": name,
                "type": c2.get("type"),
                "safety_level": c2.get("safety_level"),
                "periodicity": c2.get("periodicity"),
                "ports_count": len(c2.get("ports", [])),
                "page": c2.get("page", 1),
                "section": c2.get("section", "-")
            })

    # 2. Check Removed from V1
    for name, c1 in comp_v1.items():
        if name not in comp_v2:
            removed_components.append({
                "name": name,
                "type": c1.get("type"),
                "safety_level": c1.get("safety_level"),
                "periodicity": c1.get("periodicity"),
                "page": c1.get("page", 1),
                "section": c1.get("section", "-")
            })

    # 3. Check Modified Components
    for name, c2 in comp_v2.items():
        if name in comp_v1:
            c1 = comp_v1[name]
            diffs = []

            # Check metadata changes
            if c1.get("safety_level") != c2.get("safety_level"):
                diffs.append(f"Safety Level changed from {c1.get('safety_level')} to {c2.get('safety_level')}")
            if c1.get("periodicity") != c2.get("periodicity"):
                diffs.append(f"Periodicity changed from {c1.get('periodicity')} to {c2.get('periodicity')}")

            # Check Port differences
            ports_v1 = {p["name"]: p for p in c1.get("ports", [])}
            ports_v2 = {p["name"]: p for p in c2.get("ports", [])}

            added_ports = [p["name"] for p in ports_v2.values() if p["name"] not in ports_v1]
            removed_ports = [p["name"] for p in ports_v1.values() if p["name"] not in ports_v2]

            modified_ports = []
            for p_name, p2 in ports_v2.items():
                if p_name in ports_v1:
                    p1 = ports_v1[p_name]
                    port_changes = []
                    if p1.get("data_type") != p2.get("data_type"):
                        port_changes.append(f"Data type updated from '{p1.get('data_type')}' to '{p2.get('data_type')}'")
                    if p1.get("provider") != p2.get("provider"):
                        port_changes.append(f"Provider updated from '{p1.get('provider')}' to '{p2.get('provider')}'")
                    if p1.get("interface") != p2.get("interface"):
                        port_changes.append(f"Interface updated from '{p1.get('interface')}' to '{p2.get('interface')}'")
                    if port_changes:
                        modified_ports.append({
                            "port_name": p_name,
                            "changes": port_changes
                        })

            if added_ports:
                diffs.append(f"Added ports: {', '.join(added_ports)}")
            if removed_ports:
                diffs.append(f"Removed ports: {', '.join(removed_ports)}")
            if modified_ports:
                for mp in modified_ports:
                    diffs.append(f"Port '{mp['port_name']}': {'; '.join(mp['changes'])}")

            if diffs:
                modified_components.append({
                    "name": name,
                    "type": c2.get("type"),
                    "v1_page": c1.get("page", 1),
                    "v2_page": c2.get("page", 1),
                    "changes": diffs
                })
            else:
                unchanged_components.append(name)

    summary_text = (
        f"Compared '{doc1_meta['filename']}' ({doc1_meta['version_label']}) against "
        f"'{doc2_meta['filename']}' ({doc2_meta['version_label']}). "
        f"Detected {len(added_components)} added components, {len(removed_components)} removed components, "
        f"and {len(modified_components)} modified components."
    )

    return {
        "doc_id_v1": doc_id_v1,
        "doc_id_v2": doc_id_v2,
        "doc_name_v1": doc1_meta["filename"],
        "doc_name_v2": doc2_meta["filename"],
        "version_v1": doc1_meta["version_label"],
        "version_v2": doc2_meta["version_label"],
        "summary": summary_text,
        "added_components": added_components,
        "removed_components": removed_components,
        "modified_components": modified_components,
        "unchanged_components": unchanged_components,
        "total_changes": len(added_components) + len(removed_components) + len(modified_components)
    }
