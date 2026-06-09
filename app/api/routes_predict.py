from fastapi import APIRouter
from app.ml.model import predict_capacity
from app.graphrag.retrieve import get_similar_cases

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