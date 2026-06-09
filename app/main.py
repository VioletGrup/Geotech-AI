from fastapi import FastAPI
from app.api.routes_predict import router as predict_router
from app.api.routes_query import router as query_router
from app.api.routes_nodes import router as nodes_router

app = FastAPI(title="Geotech GraphRAG System")

app.include_router(predict_router)
app.include_router(query_router)
app.include_router(nodes_router)