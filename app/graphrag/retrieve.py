from typing import Any, Dict, List, Optional

from app.db.neo4j_driver import run_query

# ══════════════════════════════════════════════════════════════════════════════
# Schema v4 retrieval  —  all queries scoped through the Site node so ids only
# need to be unique within a site, not globally.
# ══════════════════════════════════════════════════════════════════════════════

# ── Database-wide discovery ────────────────────────────────────────────────────

_LIST_SITES = """
MATCH (s:Site)
OPTIONAL MATCH (s)-[:HAS_ZONE]->(z:Zone)
RETURN s.id      AS site_id,
       s.name    AS name,
       s.status  AS status,
       count(DISTINCT z) AS zone_count
ORDER BY s.name
"""

_DB_SUMMARY = """
MATCH (s:Site)
OPTIONAL MATCH (s)-[:HAS_ZONE]->(z:Zone)
OPTIONAL MATCH (p:PileTestLocation)-[:LOCATED_IN]->(z)
OPTIONAL MATCH (d:DPSHTest)-[:LOCATED_IN]->(z)
OPTIONAL MATCH (b:BoreHole)-[:LOCATED_IN]->(z)
OPTIONAL MATCH (tp:TestPit)-[:LOCATED_IN]->(z)
RETURN count(DISTINCT s)  AS total_sites,
       count(DISTINCT z)  AS total_zones,
       count(DISTINCT p)  AS total_pile_locations,
       count(DISTINCT d)  AS total_dpsh,
       count(DISTINCT b)  AS total_boreholes,
       count(DISTINCT tp) AS total_test_pits
"""

_DB_SOIL_TYPES = """
MATCH (st: SoilType)
RETURN  st.unit_no         AS unit_no,
        st.unit_name            AS name,
        st.description     AS description
"""
# ── Site-level counts ──────────────────────────────────────────────────────────

_SITE_COUNTS = """
MATCH (s:Site {id: $site_id})
OPTIONAL MATCH (s)-[:HAS_ZONE]->(z:Zone)
OPTIONAL MATCH (p:PileTestLocation)-[:LOCATED_IN]->(z)
OPTIONAL MATCH (pt:PileTest)<-[:HAS_TEST]-(p)
OPTIONAL MATCH (d:DPSHTest)-[:LOCATED_IN]->(z)
OPTIONAL MATCH (b:BoreHole)-[:LOCATED_IN]->(z)
OPTIONAL MATCH (tp:TestPit)-[:LOCATED_IN]->(z)
RETURN s.id   AS site_id,
       s.name AS site_name,
       s.status AS status,
       count(DISTINCT z)  AS zones,
       count(DISTINCT p)  AS pile_locations,
       count(DISTINCT pt) AS pile_tests,
       count(DISTINCT d)  AS dpsh_probes,
       count(DISTINCT b)  AS boreholes,
       count(DISTINCT tp) AS test_pits
"""

_LIST_ZONES = """
MATCH (s:Site {id: $site_id})-[:HAS_ZONE]->(z:Zone {site_id: $site_id})
OPTIONAL MATCH (p:PileTestLocation)-[:LOCATED_IN]->(z)
OPTIONAL MATCH (d:DPSHTest)-[:LOCATED_IN]->(z)
OPTIONAL MATCH (b:BoreHole)-[:LOCATED_IN]->(z)
OPTIONAL MATCH (tp:TestPit)-[:LOCATED_IN]->(z)
RETURN z.id                 AS zone_id,
       z.pre_drill_decision AS decision,
       count(DISTINCT p)    AS pile_locations,
       count(DISTINCT d)    AS dpsh_probes,
       count(DISTINCT b)    AS boreholes,
       count(DISTINCT tp)   AS test_pits
ORDER BY z.id
"""

_ZONES_BY_DECISION = """
MATCH (s:Site {id: $site_id})-[:HAS_ZONE]->(z:Zone {site_id: $site_id})
WHERE z.pre_drill_decision = $decision
  OR ($decision IS NULL AND z.pre_drill_decision IS NULL)
RETURN z.id AS zone_id, z.pre_drill_decision AS decision
ORDER BY z.id
"""

_ZONE_PILE_COUNT = """"
MATCH (s:Site {id: $site_id})-[:HAS_ZONE]->(z:Zone {id: $zone_id, site_id: $site_id})
MATCH (p:PileTestLocation)-[:LOCATED_IN]->(z)
RETURN count(p) AS pile_count
"""

_ZONE_BOREHOLE_COUNT = """"
MATCH (s:Site {id: $site_id})-[:HAS_ZONE]->(z:Zone {id: $zone_id, site_id: $site_id})
MATCH (p:BoreHole)-[:LOCATED_IN]->(z)
RETURN count(p) AS borehole_count
"""

_ZONE_TESTPIT_COUNT = """"
MATCH (s:Site {id: $site_id})-[:HAS_ZONE]->(z:Zone {id: $zone_id, site_id: $site_id})
MATCH (p:TestPit)-[:LOCATED_IN]->(z)
RETURN count(p) AS testpit_count
"""

_ZONE_DPSH_COUNT = """"
MATCH (s:Site {id: $site_id})-[:HAS_ZONE]->(z:Zone {id: $zone_id, site_id: $site_id})
MATCH (p:DPSHTest)-[:LOCATED_IN]->(z)
RETURN count(p) AS dpsh_count
"""

# ── Pile refusal (short of target embedment) ───────────────────────────────────

_PILE_REFUSALS = """
MATCH (s:Site {id: $site_id})-[:HAS_ZONE]->(z:Zone {site_id: $site_id})
MATCH (p:PileTestLocation)-[:LOCATED_IN]->(z)
WHERE p.achieved_embedment IS NOT NULL
  AND p.target_depth IS NOT NULL
  AND p.achieved_embedment < p.target_depth
  AND ($zone_id IS NULL OR z.id = $zone_id)
RETURN p.id   AS pile,
       z.id   AS zone,
       p.driving_type       AS driving_type,
       p.target_depth       AS target_depth,
       p.achieved_embedment AS achieved_embedment,
       round(p.target_depth - p.achieved_embedment, 3) AS shortfall_m
ORDER BY shortfall_m DESC
LIMIT $top_k
"""

_PILE_REFUSAL_COUNT = """
MATCH (s:Site {id: $site_id})-[:HAS_ZONE]->(z:Zone {site_id: $site_id})
MATCH (p:PileTestLocation)-[:LOCATED_IN]->(z)
WHERE p.achieved_embedment IS NOT NULL
  AND p.target_depth IS NOT NULL
  AND p.achieved_embedment < p.target_depth
  AND ($zone_id IS NULL OR z.id = $zone_id)
RETURN count(p) AS n_refusals,
       round(avg(p.target_depth - p.achieved_embedment), 3) AS avg_shortfall_m,
       round(max(p.target_depth - p.achieved_embedment), 3) AS max_shortfall_m
"""

# ── Pile tests ─────────────────────────────────────────────────────────────────

_PILE_TESTS = """
MATCH (s:Site {id: $site_id})-[:HAS_ZONE]->(z:Zone {site_id: $site_id})
MATCH (loc:PileTestLocation)-[:LOCATED_IN]->(z)
MATCH (loc)-[:HAS_TEST]->(t:PileTest)
WHERE ($zone_id IS NULL OR z.id = $zone_id)
  AND ($passed  IS NULL OR t.passed = $passed)
OPTIONAL MATCH (t)-[:HAS_TENSION_TEST]->(ten:TensionPileTest)
OPTIONAL MATCH (t)-[:HAS_LATERAL_TEST]->(lat:LateralPileTest)
OPTIONAL MATCH (t)-[:HAS_COMPRESSION_TEST]->(comp:CompressionPileTest)
RETURN loc.id AS pile, z.id AS zone, t.section_type AS section, t.passed AS passed,
       ten.max_load_proportion_ed  AS tension_pct,
       lat.max_load_proportion_ed  AS lateral_pct,
       comp.max_load_proportion_ed AS compression_pct
LIMIT $top_k
"""

_PILE_TEST_SUMMARY = """
MATCH (s:Site {id: $site_id})-[:HAS_ZONE]->(z:Zone {site_id: $site_id})
MATCH (loc:PileTestLocation)-[:LOCATED_IN]->(z)
MATCH (loc)-[:HAS_TEST]->(t:PileTest)
WHERE ($zone_id IS NULL OR z.id = $zone_id)
RETURN count(t)                                          AS total_tests,
       count(CASE WHEN t.passed = true  THEN 1 END)     AS passed,
       count(CASE WHEN t.passed = false THEN 1 END)     AS failed,
       count(CASE WHEN t.passed IS NULL THEN 1 END)     AS undecided
"""

# ── DPSH refusals ──────────────────────────────────────────────────────────────

_DPSH_REFUSALS = """
MATCH (s:Site {id: $site_id})-[:HAS_ZONE]->(z:Zone {site_id: $site_id})
MATCH (d:DPSHTest)-[:LOCATED_IN]->(z)
WHERE ($zone_id  IS NULL OR z.id = $zone_id)
  AND ($max_depth IS NULL OR d.refusal_depth <= $max_depth)
RETURN d.id AS dpsh, z.id AS zone, d.refusal_depth AS refusal_depth
ORDER BY d.refusal_depth ASC
LIMIT $top_k
"""

# ── Zone detail ────────────────────────────────────────────────────────────────

_ZONE_SUMMARY = """
MATCH (s:Site {id: $site_id})-[:HAS_ZONE]->(z:Zone {id: $zone_id, site_id: $site_id})
OPTIONAL MATCH (p:PileTestLocation)-[:LOCATED_IN]->(z)
OPTIONAL MATCH (d:DPSHTest)-[:LOCATED_IN]->(z)
OPTIONAL MATCH (b:BoreHole)-[:LOCATED_IN]->(z)
OPTIONAL MATCH (tp:TestPit)-[:LOCATED_IN]->(z)
OPTIONAL MATCH (pt:PileTest)<-[:HAS_TEST]-(p)
RETURN z.id                 AS zone_id,
       z.pre_drill_decision AS decision,
       z.trackers_4string   AS trackers_4string,
       z.trackers_3string   AS trackers_3string,
       z.trackers_2string   AS trackers_2string,
       count(DISTINCT p)    AS pile_locations,
       count(DISTINCT pt)   AS pile_tests,
       count(DISTINCT d)    AS dpsh_probes,
       count(DISTINCT b)    AS boreholes,
       count(DISTINCT tp)   AS test_pits
"""

_ZONE_PILE_IDS = """
MATCH (s:Site {id: $site_id})-[:HAS_ZONE]->(z:Zone {id: $zone_id, site_id: $site_id})
MATCH (p:PileTestLocation)-[:LOCATED_IN]->(z)
RETURN p.id                AS pile_id
ORDER BY p.id
"""
_ZONE_NO_DECISION = """
MATCH (s:Site {id: site_id})-[:HAS_ZONE]->(z:Zone: {id: $zone_id, site_id: $site_id})
WHERE (z.pre-drilling) = None
RETURN z.id                 AS zone_id
"""

_UNDECIDED_ZONE_COUNT = """
MATCH (s:Site {id: $site_id})-[:HAS_ZONE]->(z:Zone {site_id: $site_id})
WHERE z.pre_drill_decision IS NULL
RETURN count(z) AS undecided_zones
"""


# ── Ground profile ─────────────────────────────────────────────────────────────

_GROUND_PROFILE = """
MATCH (s:Site {id: $site_id})-[:HAS_ZONE]->(z:Zone {site_id: $site_id})
MATCH (loc)-[:LOCATED_IN]->(z)
WHERE loc.id = $location_id AND (loc:BoreHole OR loc:TestPit)
OPTIONAL MATCH (loc)-[:HAS_GROUND_MODEL]->(:GroundModel)-[:HAS_LAYER]->(l:GroundLayer)
OPTIONAL MATCH (l)-[:OF_MATERIAL]->(st:SoilType)
WITH loc, l,
     collect(DISTINCT st.unit_no)   AS soil_units,
     collect(DISTINCT st.unit_name) AS soil_names
RETURN loc.id AS location, head(labels(loc)) AS kind,
       l.start_depth AS start_depth, l.end_depth AS end_depth,
       soil_units, soil_names
ORDER BY l.start_depth ASC
"""

# ══════════════════════════════════════════════════════════════════════════════
# Python functions
# ══════════════════════════════════════════════════════════════════════════════

def list_sites() -> List[Dict[str, Any]]:
    return [r.data() for r in run_query(_LIST_SITES, {})]

def get_db_summary() -> Dict[str, Any]:
    rows = run_query(_DB_SUMMARY, {})
    return rows[0].data() if rows else {}

def get_site_counts(site_id: str) -> Dict[str, Any]:
    rows = run_query(_SITE_COUNTS, {"site_id": site_id})
    return rows[0].data() if rows else {}

def list_zones(site_id: str) -> List[Dict[str, Any]]:
    return [r.data() for r in run_query(_LIST_ZONES, {"site_id": site_id})]

def get_zones_by_decision(site_id: str,
                          decision: Optional[str]) -> List[Dict[str, Any]]:
    return [r.data() for r in run_query(
        _ZONES_BY_DECISION, {"site_id": site_id, "decision": decision})]

def get_zone_summary(site_id: str, zone_id: str) -> Dict[str, Any]:
    rows = run_query(_ZONE_SUMMARY, {"site_id": site_id, "zone_id": zone_id})
    return rows[0].data() if rows else {}

def get_pile_tests(site_id: str,
                   zone_id: Optional[str] = None,
                   passed: Optional[bool] = None,
                   top_k: int = 25) -> List[Dict[str, Any]]:
    return [r.data() for r in run_query(
        _PILE_TESTS,
        {"site_id": site_id, "zone_id": zone_id,
         "passed": passed, "top_k": int(top_k)})]

def get_pile_test_summary(site_id: str,
                          zone_id: Optional[str] = None) -> Dict[str, Any]:
    rows = run_query(_PILE_TEST_SUMMARY,
                     {"site_id": site_id, "zone_id": zone_id})
    return rows[0].data() if rows else {}

def get_dpsh_refusals(site_id: str,
                      zone_id: Optional[str] = None,
                      max_depth: Optional[float] = None,
                      top_k: int = 50) -> List[Dict[str, Any]]:
    return [r.data() for r in run_query(
        _DPSH_REFUSALS,
        {"site_id": site_id, "zone_id": zone_id,
         "max_depth": max_depth, "top_k": int(top_k)})]

def get_pile_refusals(site_id: str,
                      zone_id: Optional[str] = None,
                      top_k: int = 100) -> List[Dict[str, Any]]:
    return [r.data() for r in run_query(
        _PILE_REFUSALS,
        {"site_id": site_id, "zone_id": zone_id, "top_k": int(top_k)})]

def get_pile_refusal_count(site_id: str,
                           zone_id: Optional[str] = None) -> Dict[str, Any]:
    rows = run_query(_PILE_REFUSAL_COUNT,
                     {"site_id": site_id, "zone_id": zone_id})
    return rows[0].data() if rows else {}

def get_ground_profile(site_id: str, location_id: str) -> List[Dict[str, Any]]:
    return [r.data() for r in run_query(
        _GROUND_PROFILE, {"site_id": site_id, "location_id": location_id})]

def get_zones_no_decision(site_id: str) -> List[Dict[str, Any]]:
    return [r.data for r in run_query(
        _ZONE_NO_DECISION, {"site_id": site_id}
    )]

def get_undecided_zone_count(site_id: str) -> Dict[str, Any]:
    rows = run_query(_UNDECIDED_ZONE_COUNT, {"site_id": site_id})
    return rows[0].data() if rows else {"undecided_zones": 0}

def get_zone_pile_ids(site_id: str, zone_id: str) -> Dict[str, Any]:
    return [r.data() for r in run_query(
        _ZONE_PILE_IDS, {"site_id": site_id, "zone_id": zone_id}
    )]

def get_db_soil_types() -> List[Dict[str, Any]]:
    return [r.data() for r in run_query(_DB_SOIL_TYPES, {})]

def get_zone_pile_count(site_id: str, zone_id: str) -> Dict[str, Any]:
    rows = run_query(_ZONE_PILE_COUNT, {"site_id": site_id, "zone_id": zone_id})
    return rows[0].data() if rows else {"pile_count": 0}

def get_zone_borehole_count(site_id: str, zone_id: str) -> Dict[str, Any]:
    rows = run_query(_ZONE_BOREHOLE_COUNT, {"site_id": site_id, "zone_id": zone_id})
    return rows[0].data() if rows else {"borehole_count": 0}

def get_zone_testpit_count(site_id: str, zone_id: str) -> Dict[str, Any]:
    rows = run_query(_ZONE_TESTPIT_COUNT, {"site_id": site_id, "zone_id": zone_id})
    return rows[0].data() if rows else {"testpit_count": 0}

def get_zone_dpsh_count(site_id: str, zone_id: str) -> Dict[str, Any]:
    rows = run_query(_ZONE_DPSH_COUNT, {"site_id": site_id, "zone_id": zone_id})
    return rows[0].data() if rows else {"dpsh_count": 0}

# ── Legacy capacity-prediction retrieval (kept for routes_predict / ml) ────────

_SIMILAR_CASES = """
MATCH (c:CPTTest)-[:REPRESENTS]->(s:SoilLayer)<-[:INTERSECTS]-(p:Pile)
MATCH (p)-[:HAS_LOAD_TEST]->(t:PileLoadTest)
WHERE ($qc = 0 OR (c.qc >= $qc - 2000 AND c.qc <= $qc + 2000))
  AND ($soil_type IS NULL OR s.soil_type = $soil_type)
  AND ($pile_type IS NULL OR p.type = $pile_type)
RETURN p.id AS pile_id, p.type AS pile_type, p.diameter AS diameter, p.length AS length,
       c.qc AS qc, s.soil_type AS soil_type, t.max_load AS max_load
ORDER BY abs(coalesce(c.qc, 0) - $qc) LIMIT $top_k
"""

_TRAINING_ROWS = """
MATCH (c:CPTTest)-[:REPRESENTS]->(s:SoilLayer)<-[:INTERSECTS]-(p:Pile)
MATCH (p)-[:HAS_LOAD_TEST]->(t:PileLoadTest)
WHERE t.max_load IS NOT NULL
RETURN p.id AS pile_id, t.id AS test_id, p.type AS pile_type, s.soil_type AS soil_type,
       p.diameter AS diameter, p.length AS length,
       c.depth AS depth, c.qc AS qc, c.fs AS fs, t.max_load AS target
"""

def get_similar_cases(qc: Optional[float] = 0, soil_type: Optional[str] = None,
                      diameter=None, length=None, pile_type=None,
                      site_id=None, top_k: int = 10) -> List[Dict[str, Any]]:
    return [r.data() for r in run_query(
        _SIMILAR_CASES,
        {"qc": float(qc or 0), "soil_type": soil_type,
         "pile_type": pile_type, "top_k": int(top_k or 10)})]

def get_training_rows() -> List[Dict[str, Any]]:
    return [r.data() for r in run_query(_TRAINING_ROWS)]