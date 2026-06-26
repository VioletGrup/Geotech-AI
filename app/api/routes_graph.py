"""
routes_graph.py — backend-proxied graph data for the visual graph view.

GET /graph/{site_id}
  Returns nodes + edges for a site, scoped by depth/type filters.
  The frontend renders this with Cytoscape.js — no Bolt/WebSocket from browser.

Query params:
  include  comma-separated node types to include
           default: Zone,PileTestLocation,DPSHTest,BoreHole,TestPit
  limit    max nodes returned (default 300)
"""
from __future__ import annotations
from fastapi import APIRouter, Query
from app.db.neo4j_driver import run_query

router = APIRouter(prefix="/graph", tags=["graph"])

# ── node type → colour + icon letter (used by frontend) ──────────────────────
NODE_STYLE = {
    "Site":                  {"color": "#534AB7", "label_prop": "name"},
    "Zone":                  {"color": "#1D9E75", "label_prop": "id"},
    "PileTestLocation":      {"color": "#3B8BD4", "label_prop": "id"},
    "PileTest":              {"color": "#0C447C", "label_prop": "id"},
    "TensionPileTest":       {"color": "#085041", "label_prop": "id"},
    "LateralPileTest":       {"color": "#0F6E56", "label_prop": "id"},
    "CompressionPileTest":   {"color": "#042C53", "label_prop": "id"},
    "DPSHTest":              {"color": "#BA7517", "label_prop": "id"},
    "BoreHole":              {"color": "#D85A30", "label_prop": "id"},
    "TestPit":               {"color": "#993C1D", "label_prop": "id"},
    "GroundModel":           {"color": "#888780", "label_prop": "id"},
    "GroundLayer":           {"color": "#5F5E5A", "label_prop": "id"},
    "SoilType":              {"color": "#639922", "label_prop": "unit_name"},
    "LaboratoryTest":        {"color": "#3B6D11", "label_prop": "id"},
    "ThermalResistivityTest":{"color": "#EF9F27", "label_prop": "id"},
    "SoilAggressivity":      {"color": "#D4537E", "label_prop": "id"},
}

DEFAULT_TYPES = {
    "Zone", "PileTestLocation", "DPSHTest", "BoreHole", "TestPit",
    "GroundModel", "SoilType",
}

# Relationships to traverse from the site root
TRAVERSE_QUERY = """
MATCH (site:Site {id: $site_id})
CALL {
    WITH site
    // Site → Zone
    MATCH p = (site)-[:HAS_ZONE]->(z:Zone)
    RETURN p LIMIT $limit

    UNION

    // Zone → location nodes
    WITH site
    MATCH (site)-[:HAS_ZONE]->(z:Zone)
    MATCH p = (z)<-[:LOCATED_IN]-(loc)
    WHERE any(lbl IN labels(loc) WHERE lbl IN $types)
    RETURN p LIMIT $limit

    UNION

    // PileTestLocation → PileTest
    WITH site
    MATCH (site)-[:HAS_ZONE]->(z:Zone)<-[:LOCATED_IN]-(loc:PileTestLocation)
    MATCH p = (loc)-[:HAS_TEST]->(pt:PileTest)
    RETURN p LIMIT $limit

    UNION

    // BoreHole/TestPit → GroundModel
    WITH site
    MATCH (site)-[:HAS_ZONE]->(z:Zone)<-[:LOCATED_IN]-(loc)
    WHERE loc:BoreHole OR loc:TestPit
    MATCH p = (loc)-[:HAS_GROUND_MODEL]->(gm:GroundModel)
    RETURN p LIMIT $limit

    UNION

    // GroundModel → GroundLayer → SoilType
    WITH site
    MATCH (site)-[:HAS_ZONE]->(z:Zone)<-[:LOCATED_IN]-(loc)
    WHERE loc:BoreHole OR loc:TestPit
    MATCH (loc)-[:HAS_GROUND_MODEL]->(gm:GroundModel)-[:HAS_LAYER]->(gl:GroundLayer)
    MATCH p = (gl)-[:OF_MATERIAL]->(st:SoilType)
    RETURN p LIMIT $limit
}
RETURN p
"""

STATS_QUERY = """
MATCH (s:Site {id: $site_id})
OPTIONAL MATCH (s)-[:HAS_ZONE]->(z:Zone)
OPTIONAL MATCH (p:PileTestLocation)-[:LOCATED_IN]->(z)
OPTIONAL MATCH (d:DPSHTest)-[:LOCATED_IN]->(z)
OPTIONAL MATCH (b:BoreHole)-[:LOCATED_IN]->(z)
OPTIONAL MATCH (tp:TestPit)-[:LOCATED_IN]->(z)
OPTIONAL MATCH (pt:PileTest)<-[:HAS_TEST]-(p)
RETURN
  s.name AS site_name,
  count(DISTINCT z)  AS zones,
  count(DISTINCT p)  AS pile_locations,
  count(DISTINCT pt) AS pile_tests,
  count(DISTINCT d)  AS dpsh,
  count(DISTINCT b)  AS boreholes,
  count(DISTINCT tp) AS test_pits
"""


@router.get("/{site_id}")
def get_graph(
    site_id: str,
    include: str = Query(default=""),
    limit: int = Query(default=300, ge=1, le=1000),
):
    types = set(include.split(",")) if include.strip() else DEFAULT_TYPES
    types.add("Zone")    # always include
    types.add("Site")

    rows = run_query(TRAVERSE_QUERY, {
        "site_id": site_id,
        "types": list(types),
        "limit": limit,
    })

    nodes: dict[str, dict] = {}
    edges: list[dict] = {}
    edge_list: list[dict] = []
    seen_edges: set[str] = set()

    for row in rows:
        path = row["p"]
        # path.nodes and path.relationships
        for node in path.nodes:
            nid = str(node.element_id)
            if nid in nodes:
                continue
            label = next(
                (l for l in NODE_STYLE if l in node.labels),
                list(node.labels)[0] if node.labels else "Unknown"
            )
            style = NODE_STYLE.get(label, {"color": "#888780", "label_prop": "id"})
            prop  = style["label_prop"]
            display = str(node.get(prop) or node.get("id") or nid)
            nodes[nid] = {
                "id":    nid,
                "label": display,
                "type":  label,
                "color": style["color"],
                "props": dict(node),
            }

        for rel in path.relationships:
            eid = str(rel.element_id)
            if eid in seen_edges:
                continue
            seen_edges.add(eid)
            edge_list.append({
                "id":     eid,
                "source": str(rel.start_node.element_id),
                "target": str(rel.end_node.element_id),
                "label":  rel.type,
            })

    # stats
    stat_rows = run_query(STATS_QUERY, {"site_id": site_id})
    stats = stat_rows[0].data() if stat_rows else {}

    return {
        "site_id": site_id,
        "stats":   stats,
        "nodes":   list(nodes.values()),
        "edges":   edge_list,
    }