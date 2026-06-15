from typing import Any, Dict, List, Optional

from app.db.neo4j_driver import run_query

# Relationship directions match app/db/queries.py:
#   (c:CPTTest)-[:REPRESENTS]->(s:SoilLayer)<-[:INTERSECTS]-(p:Pile)
#   (p:Pile)-[:HAS_LOAD_TEST]->(t:PileLoadTest)

_SIMILAR_CASES = """
MATCH (c:CPTTest)-[:REPRESENTS]->(s:SoilLayer)<-[:INTERSECTS]-(p:Pile)
MATCH (p)-[:HAS_LOAD_TEST]->(t:PileLoadTest)
WHERE ($qc = 0 OR (c.qc >= $qc - 2000 AND c.qc <= $qc + 2000))
  AND ($soil_type IS NULL OR s.soil_type = $soil_type)
  AND ($pile_type IS NULL OR p.type = $pile_type)
RETURN p.id        AS pile_id,
       p.type      AS pile_type,
       p.diameter  AS diameter,
       p.length    AS length,
       c.qc        AS qc,
       s.soil_type AS soil_type,
       t.max_load  AS max_load
ORDER BY abs(coalesce(c.qc, 0) - $qc)
LIMIT $top_k
"""

_TRAINING_ROWS = """
MATCH (c:CPTTest)-[:REPRESENTS]->(s:SoilLayer)<-[:INTERSECTS]-(p:Pile)
MATCH (p)-[:HAS_LOAD_TEST]->(t:PileLoadTest)
WHERE t.max_load IS NOT NULL
RETURN p.id        AS pile_id,
       t.id        AS test_id,
       p.type      AS pile_type,
       s.soil_type AS soil_type,
       p.diameter  AS diameter,
       p.length    AS length,
       c.depth     AS depth,
       c.qc        AS qc,
       c.fs        AS fs,
       t.max_load  AS target
"""


def get_similar_cases(
    qc: Optional[float] = 0,
    soil_type: Optional[str] = None,
    diameter: Optional[float] = None,
    length: Optional[float] = None,
    pile_type: Optional[str] = None,
    site_id: Optional[str] = None,
    top_k: int = 10,
) -> List[Dict[str, Any]]:
    """Return logged pile cases similar in CPT resistance / soil type.

    diameter, length and site_id are accepted for interface compatibility with
    the predict route; qc, soil_type and pile_type currently drive filtering.
    """
    params = {
        "qc": float(qc or 0),
        "soil_type": soil_type,
        "pile_type": pile_type,
        "top_k": int(top_k or 10),
    }
    return [record.data() for record in run_query(_SIMILAR_CASES, params)]


def get_training_rows() -> List[Dict[str, Any]]:
    """Return one row per logged load test for model training."""
    return [record.data() for record in run_query(_TRAINING_ROWS)]


_ALL_CASES = """
MATCH (p:Pile)-[:HAS_LOAD_TEST]->(t:PileLoadTest)
OPTIONAL MATCH (p)-[:INTERSECTS]->(s:SoilLayer)<-[:REPRESENTS]-(c:CPTTest)
RETURN p.id        AS pile_id,
       p.type      AS pile_type,
       p.diameter  AS diameter,
       p.length    AS length,
       c.qc        AS qc,
       s.soil_type AS soil_type,
       t.max_load  AS max_load
ORDER BY t.max_load DESC
LIMIT $limit
"""


def get_all_cases(limit: int = 200) -> List[Dict[str, Any]]:
    """Return all logged pile load-test cases (for the results browser)."""
    return [record.data() for record in run_query(_ALL_CASES, {"limit": int(limit)})]