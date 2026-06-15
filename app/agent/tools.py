from typing import Annotated, Optional

from pydantic import Field
from agent_framework import tool

from app.graphrag.retrieve import get_similar_cases
from app.graphrag.context_builder import build_context
from app.ml.model import ModelNotTrainedError, predict_capacity


@tool(
    description="Predict pile load capacity for a solar-farm pile from its "
    "geometry and CPT/soil inputs, grounded in similar logged cases. Returns "
    "the prediction, the analog cases behind it, and model_status."
)
def predict_pile_capacity(
    diameter: Annotated[float, Field(description="Pile diameter in metres", gt=0)],
    length: Annotated[float, Field(description="Pile length in metres", gt=0)],
    qc: Annotated[Optional[float], Field(description="CPT cone resistance (kPa)")] = None,
    soil_type: Annotated[Optional[str], Field(description="Soil class, e.g. clay/sand/silt")] = None,
    pile_type: Annotated[Optional[str], Field(description="Pile type/section")] = None,
    site_id: Annotated[Optional[str], Field(description="Site identifier")] = None,
    top_k: Annotated[int, Field(description="Number of analog cases to retrieve", ge=1, le=20)] = 5,
) -> dict:
    payload = {
        "diameter": diameter, "length": length, "qc": qc,
        "soil_type": soil_type, "pile_type": pile_type, "site_id": site_id,
    }
    cases = get_similar_cases(
        qc=qc or 0, soil_type=soil_type, diameter=diameter, length=length,
        pile_type=pile_type, site_id=site_id, top_k=top_k,
    )
    try:
        prediction = predict_capacity(payload)
    except ModelNotTrainedError:
        loads = [c["max_load"] for c in cases if c.get("max_load") is not None]
        if not loads:
            return {"error": "Model untrained and no similar cases available.", "inputs": payload}
        prediction = {
            "predicted_capacity": float(sum(loads) / len(loads)),
            "model_metrics": None,
            "model_status": "fallback_average_of_similar_cases",
        }
    return {
        **prediction,
        "n_cases": len(cases),
        "similar_cases": cases,
        "evidence_context": build_context(cases, payload),
    }


@tool(description="Retrieve logged pile cases similar in CPT resistance and soil type.")
def query_similar_cases(
    qc: Annotated[float, Field(description="CPT cone resistance (kPa)", ge=0)] = 0,
    soil_type: Annotated[Optional[str], Field(description="Soil class to match")] = None,
    top_k: Annotated[int, Field(description="Maximum cases to return", ge=1, le=20)] = 10,
) -> dict:
    return {"results": get_similar_cases(qc=qc, soil_type=soil_type, top_k=top_k)}