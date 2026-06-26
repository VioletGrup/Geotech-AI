"""
Schema v4 — multi-site uniqueness.

Global unique constraints:
  - Site.id          (one site per id across the whole db)
  - SoilType.unit_no (shared material vocabulary, global)

All other nodes (Zone, PileTestLocation, DPSHTest, BoreHole, TestPit,
PileTest, sub-tests, GroundModel, GroundLayer, lab/thermal/aggressivity)
are unique WITHIN a site only — enforced by the graph hierarchy
(Site→Zone→...) rather than a global constraint.

On startup this function drops all stale global constraints for those node
types and ensures only the two correct ones exist.
"""
from app.db.neo4j_driver import run_query
from app.utils.logger import get_logger

logger = get_logger(__name__)

_DROP = [
    "DROP CONSTRAINT zone_id                  IF EXISTS",
    "DROP CONSTRAINT pile_test_location_id    IF EXISTS",
    "DROP CONSTRAINT dpsh_id                  IF EXISTS",
    "DROP CONSTRAINT borehole_id              IF EXISTS",
    "DROP CONSTRAINT testpit_id               IF EXISTS",
    "DROP CONSTRAINT pile_test_id             IF EXISTS",
    "DROP CONSTRAINT tension_test_id          IF EXISTS",
    "DROP CONSTRAINT lateral_test_id          IF EXISTS",
    "DROP CONSTRAINT compression_test_id      IF EXISTS",
    "DROP CONSTRAINT thermal_test_id          IF EXISTS",
    "DROP CONSTRAINT lab_test_id              IF EXISTS",
    "DROP CONSTRAINT aggressivity_id          IF EXISTS",
    "DROP CONSTRAINT ground_model_id          IF EXISTS",
    "DROP CONSTRAINT ground_layer_id          IF EXISTS",
]

_KEEP = [
    "CREATE CONSTRAINT site_id       IF NOT EXISTS FOR (s:Site)     REQUIRE s.id      IS UNIQUE",
    "CREATE CONSTRAINT soil_type_unit IF NOT EXISTS FOR (s:SoilType) REQUIRE s.unit_no IS UNIQUE",
]


def create_constraints():
    for q in _DROP:
        try:
            run_query(q)
        except Exception as e:
            logger.debug("Drop skipped (%s): %s", q.split()[2], e)
    for q in _KEEP:
        run_query(q)
    logger.info("Schema v4: 2 global constraints (Site.id, SoilType.unit_no)")