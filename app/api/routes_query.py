from fastapi import APIRouter, HTTPException

from app.config import ALLOW_RAW_CYPHER
from app.db.neo4j_driver import run_query

router = APIRouter(tags=["query"])


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