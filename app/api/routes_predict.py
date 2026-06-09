from fastapi import APIRouter
from typing import Optional 

from app.graphrag.context_builder import build_context
from app.utils.logger import get_logger
from app.ml.model import ModelNotTrainedError, predict_capacity, train_model_from_graph
from app.graphrag.retrieve import get_similar_cases
from app.utils.validators import validate_pile_input

router = APIRouter()

@router.get("/predict")
def predict(qc: float, depth: float, diameter: float):
    # ML Prediction
    capacity = predict_capacity(qc, depth, diameter)
    # GraphRAG Context
    similar_cases = get_similar_cases(qc)

    return {
        "predicted_capacity": capacity,
        "similar_cases": similar_cases
    }