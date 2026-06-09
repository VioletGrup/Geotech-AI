from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import re

from config import ALLOW_RAW_CYPHER
from app.graphrag.context_builder import build_context
from app.utils.logger import get_logger
from app.db.neo4j_driver import run_query
from app.graphrag.retrieve import get_dataset_summary, get_high_load_test, get_similar_cases


router = APIRouter()

@router.get("/query")
def query_graph(qc: float = None, soil_type: str = None):
    """Retrieves similar geotechnical cases from Neo4j"""
    if qc is None and soil_type is None:
        raise HTTPException(
            status_code = 400,
            detail = "Provide at least qc or soil type"
        )
    try: 
        results = get_similar_cases(qc or 0, soil_type)
        return {
            "query_inputs": {
                "qc": qc,
                "soil_type": soil_type
            },
            "results": results
        }
    
    except Exception as e:
        raise HTTPException(
            status_code = 500,
            detail = str(e)
        )
    


@router.post("/query/raw")
def run_raw_query(payload: dict):
    """Direct Neo4j query interface for debugging GraphRAG."""
    if "cypher" not in payload:
        raise HTTPException(
            status_code = 400,
            detail = "Missing 'cypher' field"
        )
    
    try:
        result = run_query(payload["cypher"], payload.get("params", {}))
        return {
            "result": [dict(record) for record in result]
        }

    except Exception as e:
        raise HTTPException(
            status_code = 500,
            detail = str(e)
        )