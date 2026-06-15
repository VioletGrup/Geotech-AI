import os

from dotenv import load_dotenv

load_dotenv()

APP_NAME = "Geotech AI"
ALLOW_RAW_CYPHER = os.getenv("ALLOW_RAW_CYPHER", "false").lower() in {"1", "true", "yes"}

# Secrets come from the environment / .env (never commit these).
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USER")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

# ML
MODEL_PATH = os.getenv("MODEL_PATH", "app/ml/model.joblib")
MIN_TRAINING_ROWS = int(os.getenv("MIN_TRAINING_ROWS", "10"))
RANDOM_STATE = int(os.getenv("RANDOM_STATE", "42"))

# ── Agent / LLM (configure ONE provider) ──────────────────────────────────────
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1")

AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4.1")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21")