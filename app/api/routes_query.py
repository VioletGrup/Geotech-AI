from typing import Optional

from fastapi import APIRouter, HTTPException

from app.config import ALLOW_RAW_CYPHER
from app.db.neo4j_driver import run_query
from app.graphrag.retrieve import get_similar_cases, get_all_cases

router = APIRouter(tags=["query"])


@router.get("/query")
def query_graph(qc: Optional[float] = None, soil_type: Optional[str] = None):
    """Retrieve similar geotechnical cases from Neo4j."""
    if qc is None and soil_type is None:
        raise HTTPException(status_code=400, detail="Provide at least qc or soil_type")
    try:
        results = get_similar_cases(qc=qc or 0, soil_type=soil_type)
        return {"query_inputs": {"qc": qc, "soil_type": soil_type}, "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/query/raw")
def run_raw_query(payload: dict):
    """Direct Neo4j query interface for debugging GraphRAG (disabled by default)."""
    if not ALLOW_RAW_CYPHER:
        raise HTTPException(
            status_code=403,
            detail="Raw Cypher is disabled. Set ALLOW_RAW_CYPHER=true to enable.",
        )
    if "cypher" not in payload:
        raise HTTPException(status_code=400, detail="Missing 'cypher' field")
    try:
        result = run_query(payload["cypher"], payload.get("params", {}))
        return {"result": [record.data() for record in result]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cases")
def list_cases(limit: int = 200):
    """List all logged pile cases, newest/highest-load first."""
    try:
        return {"results": get_all_cases(limit=limit)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))