from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from context_builder import build_context
from logger import get_logger
from model import ModelNotTrainedError, predict_capacity, train_model_from_graph
from retrieve import get_similar_cases
from validators import validate_pile_input

router = APIRouter()
logger = get_logger(__name__)


class PredictRequest(BaseModel):
    diameter: float = Field(..., gt=0)
    length: float = Field(..., gt=0)
    depth: Optional[float] = Field(None, gt=0)
    qc: Optional[float] = Field(None, ge=0)
    fs: Optional[float] = Field(None, ge=0)
    pile_type: Optional[str] = None
    soile_type: Optional[str] = None
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
        fs=payload.get("fs")
    )

    similar_cases = get_similar_cases(
        qc=payload.get("qc"),
        soil_type=payload.get("soil_type"),
        diameter=payload.get("diameter"),
        length=payload.get("length"),
        pile_type=payload.get("pile_type"),
        site_id=payload.get("site_id"),
        top_k=payload.get("top_k", 5)
    )

    try: 
        prediction = predict_capacity(payload)
    except ModelNotTrainedError:
        if not similar_cases:
            raise HTTPException(
                status_code = 503,
                detail = "Prediction model is not trained and there are no similar cases to use as a fallback.",
            )
        fallback_estimate = sum(case["max_load"] for case in similar_cases if case.get("max_load") is not None) / max(1, len([case for case in similar_cases if case.get("max_load") is not None]))
        prediction = {
            "predicted_capacity": float(fallback_estimate),
            "model_metrics": None,
            "model_status": "fallback_average_of_similar_cases",
        }
    except Exception as exc:
        logger.exception("Prediction failed")
        raise HTTPException(status_code=500, detail=str(exc))
    
    context = build_context(similar_cases, payload)
    return {
        **prediction,
        "similar_cases": similar_cases,
        "evidence_context": context,
    }

@router.post("/train")
def train_model():
    try:    
        metrics = train_model_from_graph()
        return {"message": "Model trained successfully", "metrics": metrics}
    except Exception as exc:
        logger.exception("Model training failed")
        raise HTTPException(status_code = 500, detail=str(exc))