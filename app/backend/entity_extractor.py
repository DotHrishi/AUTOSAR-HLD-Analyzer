"""
Architecture Entity Extractor module.
Extracts Software Components (SWCs), Interfaces, Port Prototypes, Signals, Data Types,
Dependencies, and Functional Flows with full page/section provenance.
"""

import re
import json
from typing import Dict, Any, List, Optional
from app.backend.pdf_parser import extract_text_from_pdf
from app.backend.llm_service import get_llm_service
from app.backend.database import (
    save_extracted_entities,
    get_cached_extracted_entities,
    get_document_by_id
)


GENERIC_SWC_NAMES = {
    "APPLICATIONSWC", "SENSORACTUATORSWC", "SERVICESWC",
    "COMPLEXDEVICEDRIVERSWC", "ECUABSTRACTIONSWC", "SWC"
}


def extract_architecture_entities(doc_id: str, force_refresh: bool = False) -> Dict[str, Any]:
    """
    Extracts structured architecture entities from an ingested document.
    Checks SQLite cache first unless force_refresh is True.
    """
    if not force_refresh:
        cached = get_cached_extracted_entities(doc_id)
        if cached:
            return cached

    doc_meta = get_document_by_id(doc_id)
    if not doc_meta:
        raise ValueError(f"Document {doc_id} not found")

    file_path = doc_meta["file_path"]
    parsed_pdf = extract_text_from_pdf(file_path)

    # 1. Deterministic pattern-based extraction
    deterministic_model = _extract_deterministic_entities(parsed_pdf)

    # 2. LLM-assisted refinement pass if active
    llm = get_llm_service()
    full_text = "\n\n".join([f"--- Page {p['page_number']} ---\n{p['text']}" for p in parsed_pdf.get("pages", [])])
    
    extraction_prompt = f"""You are an AUTOSAR Architecture Model Extractor.
Extract all Software Components, Ports, Interfaces, Signals, Data Types, and Dependencies from this document into valid JSON.

JSON Schema:
{{
  "components": [
    {{
      "name": "ComponentSWC",
      "type": "ApplicationSWC | SensorActuatorSWC",
      "periodicity": "10ms",
      "safety_level": "ASIL-D",
      "page": 1,
      "section": "2. Software Component: ...",
      "ports": [
        {{
          "name": "RPort_Name",
          "type": "Require | Provide",
          "interface": "If_Name",
          "signal": "Signal_Name",
          "data_type": "uint16",
          "provider": "TargetSWC"
        }}
      ]
    }}
  ],
  "functional_flows": [
    {{
      "name": "Flow Name",
      "page": 3,
      "description": "Step by step flow"
    }}
  ]
}}

DOCUMENT TEXT:
{full_text}
"""
    final_components = deterministic_model.get("components", [])
    final_flows = deterministic_model.get("functional_flows", [])

    try:
        raw_response = llm.generate_response(
            system_prompt="You are a strict JSON architecture extractor. Output ONLY valid JSON, no markdown fences or comments.",
            user_prompt=extraction_prompt,
            temperature=0.0
        )
        clean_json = raw_response.strip()
        if clean_json.startswith("```json"):
            clean_json = clean_json[7:]
        if clean_json.startswith("```"):
            clean_json = clean_json[3:]
        if clean_json.endswith("```"):
            clean_json = clean_json[:-3]
        clean_json = clean_json.strip()

        if clean_json.startswith("{") and clean_json.endswith("}"):
            llm_data = json.loads(clean_json)
            if "components" in llm_data and llm_data["components"]:
                final_components = _merge_component_models(deterministic_model.get("components", []), llm_data.get("components", []))
            if "functional_flows" in llm_data and llm_data["functional_flows"]:
                final_flows = llm_data["functional_flows"]
    except Exception as e:
        print(f"[EntityExtractor] LLM parse fallback to deterministic: {e}")

    result = {
        "doc_id": doc_id,
        "components": final_components,
        "functional_flows": final_flows,
        "flattened_table": _flatten_entities_to_table(final_components)
    }

    save_extracted_entities(doc_id, result)
    return result


def _clean_text_lines(text: str) -> List[str]:
    """Cleans text and repairs wrapped words like PPort_BrakeTorqueRe quest."""
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    cleaned = []
    i = 0
    while i < len(lines):
        line = lines[i]
        # Check if port name is broken across lines
        if (line.startswith("PPort_") or line.startswith("RPort_")) and i + 1 < len(lines):
            next_line = lines[i+1]
            if not next_line.startswith(("R-Port", "P-Port", "If_", "Port", "Software", "Component")) and len(next_line) <= 10:
                line = line + next_line
                i += 1
        cleaned.append(line)
        i += 1
    return cleaned


def _extract_deterministic_entities(parsed_pdf: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deterministic rule-based extractor using regular expressions to parse AUTOSAR tables.
    """
    components: List[Dict[str, Any]] = []
    flows: List[Dict[str, Any]] = []

    for page in parsed_pdf.get("pages", []):
        page_num = page["page_number"]
        text = page["text"]
        lines = _clean_text_lines(text)

        current_swc: Optional[Dict[str, Any]] = None

        for idx, line in enumerate(lines):
            # 1. Detect explicit Component Definition Headers
            # e.g. "2. Software Component: BrakeControlSWC" or "Software Component: EngineManagerSWC"
            swc_header_match = re.search(r'(?:[0-9]+\.\s*)?Software Component:\s*([A-Za-z0-9_]+SWC)', line, re.IGNORECASE)
            
            if swc_header_match:
                swc_name = swc_header_match.group(1).strip()
                if swc_name.upper() not in GENERIC_SWC_NAMES:
                    # Look ahead for component metadata
                    swc_type = "ApplicationSWC"
                    periodicity = "10ms"
                    safety = "ASIL-B"
                    
                    for look in lines[idx:min(len(lines), idx+8)]:
                        if "SensorActuatorSWC" in look or "Sensor/Actuator" in look:
                            swc_type = "SensorActuatorSWC"
                        elif "ApplicationSWC" in look or "Application Software" in look:
                            swc_type = "ApplicationSWC"
                        if "ASIL-D" in look:
                            safety = "ASIL-D"
                        elif "ASIL-C" in look:
                            safety = "ASIL-C"
                        elif "ASIL-B" in look:
                            safety = "ASIL-B"
                        period_match = re.search(r'(\d+ms)', look)
                        if period_match:
                            periodicity = period_match.group(1)

                    current_swc = {
                        "name": swc_name,
                        "type": swc_type,
                        "periodicity": periodicity,
                        "safety_level": safety,
                        "page": page_num,
                        "section": f"Component: {swc_name}",
                        "ports": []
                    }
                    
                    # Deduplicate or replace
                    existing_idx = next((i for i, c in enumerate(components) if c["name"] == swc_name), -1)
                    if existing_idx == -1:
                        components.append(current_swc)
                    else:
                        current_swc = components[existing_idx]

            # 2. Detect Port definitions when inside a component section
            port_match = re.search(r'([RP]Port_[A-Za-z0-9_]+)', line)
            if port_match and current_swc:
                p_name = port_match.group(1).strip()
                p_type = "Require" if p_name.startswith("RPort") else "Provide"
                
                # Check if port is already recorded
                if not any(p["name"] == p_name for p in current_swc["ports"]):
                    # Scan following lines for port attributes
                    if_name = f"If_{p_name[6:]}"
                    signal_name = f"{p_name[6:]}"
                    data_type = "uint16"
                    provider_target = "External"

                    lookahead_lines = lines[idx:min(len(lines), idx+10)]
                    
                    # Search for Interface Name (If_...)
                    for l in lookahead_lines:
                        if_m = re.search(r'\b(If_[A-Za-z0-9_]+)\b', l)
                        if if_m:
                            if_name = if_m.group(1)
                            break

                    # Search for Data Type
                    for l in lookahead_lines:
                        dt_m = re.search(r'\b(float32|uint16|uint8|uint32|boolean|sint16|sint32)\b', l)
                        if dt_m:
                            data_type = dt_m.group(1)
                            break

                    # Search for Signal / Element Name
                    for l in lookahead_lines:
                        sig_m = re.search(r'\b([A-Za-z0-9_]+(?:_kph|_Nm|_rpm|_deg|_pct|_A|_mps2|Percent|CurrentGear))\b', l)
                        if sig_m:
                            signal_name = sig_m.group(1)
                            break

                    # Search for Target / Provider SWC
                    for l in lookahead_lines:
                        tgt_m = re.search(r'\b([A-Za-z0-9_]+SWC)\b', l)
                        if tgt_m and tgt_m.group(1) != current_swc["name"] and tgt_m.group(1).upper() not in GENERIC_SWC_NAMES:
                            provider_target = tgt_m.group(1)
                            break

                    current_swc["ports"].append({
                        "name": p_name,
                        "type": p_type,
                        "interface": if_name,
                        "signal": signal_name,
                        "data_type": data_type,
                        "provider": provider_target
                    })

            # 3. Detect Functional Flows
            if ("Flow 1:" in line or "Flow 2:" in line or "Functional Flow" in line) and "Page" not in line:
                desc = lines[idx+1] if idx+1 < len(lines) else line
                flows.append({
                    "name": line,
                    "page": page_num,
                    "description": desc
                })

    return {
        "components": components,
        "functional_flows": flows
    }


def _merge_component_models(det_components: List[Dict], llm_components: List[Dict]) -> List[Dict]:
    """Combines deterministic table scans with LLM extracted attributes."""
    merged = {c["name"]: c for c in det_components}

    for lc in llm_components:
        name = lc.get("name")
        if not name or name.upper() in GENERIC_SWC_NAMES:
            continue
        if name not in merged:
            merged[name] = lc
        else:
            existing_port_names = {p["name"] for p in merged[name].get("ports", [])}
            for lp in lc.get("ports", []):
                if lp.get("name") not in existing_port_names:
                    merged[name]["ports"].append(lp)
            if lc.get("safety_level"):
                merged[name]["safety_level"] = lc["safety_level"]
            if lc.get("periodicity"):
                merged[name]["periodicity"] = lc["periodicity"]

    return list(merged.values())


def _flatten_entities_to_table(components: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Flattens components and ports into tabular rows for UI display and CSV export."""
    rows = []
    for c in components:
        c_name = c.get("name", "UnknownSWC")
        c_type = c.get("type", "ApplicationSWC")
        period = c.get("periodicity", "-")
        safety = c.get("safety_level", "ASIL-B")
        page = c.get("page", 1)
        section = c.get("section", "-")

        ports = c.get("ports", [])
        if not ports:
            rows.append({
                "Component Name": c_name,
                "Component Type": c_type,
                "Periodicity": period,
                "Safety Level": safety,
                "Port Name": "-",
                "Port Type": "-",
                "Interface Name": "-",
                "Signal / Element": "-",
                "Data Type": "-",
                "Target / Provider SWC": "-",
                "Source Page": page,
                "Provenance Section": section
            })
        else:
            for p in ports:
                rows.append({
                    "Component Name": c_name,
                    "Component Type": c_type,
                    "Periodicity": period,
                    "Safety Level": safety,
                    "Port Name": p.get("name", "-"),
                    "Port Type": p.get("type", "-"),
                    "Interface Name": p.get("interface", "-"),
                    "Signal / Element": p.get("signal", "-"),
                    "Data Type": p.get("data_type", "-"),
                    "Target / Provider SWC": p.get("provider", "-"),
                    "Source Page": page,
                    "Provenance Section": section
                })
    return rows
