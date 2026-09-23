"""
Architecture Graph Analyzer module using NetworkX with optional Cypher / Neo4j export.
Provides topological dependency analysis, downstream/upstream impact traversal, and graph export.
"""

from typing import Dict, Any, List, Set
import networkx as nx
from app.backend.entity_extractor import extract_architecture_entities


def build_architecture_graph(doc_id: str) -> nx.DiGraph:
    """
    Constructs a directed graph of Software Components, Ports, and Interfaces.
    """
    entities = extract_architecture_entities(doc_id)
    components = entities.get("components", [])

    G = nx.DiGraph()

    for c in components:
        c_name = c["name"]
        G.add_node(
            c_name,
            node_type="SoftwareComponent",
            swc_type=c.get("type", "ApplicationSWC"),
            safety_level=c.get("safety_level", "ASIL-B"),
            periodicity=c.get("periodicity", "10ms"),
            page=c.get("page", 1)
        )

        for p in c.get("ports", []):
            p_name = f"{c_name}.{p['name']}"
            p_type = p.get("type", "Provide")
            if_name = p.get("interface", "UnknownIf")
            target = p.get("provider", "")

            G.add_node(
                p_name,
                node_type="PortPrototype",
                port_type=p_type,
                interface=if_name,
                signal=p.get("signal", ""),
                data_type=p.get("data_type", ""),
                parent_swc=c_name
            )

            if p_type == "Provide":
                G.add_edge(c_name, p_name, relationship="EXPOSES_PPORT")
                if target and target != "External":
                    G.add_edge(p_name, target, relationship="DELIVERS_TO")
            else:
                G.add_edge(c_name, p_name, relationship="REQUIRES_RPORT")
                if target and target != "External":
                    G.add_edge(target, p_name, relationship="FEEDS_RPORT")
                    G.add_edge(target, c_name, relationship="DEPENDS_ON")

    return G


def analyze_component_impact(doc_id: str, target_component: str) -> Dict[str, Any]:
    """
    Computes upstream dependencies and downstream blast radius for a target SWC.
    """
    G = build_architecture_graph(doc_id)

    if target_component not in G:
        return {
            "target_component": target_component,
            "error": f"Component '{target_component}' not found in architecture graph.",
            "upstream_dependencies": [],
            "downstream_impact": [],
            "blast_radius_count": 0
        }

    # Upstream: nodes that target_component depends on
    upstream_swcs: Set[str] = set()
    for n in nx.ancestors(G, target_component):
        if G.nodes[n].get("node_type") == "SoftwareComponent":
            upstream_swcs.add(n)

    # Downstream: nodes that depend on target_component
    downstream_swcs: Set[str] = set()
    for n in nx.descendants(G, target_component):
        if G.nodes[n].get("node_type") == "SoftwareComponent":
            downstream_swcs.add(n)

    return {
        "target_component": target_component,
        "metadata": G.nodes[target_component],
        "upstream_dependencies": list(upstream_swcs),
        "downstream_impact": list(downstream_swcs),
        "blast_radius_count": len(downstream_swcs),
        "total_graph_nodes": G.number_of_nodes(),
        "total_graph_edges": G.number_of_edges()
    }


def generate_cypher_export(doc_id: str) -> str:
    """
    Generates Cypher query statements ready to be imported into Neo4j graph database.
    """
    entities = extract_architecture_entities(doc_id)
    components = entities.get("components", [])

    cypher_lines = [
        f"// --- Neo4j Cypher Import Script for Document: {doc_id} ---",
        "CREATE CONSTRAINT swc_name IF NOT EXISTS FOR (c:SoftwareComponent) REQUIRE c.name IS UNIQUE;",
        ""
    ]

    for c in components:
        cypher_lines.append(
            f"MERGE (c:SoftwareComponent {{name: '{c['name']}'}}) "
            f"SET c.type = '{c.get('type')}', c.safety = '{c.get('safety_level')}', "
            f"c.periodicity = '{c.get('periodicity')}', c.page = {c.get('page', 1)};"
        )

        for p in c.get("ports", []):
            cypher_lines.append(
                f"MERGE (p:Port {{name: '{c['name']}_{p['name']}'}}) "
                f"SET p.type = '{p.get('type')}', p.interface = '{p.get('interface')}', "
                f"p.dataType = '{p.get('data_type')}', p.signal = '{p.get('signal')}';"
            )
            rel = "EXPOSES_PPORT" if p.get("type") == "Provide" else "REQUIRES_RPORT"
            cypher_lines.append(
                f"MATCH (c:SoftwareComponent {{name: '{c['name']}'}}), (p:Port {{name: '{c['name']}_{p['name']}'}}) "
                f"MERGE (c)-[:{rel}]->(p);"
            )

    return "\n".join(cypher_lines)
