"""
routes_delete.py — safe site deletion.

DELETE /sites/{site_id}

Removes a site and everything that belongs exclusively to it. Nodes that are
shared with other sites (SoilType, GroundModel referenced from another site's
boreholes, etc.) are left untouched.

Deletion order (innermost → outermost to avoid orphans):
  sub-tests → PileTest → PileTestLocation
  ThermalResistivityTest → LaboratoryTest → SoilAggressivity
  GroundLayer (only if its GroundModel belongs only to this site)
  GroundModel (only if it has no remaining HAS_LAYER or HAS_GROUND_MODEL
               relationship to a location outside this site)
  DPSHTest → BoreHole → TestPit
  Zone → Site

SoilType nodes are NEVER deleted (they are a global vocabulary).
"""
from fastapi import APIRouter, HTTPException
from app.db.neo4j_driver import run_query
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["delete"])


# ── helpers ────────────────────────────────────────────────────────────────────

def _run(cypher: str, params: dict | None = None) -> list:
    return list(run_query(cypher, params or {}))


def _count(cypher: str, params: dict | None = None) -> int:
    rows = _run(cypher, params)
    return rows[0][0] if rows else 0


# ── route ──────────────────────────────────────────────────────────────────────

@router.get("/sites")
def list_sites():
    """Return all sites with zone + node counts for the management UI."""
    rows = _run("""
        MATCH (s:Site)
        OPTIONAL MATCH (s)-[:HAS_ZONE]->(z:Zone)
        OPTIONAL MATCH (p:PileTestLocation)-[:LOCATED_IN]->(z)
        OPTIONAL MATCH (d:DPSHTest)-[:LOCATED_IN]->(z)
        OPTIONAL MATCH (b:BoreHole)-[:LOCATED_IN]->(z)
        OPTIONAL MATCH (tp:TestPit)-[:LOCATED_IN]->(z)
        RETURN s.id AS site_id, s.name AS name,
               count(DISTINCT z)  AS zones,
               count(DISTINCT p)  AS pile_locations,
               count(DISTINCT d)  AS dpsh_probes,
               count(DISTINCT b)  AS boreholes,
               count(DISTINCT tp) AS test_pits
        ORDER BY s.name
    """)
    return [r.data() for r in rows]


@router.delete("/sites/{site_id}")
def delete_site(site_id: str):
    """
    Permanently delete a site and all data that belongs only to it.
    Shared nodes (SoilType, GroundModel used by other sites) are preserved.
    """
    # ── verify site exists ────────────────────────────────────────────────────
    exists = _run("MATCH (s:Site {id: $id}) RETURN s.id", {"id": site_id})
    if not exists:
        raise HTTPException(404, f"Site '{site_id}' not found")

    deleted = {}

    # ── 1. pile sub-tests ─────────────────────────────────────────────────────
    for label, rel in [
        ("TensionPileTest",      "HAS_TENSION_TEST"),
        ("LateralPileTest",      "HAS_LATERAL_TEST"),
        ("CompressionPileTest",  "HAS_COMPRESSION_TEST"),
    ]:
        r = _run(f"""
            MATCH (s:Site {{id: $sid}})-[:HAS_ZONE]->(z:Zone)
            MATCH (loc:PileTestLocation)-[:LOCATED_IN]->(z)
            MATCH (loc)-[:HAS_TEST]->(pt:PileTest)-[:{rel}]->(sub:{label})
            DETACH DELETE sub RETURN count(sub) AS n
        """, {"sid": site_id})
        deleted[label] = r[0]["n"] if r else 0

    # ── 2. PileTest containers ────────────────────────────────────────────────
    r = _run("""
        MATCH (s:Site {id: $sid})-[:HAS_ZONE]->(z:Zone)
        MATCH (loc:PileTestLocation)-[:LOCATED_IN]->(z)
        MATCH (loc)-[:HAS_TEST]->(pt:PileTest)
        DETACH DELETE pt RETURN count(pt) AS n
    """, {"sid": site_id})
    deleted["PileTest"] = r[0]["n"] if r else 0

    # ── 3. PileTestLocation ───────────────────────────────────────────────────
    r = _run("""
        MATCH (s:Site {id: $sid})-[:HAS_ZONE]->(z:Zone)
        MATCH (loc:PileTestLocation)-[:LOCATED_IN]->(z)
        DETACH DELETE loc RETURN count(loc) AS n
    """, {"sid": site_id})
    deleted["PileTestLocation"] = r[0]["n"] if r else 0

    # ── 4. Tests attached to BoreHole / TestPit ───────────────────────────────
    for label, rel in [
        ("ThermalResistivityTest", "HAS_THERMAL_TEST"),
        ("LaboratoryTest",         "HAS_LAB_TEST"),
        ("SoilAggressivity",       "HAS_AGGRESSIVITY_TEST"),
    ]:
        r = _run(f"""
            MATCH (s:Site {{id: $sid}})-[:HAS_ZONE]->(z:Zone)
            MATCH (loc)-[:LOCATED_IN]->(z) WHERE loc:BoreHole OR loc:TestPit
            MATCH (loc)-[:{rel}]->(t:{label})
            DETACH DELETE t RETURN count(t) AS n
        """, {"sid": site_id})
        deleted[label] = r[0]["n"] if r else 0

    # ── 5. GroundLayers whose GroundModel belongs only to this site ───────────
    # A GroundModel is exclusive to this site when every HAS_GROUND_MODEL
    # relationship points to a BoreHole/TestPit inside this site's zones.
    r = _run("""
        MATCH (s:Site {id: $sid})-[:HAS_ZONE]->(z:Zone)
        MATCH (loc)-[:LOCATED_IN]->(z)-[:HAS_ZONE]-(s)
            WHERE loc:BoreHole OR loc:TestPit
        MATCH (loc)-[:HAS_GROUND_MODEL]->(gm:GroundModel)
        // confirm no outside reference
        WHERE NOT EXISTS {
            MATCH (gm)<-[:HAS_GROUND_MODEL]-(other)
            WHERE NOT (other)-[:LOCATED_IN]->(:Zone)<-[:HAS_ZONE]-(s)
        }
        MATCH (gm)-[:HAS_LAYER]->(gl:GroundLayer)
        DETACH DELETE gl RETURN count(gl) AS n
    """, {"sid": site_id})
    deleted["GroundLayer"] = r[0]["n"] if r else 0

    # ── 6. Exclusive GroundModels ─────────────────────────────────────────────
    r = _run("""
        MATCH (s:Site {id: $sid})-[:HAS_ZONE]->(z:Zone)
        MATCH (loc)-[:LOCATED_IN]->(z) WHERE loc:BoreHole OR loc:TestPit
        MATCH (loc)-[:HAS_GROUND_MODEL]->(gm:GroundModel)
        WHERE NOT EXISTS {
            MATCH (gm)<-[:HAS_GROUND_MODEL]-(other)
            WHERE NOT (other)-[:LOCATED_IN]->(:Zone)<-[:HAS_ZONE]-(s)
        }
        DETACH DELETE gm RETURN count(gm) AS n
    """, {"sid": site_id})
    deleted["GroundModel"] = r[0]["n"] if r else 0

    # ── 7. DPSH probes ────────────────────────────────────────────────────────
    r = _run("""
        MATCH (s:Site {id: $sid})-[:HAS_ZONE]->(z:Zone)
        MATCH (d:DPSHTest)-[:LOCATED_IN]->(z)
        DETACH DELETE d RETURN count(d) AS n
    """, {"sid": site_id})
    deleted["DPSHTest"] = r[0]["n"] if r else 0

    # ── 8. BoreHoles ─────────────────────────────────────────────────────────
    r = _run("""
        MATCH (s:Site {id: $sid})-[:HAS_ZONE]->(z:Zone)
        MATCH (b:BoreHole)-[:LOCATED_IN]->(z)
        DETACH DELETE b RETURN count(b) AS n
    """, {"sid": site_id})
    deleted["BoreHole"] = r[0]["n"] if r else 0

    # ── 9. TestPits ───────────────────────────────────────────────────────────
    r = _run("""
        MATCH (s:Site {id: $sid})-[:HAS_ZONE]->(z:Zone)
        MATCH (tp:TestPit)-[:LOCATED_IN]->(z)
        DETACH DELETE tp RETURN count(tp) AS n
    """, {"sid": site_id})
    deleted["TestPit"] = r[0]["n"] if r else 0

    # ── 10. Zones ─────────────────────────────────────────────────────────────
    r = _run("""
        MATCH (s:Site {id: $sid})-[:HAS_ZONE]->(z:Zone)
        DETACH DELETE z RETURN count(z) AS n
    """, {"sid": site_id})
    deleted["Zone"] = r[0]["n"] if r else 0

    # ── 11. Site itself ───────────────────────────────────────────────────────
    _run("MATCH (s:Site {id: $sid}) DETACH DELETE s", {"sid": site_id})
    deleted["Site"] = 1

    logger.info("Deleted site %s: %s", site_id, deleted)
    return {
        "message": f"Site '{site_id}' and all exclusive data deleted.",
        "deleted": deleted,
        "preserved": "SoilType nodes and any GroundModel shared with other sites are preserved.",
    }