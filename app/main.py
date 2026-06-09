from contextlib import asynccontextmanager

from fastapi import FastAPI

from config import APP_NAME
from app.utils.logger import get_logger
from app.db.neo4j_driver import Neo4jNotConfiguredError, verify_connectivity
from app.api.routes_nodes import router as nodes_router
from app.api.routes_predict import router as predict_router
from app.api.routes_query import router as query_router
from app.ingestion.schema import create_constraints

logger = get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        verify_connectivity()
        create_constraints()
        logger.info("Neo4j connectivity verified and schema prepared")
    except Neo4jNotConfiguredError:
        logger.warning("Neo4j is not configured yet. The API will start, but DB-backend endpoints will fail until env vars are set.")
    except Exception:
        logger.exception("Startup checks failed")
    yield

app = FastAPI(title = APP_NAME, version = "0.1.0", lifespan = lifespan)
app.include_router(nodes_router)
app.include_router(query_router)
app.include_router(predict_router)

@app.get("/")
def root():
    return {
        "message": "Geotech GraphRAG MVP is running",
        "routes": ["/nodes/*", "/query/*", "/predict/*"],
    }


@app.get("/health")
def health():
    return {"status": "ok"}
