import os

from dotenv import load_dotenv

load_dotenv()

APP_NAME = "Geotech AI"
ALLOW_RAW_CYPHER = os.getenv("ALLOW_RAW_CYPHER", "false").lower() in {"1", "true", "yes"}

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USER")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

# ML
MODEL_PATH = os.getenv("MODEL_PATH", "app/ml/model.joblib")
MIN_TRAINING_ROWS = int(os.getenv("MIN_TRAINING_ROWS", "10"))
RANDOM_STATE = int(os.getenv("RANDOM_STATE", "42"))

# ── Agent / LLM (configure ONE provider) ──────────────────────────────────────
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")

# GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
# GEMINI_BASE_URL = os.getenv(
#     "GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/"
# )

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1")

AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4.1")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_BASE_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")