"""
Streamlit Frontend for AUTOSAR HLD Document Analysis Assistant.
Comprehensive Automotive Architecture AI Workbench.
"""

import os
import sys
import io
import json
from pathlib import Path
import pandas as pd
import streamlit as st
from datetime import datetime

try:
    import plotly.graph_objects as go
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

# Ensure project root is in sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

try:
    from app.frontend.api_client import APIClient
except ImportError:
    from api_client import APIClient

# Page configuration
st.set_page_config(
    page_title="AUTOSAR HLD Assistant | Tata Technologies",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize API client
api = APIClient()

# Custom CSS for rich automotive styling
st.markdown("""
<style>
    .main-header {
        font-size: 1.8rem;
        font-weight: 700;
        color: #00FF66;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 0.95rem;
        color: #4B5563;
        margin-bottom: 1rem;
    }
    .badge-asil-d {
        background-color: #FEE2E2;
        color: #991B1B;
        padding: 2px 8px;
        border-radius: 4px;
        font-weight: 600;
        font-size: 0.8rem;
    }
    .badge-asil-b {
        background-color: #FEF3C7;
        color: #92400E;
        padding: 2px 8px;
        border-radius: 4px;
        font-weight: 600;
        font-size: 0.8rem;
    }
    .badge-status {
        padding: 3px 8px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    .citation-tag {
        background-color: #E0E7FF;
        color: #3730A3;
        padding: 2px 6px;
        border-radius: 4px;
        font-size: 0.8rem;
        font-weight: 600;
        margin-right: 4px;
    }
    .card-box {
        border: 1px solid #E5E7EB;
        border-radius: 8px;
        padding: 16px;
        background-color: #FFFFFF;
        margin-bottom: 12px;
    }
</style>
""", unsafe_allow_html=True)

# ----------------- SIDEBAR -----------------
with st.sidebar:
    st.image("https://img.icons8.com/color/96/car.png", width=64)
    st.markdown("### **AUTOSAR HLD Assistant**")
    st.caption("Automotive AI Architecture Workbench — Tata Technologies")
    
    # Engineer Profile
    engineer_name = st.text_input("👤 Engineer Name / ID", value="Hrishikesh Kali (Chassis Lead)")
    st.divider()

    # Backend Connection Status
    health = api.check_health()
    if health.get("status") == "healthy":
        st.success(f"Backend Connected ({health.get('llm_provider', 'mock').upper()} Mode)")
    else:
        st.error("⚠️ Backend Offline (Ensure FastAPI is running)")

    st.divider()
    
    # Document Selection
    docs = api.list_documents()
    doc_options = {f"{d['filename']} (v{d['version_label']})": d['doc_id'] for d in docs}
    
    selected_doc_id = None
    if doc_options:
        selected_doc_label = st.selectbox("📂 Active HLD Document", list(doc_options.keys()))
        selected_doc_id = doc_options[selected_doc_label]
        active_doc_info = next((d for d in docs if d['doc_id'] == selected_doc_id), None)
        if active_doc_info:
            st.info(
                f"**Pages:** {active_doc_info.get('page_count', 0)} | "
                f"**Chunks:** {active_doc_info.get('chunk_count', 0)} | "
                f"**Size:** {active_doc_info.get('file_size_kb', 0)} KB"
            )
    else:
        st.warning("No documents loaded. Go to Tab 1 to upload or load sample HLDs.")

    st.divider()
    st.caption("AUTOSAR Classic 4.4 | ISO 26262 ASIL-D | Local Embedding RAG")


# ----------------- MAIN INTERFACE -----------------
st.markdown('<div class="main-header">AUTOSAR High-Level Design (HLD) Document Analysis Assistant</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Grounded RAG Q&A, Deterministic Inconsistency Engine, Provenance Extraction & Architecture Diffs</div>', unsafe_allow_html=True)

# Navigation Tabs
tab_upload, tab_rag, tab_entities, tab_inconsistencies, tab_compare, tab_graph, tab_audit = st.tabs([
    "📄 Ingest & Upload",
    "💬 Architecture Q&A",
    "🧩 Entity Explorer",
    "⚠️ Inconsistencies & Review",
    "🔄 Revision Comparison",
    "🕸️ Graph & Impact",
    "📜 Governance & Audit"
])


# ----------------- TAB 1: UPLOAD & INGESTION -----------------
with tab_upload:
    st.subheader("1. Ingest AUTOSAR HLD Specification")
    
    col_up1, col_up2 = st.columns([1.2, 1])

    with col_up1:
        st.markdown("#### Upload New HLD PDF")
        uploaded_file = st.file_uploader("Select AUTOSAR HLD PDF Document", type=["pdf"])
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            ver_input = st.text_input("Version Label", value="1.0")
        with col_m2:
            title_input = st.text_input("Document Title (Optional)", placeholder="Powertrain Domain HLD")

        if uploaded_file and st.button("🚀 Ingest & Index Document", type="primary"):
            with st.spinner("Processing PDF (parsing pages, generating vector embeddings, and extracting architecture)... For large 500+ page specifications, this may take 1-2 minutes..."):
                try:
                    bytes_data = uploaded_file.getvalue()
                    res = api.upload_document(
                        file_bytes=bytes_data,
                        filename=uploaded_file.name,
                        version_label=ver_input,
                        doc_title=title_input if title_input else None
                    )
                    st.success(f"✅ Ingestion Complete! ID: `{res['doc_id']}` ({res['page_count']} Pages, {res['chunk_count']} Chunks)")
                    st.rerun()
                except Exception as e:
                    st.error(f"Ingestion failed: {e}")

    with col_up2:
        st.markdown("#### Quick Load Demo Artifacts")
        st.info("Load pre-generated AUTOSAR sample specifications for immediate end-to-end demonstration.")
        
        sample_dir = os.path.join(os.path.dirname(__file__), "..", "sample_docs")
        v1_path = os.path.join(sample_dir, "sample_autosar_hld_v1.pdf")
        v2_path = os.path.join(sample_dir, "sample_autosar_hld_v2.pdf")

        if os.path.exists(v1_path) and st.button("📥 Load Baseline HLD V1.0 (Contains Flaws)"):
            with st.spinner("Ingesting Sample HLD V1..."):
                with open(v1_path, "rb") as f:
                    api.upload_document(f.read(), "sample_autosar_hld_v1.pdf", "1.0", "Powertrain Domain HLD Baseline")
                st.success("Sample HLD V1.0 loaded!")
                st.rerun()

        if os.path.exists(v2_path) and st.button("📥 Load Revised HLD V2.0 (ADAS & Fixes)"):
            with st.spinner("Ingesting Sample HLD V2..."):
                with open(v2_path, "rb") as f:
                    api.upload_document(f.read(), "sample_autosar_hld_v2.pdf", "2.0", "Powertrain Domain HLD Revision 2.0")
                st.success("Sample HLD V2.0 loaded!")
                st.rerun()

    st.divider()
    st.markdown("#### Ingested Documents in Knowledge Repository")
    all_docs = api.list_documents()
    if all_docs:
        df_docs = pd.DataFrame(all_docs)[["doc_id", "filename", "doc_title", "version_label", "page_count", "chunk_count", "upload_time"]]
        st.dataframe(df_docs, use_container_width=True)
    else:
        st.info("No documents currently ingested.")


# ----------------- TAB 2: RAG Q&A -----------------
with tab_rag:
    st.subheader("2. Grounded Architecture Q&A (RAG)")
    
    if not selected_doc_id:
        st.warning("Please select or ingest a document in the sidebar first.")
    else:
        st.caption(f"Currently querying: **{selected_doc_label}**")
        
        # Suggested questions
        st.markdown("**Sample Architectural Queries:**")
        cols_q = st.columns(4)
        sample_qs = [
            "What interfaces does the BrakeControlSWC component expose?",
            "What are the ports and dependencies of EngineManagerSWC?",
            "Describe the Regenerative Braking Coordination functional flow.",
            "Are there any data type mismatches or undefined dependencies?"
        ]
        
        if "query_input" not in st.session_state:
            st.session_state.query_input = ""

        for idx, sq in enumerate(sample_qs):
            if cols_q[idx].button(sq, key=f"sq_{idx}"):
                st.session_state.query_input = sq

        user_question = st.text_input("Ask a question about software components, interfaces, ports, or signals:", value=st.session_state.query_input)

        col_rag1, col_rag2 = st.columns([1, 4])
        top_k = col_rag1.slider("Context Chunks (Top-K)", min_value=2, max_value=8, value=4)
        ask_btn = col_rag2.button("🔍 Query Architecture Knowledge Base", type="primary")

        if ask_btn and user_question:
            with st.spinner("Retrieving relevant semantic chunks and generating grounded answer with citations..."):
                try:
                    rag_res = api.query_rag(
                        doc_id=selected_doc_id,
                        question=user_question,
                        engineer_name=engineer_name,
                        top_k=top_k
                    )

                    st.markdown("### Grounded Answer")
                    st.markdown(rag_res.get("answer", ""))

                    # Display Citations
                    citations = rag_res.get("citations", [])
                    if citations:
                        st.markdown("**Source Provenance Citations:**")
                        cit_html = " ".join([f'<span class="citation-tag">📌 {c}</span>' for c in citations])
                        st.markdown(cit_html, unsafe_allow_html=True)

                    st.caption(f"⏱️ Retrieval + LLM Latency: {rag_res.get('latency_ms', 0)} ms | Logged to SQLite Audit Trail")

                    # Expandable chunks
                    with st.expander("🔍 Inspect Retrieved Context Blocks"):
                        for i, chunk in enumerate(rag_res.get("retrieved_chunks", [])):
                            st.markdown(f"**Chunk {i+1} | Page {chunk.get('page_number')} | Section: {chunk.get('section_title')} (Similarity: {chunk.get('similarity_score')})**")
                            st.code(chunk.get("text", ""), language="text")

                except Exception as e:
                    st.error(f"Query error: {e}")


# ----------------- TAB 3: ENTITY EXPLORER -----------------
with tab_entities:
    st.subheader("3. Architecture Entity Extraction & Provenance Explorer")
    
    if not selected_doc_id:
        st.warning("Please select a document from the sidebar.")
    else:
        col_e1, col_e2 = st.columns([3, 1])
        with col_e1:
            st.caption(f"Structured software components, ports, and signals extracted from **{selected_doc_label}**")
        with col_e2:
            refresh_ent = st.button("🔄 Re-Extract Entities")

        try:
            ent_data = api.get_entities(selected_doc_id, force_refresh=refresh_ent)
            flat_table = ent_data.get("flattened_table", [])
            
            if flat_table:
                df_ent = pd.DataFrame(flat_table)
                
                # Filters
                col_f1, col_f2, col_f3 = st.columns(3)
                swc_filter = col_f1.multiselect("Filter by Component", options=sorted(df_ent["Component Name"].unique()))
                port_filter = col_f2.multiselect("Filter by Port Type", options=sorted(df_ent["Port Type"].unique()))
                search_term = col_f3.text_input("Search Interface/Signal", "")

                filtered_df = df_ent.copy()
                if swc_filter:
                    filtered_df = filtered_df[filtered_df["Component Name"].isin(swc_filter)]
                if port_filter:
                    filtered_df = filtered_df[filtered_df["Port Type"].isin(port_filter)]
                if search_term:
                    filtered_df = filtered_df[
                        filtered_df["Interface Name"].str.contains(search_term, case=False, na=False) |
                        filtered_df["Signal / Element"].str.contains(search_term, case=False, na=False)
                    ]

                st.dataframe(filtered_df, use_container_width=True)

                # Export buttons — CSV and structured JSON
                col_exp1, col_exp2 = st.columns(2)
                csv_buffer = io.StringIO()
                filtered_df.to_csv(csv_buffer, index=False)
                col_exp1.download_button(
                    label="📥 Export Entities to CSV",
                    data=csv_buffer.getvalue(),
                    file_name=f"autosar_entities_{selected_doc_id}.csv",
                    mime="text/csv"
                )
                try:
                    json_export = api.export_entities_json(selected_doc_id)
                    col_exp2.download_button(
                        label="📦 Export Entities to JSON (Toolchain)",
                        data=json.dumps(json_export, indent=2),
                        file_name=f"autosar_entities_{selected_doc_id}.json",
                        mime="application/json"
                    )
                except Exception:
                    pass

                # Functional flows
                flows = ent_data.get("functional_flows", [])
                if flows:
                    st.markdown("#### Document Functional Flows")
                    for fl in flows:
                        st.info(f"**{fl.get('name')}** (Page {fl.get('page', 1)}): {fl.get('description', '')}")

            else:
                st.info("No entities extracted yet.")

        except Exception as e:
            st.error(f"Failed to fetch entities: {e}")


# ----------------- TAB 4: INCONSISTENCIES & HUMAN REVIEW -----------------
with tab_inconsistencies:
    st.subheader("4. Deterministic Inconsistency Engine & Human Review Workbench")
    
    st.warning(
        "⚠️ **Governance Note:** The findings below are generated via deterministic schema verification and AI heuristics. "
        "They **require human engineering review** and do NOT constitute automated safety approval."
    )

    if not selected_doc_id:
        st.warning("Please select a document from the sidebar.")
    else:
        col_inc1, col_inc2 = st.columns([3, 1])
        with col_inc2:
            re_run = st.button("⚡ Run Validation Checks", type="primary")

        try:
            findings = api.get_inconsistencies(selected_doc_id, force_refresh=re_run)
            
            if not findings:
                st.success("🎉 No architectural inconsistencies detected for this document.")
            else:
                st.markdown(f"**Found {len(findings)} architectural issue(s):**")
                
                for f in findings:
                    sev = f.get("severity", "MEDIUM")
                    status = f.get("status", "AI_FLAGGED")
                    
                    status_colors = {
                        "AI_FLAGGED": "#3B82F6",
                        "UNDER_REVIEW": "#F59E0B",
                        "ACCEPTED": "#EF4444",
                        "REJECTED": "#10B981"
                    }

                    with st.container():
                        st.markdown(f"""
                        <div class="card-box">
                            <div style="display:flex; justify-content:space-between; align-items:center;">
                                <h4 style="margin:0; color:#1E3A8A;">[{sev}] {f.get('summary')}</h4>
                                <span class="badge-status" style="background-color:{status_colors.get(status, '#6B7280')}; color:white;">
                                    {status}
                                </span>
                            </div>
                            <p style="margin-top:8px; color:#374151;"><b>Description:</b> {f.get('description')}</p>
                            <p style="color:#047857;"><b>Recommended Remediation:</b> {f.get('remediation')}</p>
                            <p style="font-size:0.85rem; color:#6B7280;">
                                <b>Evidence:</b> Page {f.get('evidence_page')} ({f.get('evidence_section')}) | 
                                <b>Component:</b> {f.get('component_name')} | 
                                <b>Reviewer:</b> {f.get('reviewer_name') or 'Unassigned'}
                            </p>
                        </div>
                        """, unsafe_allow_html=True)

                        # Human Review Action Form
                        with st.expander(f"✍️ Human Review Action: {f.get('id')}"):
                            col_act1, col_act2, col_act3 = st.columns([1, 2, 1])
                            new_st = col_act1.selectbox(
                                "Status Action",
                                ["AI_FLAGGED", "UNDER_REVIEW", "ACCEPTED", "REJECTED"],
                                index=["AI_FLAGGED", "UNDER_REVIEW", "ACCEPTED", "REJECTED"].index(status),
                                key=f"st_sel_{f.get('id')}"
                            )
                            notes = col_act2.text_input("Reviewer Engineering Note", value=f.get("reviewer_notes") or "", key=f"note_{f.get('id')}")
                            if col_act3.button("💾 Submit Decision", key=f"btn_{f.get('id')}"):
                                res = api.submit_review_action(
                                    finding_id=f.get("id"),
                                    status=new_st,
                                    reviewer_name=engineer_name,
                                    notes=notes
                                )
                                st.success(f"Review updated to {new_st}")
                                st.rerun()

        except Exception as e:
            st.error(f"Inconsistency analysis error: {e}")

    # JSON export for the full inconsistency report
    if selected_doc_id:
        try:
            st.divider()
            col_jexp1, _ = st.columns([1, 3])
            json_inc_export = api.export_inconsistencies_json(selected_doc_id)
            col_jexp1.download_button(
                label="📦 Export Findings to JSON (Issue Tracker / FMEA)",
                data=json.dumps(json_inc_export, indent=2),
                file_name=f"autosar_inconsistencies_{selected_doc_id}.json",
                mime="application/json"
            )
        except Exception:
            pass


# ----------------- TAB 5: REVISION COMPARISON -----------------
with tab_compare:
    st.subheader("5. HLD Document Revision Comparison (Semantic Diff)")
    st.caption("Compare two versions of an AUTOSAR HLD to detect added, removed, and modified architectural elements.")

    if len(docs) < 2:
        st.info("You need at least 2 ingested documents to perform revision comparison. Go to Tab 1 to load Sample HLD V1 and V2.")
    else:
        col_cmp1, col_cmp2, col_cmp3 = st.columns([2, 2, 1])
        doc1_label = col_cmp1.selectbox("Baseline HLD (V1)", list(doc_options.keys()), index=0)
        doc2_label = col_cmp2.selectbox("Revised HLD (V2)", list(doc_options.keys()), index=min(1, len(doc_options)-1))
        
        doc1_id = doc_options[doc1_label]
        doc2_id = doc_options[doc2_label]

        if col_cmp3.button("🔄 Compare Versions", type="primary"):
            with st.spinner("Analyzing structural and interface differences across revisions..."):
                try:
                    diff = api.compare_documents(doc_id_v1=doc1_id, doc_id_v2=doc2_id)
                    
                    st.success(diff.get("summary", ""))

                    col_d1, col_d2, col_d3 = st.columns(3)
                    col_d1.metric("Added Components", len(diff.get("added_components", [])))
                    col_d2.metric("Removed Components", len(diff.get("removed_components", [])))
                    col_d3.metric("Modified Components", len(diff.get("modified_components", [])))

                    # Detailed breakdowns
                    if diff.get("added_components"):
                        st.markdown("#### ➕ Added Components")
                        for ac in diff.get("added_components", []):
                            st.success(f"**{ac['name']}** ({ac['type']}, {ac['safety_level']}) — Added on Page {ac['page']}")

                    if diff.get("removed_components"):
                        st.markdown("#### ➖ Removed Components")
                        for rc in diff.get("removed_components", []):
                            st.error(f"**{rc['name']}** ({rc['type']}) — Removed from baseline")

                    if diff.get("modified_components"):
                        st.markdown("#### ✏️ Modified Components & Port Data Types")
                        for mc in diff.get("modified_components", []):
                            with st.expander(f"**{mc['name']}** (Modified on Page {mc['v2_page']})"):
                                for chg in mc["changes"]:
                                    st.write(f"- {chg}")

                except Exception as e:
                    st.error(f"Comparison error: {e}")


# ----------------- TAB 6: GRAPH & IMPACT ANALYSIS -----------------
with tab_graph:
    st.subheader("6. Architecture Dependency Graph & Blast Radius Impact Analysis")

    if not selected_doc_id:
        st.warning("Please select a document from the sidebar.")
    else:
        try:
            ent_data = api.get_entities(selected_doc_id)
            components = ent_data.get("components", [])
            component_names = [c["name"] for c in components]

            if not component_names:
                st.info("No components found in document.")
            else:
                # ---- Inline Plotly Network Graph ----
                if HAS_PLOTLY and components:
                    st.markdown("#### Architecture Dependency Graph")
                    st.caption("Arrows represent Provide→Require port dependencies between SWCs.")

                    # Build edge list from ports
                    edges = []
                    for comp in components:
                        for port in comp.get("ports", []):
                            if port.get("type") == "Provide":
                                provider = port.get("provider", "")
                                if provider and provider not in ("External", "-", ""):
                                    edges.append((comp["name"], provider, port.get("interface", "")))

                    # Node positions (circular layout)
                    import math
                    n = len(component_names)
                    angle_step = 2 * math.pi / max(n, 1)
                    pos = {
                        name: (math.cos(i * angle_step) * 2, math.sin(i * angle_step) * 2)
                        for i, name in enumerate(component_names)
                    }

                    # Safety level color map
                    asil_colors = {
                        "ASIL-D": "#EF4444", "ASIL-C": "#F97316",
                        "ASIL-B": "#EAB308", "ASIL-A": "#22C55E", "QM": "#6B7280"
                    }

                    # Edge traces
                    edge_traces = []
                    for src, dst, iface in edges:
                        x0, y0 = pos.get(src, (0, 0))
                        x1, y1 = pos.get(dst, (0, 0))
                        edge_traces.append(go.Scatter(
                            x=[x0, x1, None], y=[y0, y1, None],
                            mode="lines",
                            line=dict(width=1.5, color="#94A3B8"),
                            hoverinfo="text",
                            text=iface,
                            showlegend=False
                        ))

                    # Node trace
                    node_x = [pos[n][0] for n in component_names]
                    node_y = [pos[n][1] for n in component_names]
                    node_colors = [
                        asil_colors.get(
                            next((c["safety_level"] for c in components if c["name"] == n), "QM"),
                            "#6B7280"
                        )
                        for n in component_names
                    ]
                    node_text = [
                        f"<b>{c['name']}</b><br>Type: {c.get('type','')}<br>"
                        f"Periodicity: {c.get('periodicity','')}<br>ASIL: {c.get('safety_level','')}<br>"
                        f"Ports: {len(c.get('ports',[]))}"
                        for c in components
                    ]
                    node_trace = go.Scatter(
                        x=node_x, y=node_y,
                        mode="markers+text",
                        marker=dict(size=28, color=node_colors, line=dict(width=2, color="white")),
                        text=component_names,
                        textposition="top center",
                        hoverinfo="text",
                        hovertext=node_text,
                        showlegend=False
                    )

                    fig = go.Figure(
                        data=edge_traces + [node_trace],
                        layout=go.Layout(
                            paper_bgcolor="#0F172A",
                            plot_bgcolor="#0F172A",
                            font=dict(color="white"),
                            margin=dict(l=20, r=20, t=20, b=20),
                            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                            height=480,
                        )
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    st.caption("🔴 ASIL-D  🟠 ASIL-C  🟡 ASIL-B  🟢 ASIL-A  ⚫ QM")

                st.divider()

                # ---- Blast Radius Analysis ----
                col_g1, col_g2 = st.columns([2, 1])
                target_swc = col_g1.selectbox(
                    "Select Target Component for change blast radius:", component_names
                )

                if col_g2.button("💥 Calculate Blast Radius Impact"):
                    impact = api.get_component_impact(selected_doc_id, target_swc)

                    st.markdown(f"### Impact Analysis for `{target_swc}`")
                    col_i1, col_i2 = st.columns(2)

                    with col_i1:
                        st.markdown("#### ⬅️ Upstream Dependencies (What it relies on)")
                        upstreams = impact.get("upstream_dependencies", [])
                        if upstreams:
                            for u in upstreams:
                                st.info(f"- **{u}**")
                        else:
                            st.write("No upstream SWC dependencies.")

                    with col_i2:
                        st.markdown("#### ➡️ Downstream Blast Radius (What will be affected)")
                        downstreams = impact.get("downstream_impact", [])
                        if downstreams:
                            for d in downstreams:
                                st.error(f"- **{d}** (Directly or transitively impacted)")
                        else:
                            st.write("No downstream consumers.")

                st.divider()

                # ---- Neo4j Cypher Export ----
                st.markdown("#### Neo4j Cypher Graph Script Export")
                st.caption(
                    "Copy and execute in Neo4j Browser to visualize full architecture topology. "
                    "Or download and import into your graph database."
                )
                cypher_code = api.get_cypher_export(selected_doc_id)
                col_cy1, col_cy2 = st.columns([3, 1])
                col_cy1.code(cypher_code, language="cypher")
                col_cy2.download_button(
                    label="📥 Download Cypher Script",
                    data=cypher_code,
                    file_name=f"architecture_{selected_doc_id}.cypher",
                    mime="text/plain"
                )

        except Exception as e:
            st.error(f"Graph error: {e}")


# ----------------- TAB 7: GOVERNANCE & AUDIT -----------------
with tab_audit:
    st.subheader("7. Governance, Query History & Review Audit Trails")
    
    tab_aud1, tab_aud2 = st.tabs(["💬 Query History Audit", "✍️ Human Review Audit Log"])

    with tab_aud1:
        st.caption("Every RAG query, engineer identity, retrieved evidence chunk, and generated answer is permanently logged.")
        query_logs = api.get_query_audit(limit=50)
        if query_logs:
            df_q = pd.DataFrame(query_logs)[["id", "timestamp", "engineer_name", "doc_name", "question", "answer", "latency_ms"]]
            st.dataframe(df_q, use_container_width=True)
        else:
            st.info("No query logs recorded yet.")

    with tab_aud2:
        st.caption("All reviewer status transitions (AI_FLAGGED -> ACCEPTED / REJECTED) with engineering rationale.")
        review_logs = api.get_review_audit(limit=50)
        if review_logs:
            df_r = pd.DataFrame(review_logs)[["id", "timestamp", "finding_id", "reviewer_name", "old_status", "new_status", "action_note"]]
            st.dataframe(df_r, use_container_width=True)
        else:
            st.info("No review actions recorded yet.")
