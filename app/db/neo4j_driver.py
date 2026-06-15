from functools import lru_cache

from neo4j import GraphDatabase

from app.config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, NEO4J_DATABASE
from app.utils.logger import get_logger

logger = get_logger(__name__)


class Neo4jNotConfiguredError(RuntimeError):
    """Raised when Neo4j connection details are missing from the environment."""


def _configured() -> bool:
    return all([NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD])


@lru_cache(maxsize=1)
def get_driver():
    if not _configured():
        raise Neo4jNotConfiguredError(
            "NEO4J_URI / NEO4J_USER / NEO4J_PASSWORD are not set. "
            "Add them to your environment or .env file."
        )
    return GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))


def verify_connectivity() -> None:
    if not _configured():
        raise Neo4jNotConfiguredError("Neo4j environment variables are not set.")
    get_driver().verify_connectivity()


def run_query(query, params=None):
    driver = get_driver()
    with driver.session(database=NEO4J_DATABASE or None) as session:
        return list(session.run(query, params or {}))