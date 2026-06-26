from typing import Any, Dict, List, Optional

from app.db.neo4j_driver import run_query

# ══════════════════════════════════════════════════════════════════════════════
# Schema v3 retrieval — zones, pile tests, DPSH refusals, ground profiles.
# Backs the Copilot agent tools (app/agent/tools.py).
# ══════════════════════════════════════════════════════════════════════════════

_ZONE_SUMMARY = """
MATCH (z:Zone {id: $zone_id})
OPTIONAL MATCH (p:PileTestLocation)-[:LOCATED_IN]->(z)
OPTIONAL MATCH (d:DPSHTest)-[:LOCATED_IN]->(z)
OPTIONAL MATCH (b:BoreHole)-[:LOCATED_IN]->(z)
OPTIONAL MATCH (tp:TestPit)-[:LOCATED_IN]->(z)
RETURN z.id                  AS zone,
       z.pre_drill_decision  AS pre_drill_decision,
       z.trackers_4string    AS trackers_4string,
       z.trackers_3string    AS trackers_3string,
       z.trackers_2string    AS trackers_2string,
       count(DISTINCT p)     AS pile_locations,
       count(DISTINCT d)     AS dpsh_probes,
       count(DISTINCT b)     AS boreholes,
       count(DISTINCT tp)    AS test_pits
"""

_PILE_TESTS = """
MATCH (loc:PileTestLocation)-[:HAS_TEST]->(t:PileTest)
OPTIONAL MATCH (loc)-[:LOCATED_IN]->(z:Zone)
WITH loc, t, z
WHERE ($zone_id IS NULL OR z.id = $zone_id)
  AND ($passed IS NULL OR t.passed = $passed)
OPTIONAL MATCH (t)-[:HAS_TENSION_TEST]->(ten:TensionPileTest)
OPTIONAL MATCH (t)-[:HAS_LATERAL_TEST]->(lat:LateralPileTest)
OPTIONAL MATCH (t)-[:HAS_COMPRESSION_TEST]->(comp:CompressionPileTest)
RETURN loc.id AS pile, z.id AS zone, t.section_type AS section, t.passed AS passed,
       ten.max_load_proportion_ed  AS tension_pct,
       lat.max_load_proportion_ed  AS lateral_pct,
       comp.max_load_proportion_ed AS compression_pct
LIMIT $top_k
"""

_DPSH_REFUSALS = """
MATCH (d:DPSHTest)
OPTIONAL MATCH (d)-[:LOCATED_IN]->(z:Zone)
WITH d, z
WHERE ($zone_id IS NULL OR z.id = $zone_id)
  AND ($max_depth IS NULL OR d.refusal_depth <= $max_depth)
RETURN d.id AS dpsh, z.id AS zone, d.refusal_depth AS refusal_depth
ORDER BY d.refusal_depth ASC
LIMIT $top_k
"""

_GROUND_PROFILE = """
MATCH (loc {id: $location_id}) WHERE loc:BoreHole OR loc:TestPit
OPTIONAL MATCH (loc)-[:HAS_GROUND_MODEL]->(:GroundModel)-[:HAS_LAYER]->(l:GroundLayer)
OPTIONAL MATCH (l)-[:OF_MATERIAL]->(s:SoilType)
WITH loc, l, collect(DISTINCT s.unit_no) AS soil_units, collect(DISTINCT s.unit_name) AS soil_names
RETURN loc.id AS location, head(labels(loc)) AS kind,
       l.start_depth AS start_depth, l.end_depth AS end_depth,
       soil_units AS soil_units, soil_names AS soil_names
ORDER BY l.start_depth ASC
"""

_PILE_REFUSALS = """
MATCH (p:PileTestLocation)
OPTIONAL MATCH (p)-[:LOCATED_IN]->(z:Zone)
WITH p, z
WHERE p.achieved_embedment IS NOT NULL AND p.target_depth IS NOT NULL
  AND p.achieved_embedment < p.target_depth
  AND ($zone_id IS NULL OR z.id = $zone_id)
RETURN p.id AS pile, z.id AS zone, p.driving_type AS driving_type,
       p.target_depth AS target_depth, p.achieved_embedment AS achieved_embedment,
       round(p.target_depth - p.achieved_embedment, 3) AS shortfall
ORDER BY shortfall DESC
LIMIT $top_k
"""


def get_zone_summary(zone_id: str) -> List[Dict[str, Any]]:
    return [r.data() for r in run_query(_ZONE_SUMMARY, {"zone_id": zone_id})]


def get_pile_tests(zone_id: Optional[str] = None, passed: Optional[bool] = None,
                   top_k: int = 25) -> List[Dict[str, Any]]:
    return [r.data() for r in run_query(
        _PILE_TESTS, {"zone_id": zone_id, "passed": passed, "top_k": int(top_k)})]


def get_dpsh_refusals(zone_id: Optional[str] = None, max_depth: Optional[float] = None,
                      top_k: int = 50) -> List[Dict[str, Any]]:
    return [r.data() for r in run_query(
        _DPSH_REFUSALS, {"zone_id": zone_id, "max_depth": max_depth, "top_k": int(top_k)})]


def get_ground_profile(location_id: str) -> List[Dict[str, Any]]:
    return [r.data() for r in run_query(_GROUND_PROFILE, {"location_id": location_id})]


def get_pile_refusals(zone_id: Optional[str] = None, top_k: int = 50) -> List[Dict[str, Any]]:
    return [r.data() for r in run_query(_PILE_REFUSALS, {"zone_id": zone_id, "top_k": int(top_k)})]


# ── Legacy capacity-prediction retrieval (kept for routes_predict / ml.model) ──
# Targets the old synthetic labels; not used by the v3 Copilot.

_SIMILAR_CASES = """
MATCH (c:CPTTest)-[:REPRESENTS]->(s:SoilLayer)<-[:INTERSECTS]-(p:Pile)
MATCH (p)-[:HAS_LOAD_TEST]->(t:PileLoadTest)
WHERE ($qc = 0 OR (c.qc >= $qc - 2000 AND c.qc <= $qc + 2000))
  AND ($soil_type IS NULL OR s.soil_type = $soil_type)
  AND ($pile_type IS NULL OR p.type = $pile_type)
RETURN p.id AS pile_id, p.type AS pile_type, p.diameter AS diameter, p.length AS length,
       c.qc AS qc, s.soil_type AS soil_type, t.max_load AS max_load
ORDER BY abs(coalesce(c.qc, 0) - $qc)
LIMIT $top_k
"""

_TRAINING_ROWS = """
MATCH (c:CPTTest)-[:REPRESENTS]->(s:SoilLayer)<-[:INTERSECTS]-(p:Pile)
MATCH (p)-[:HAS_LOAD_TEST]->(t:PileLoadTest)
WHERE t.max_load IS NOT NULL
RETURN p.id AS pile_id, t.id AS test_id, p.type AS pile_type, s.soil_type AS soil_type,
       p.diameter AS diameter, p.length AS length, c.depth AS depth, c.qc AS qc,
       c.fs AS fs, t.max_load AS target
"""


def get_similar_cases(qc: Optional[float] = 0, soil_type: Optional[str] = None,
                      diameter: Optional[float] = None, length: Optional[float] = None,
                      pile_type: Optional[str] = None, site_id: Optional[str] = None,
                      top_k: int = 10) -> List[Dict[str, Any]]:
    params = {"qc": float(qc or 0), "soil_type": soil_type, "pile_type": pile_type,
              "top_k": int(top_k or 10)}
    return [record.data() for record in run_query(_SIMILAR_CASES, params)]


def get_training_rows() -> List[Dict[str, Any]]:
    return [record.data() for record in run_query(_TRAINING_ROWS)]