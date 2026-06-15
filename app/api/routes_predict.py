from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.db.neo4j_driver import Neo4jNotConfiguredError
from app.graphrag.context_builder import build_context
from app.graphrag.retrieve import get_similar_cases
from app.ml.model import ModelNotTrainedError, predict_capacity, train_model_from_graph
from app.utils.logger import get_logger
from app.utils.validators import validate_pile_input

router = APIRouter(prefix="/predict", tags=["predict"])
logger = get_logger(__name__)


class PredictRequest(BaseModel):
    diameter: float = Field(..., gt=0)
    length: float = Field(..., gt=0)
    depth: Optional[float] = Field(None, gt=0)
    qc: Optional[float] = Field(None, ge=0)
    fs: Optional[float] = Field(None, ge=0)
    pile_type: Optional[str] = None
    soil_type: Optional[str] = None
    site_id: Optional[str] = None
    top_k: int = Field(5, ge=1, le=20)


@router.post("")
def predict(request: PredictRequest):
    payload = request.model_dump()
    validate_pile_input(
        qc=payload.get("qc"),
        depth=payload.get("depth"),
        diameter=payload.get("diameter"),
        length=payload.get("length"),
        fs=payload.get("fs"),
    )

    try:
        similar_cases = get_similar_cases(
            qc=payload.get("qc") or 0,
            soil_type=payload.get("soil_type"),
            diameter=payload.get("diameter"),
            length=payload.get("length"),
            pile_type=payload.get("pile_type"),
            site_id=payload.get("site_id"),
            top_k=payload.get("top_k", 5),
        )
    except Neo4jNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=f"Database not configured: {exc}")
    except Exception as exc:
        logger.exception("Similar-case retrieval failed")
        raise HTTPException(status_code=502, detail=f"Graph query failed: {exc}")

    try:
        prediction = predict_capacity(payload)
    except ModelNotTrainedError:
        loads = [c["max_load"] for c in similar_cases if c.get("max_load") is not None]
        if not loads:
            raise HTTPException(
                status_code=503,
                detail="Prediction model is not trained and no similar cases exist for fallback.",
            )
        prediction = {
            "predicted_capacity": float(sum(loads) / len(loads)),
            "model_metrics": None,
            "model_status": "fallback_average_of_similar_cases",
        }
    except Exception as exc:
        logger.exception("Prediction failed")
        raise HTTPException(status_code=500, detail=str(exc))

    return {
        **prediction,
        "similar_cases": similar_cases,
        "evidence_context": build_context(similar_cases, payload),
    }


@router.post("/train")
def train_model():
    try:
        metrics = train_model_from_graph()
        return {"message": "Model trained successfully", "metrics": metrics}
    except Exception as exc:
        logger.exception("Model training failed")
        raise HTTPException(status_code=500, detail=str(exc))