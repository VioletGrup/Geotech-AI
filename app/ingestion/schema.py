from app.db.neo4j_driver import run_query
from app.utils.logger import get_logger

logger = get_logger(__name__)


def create_constraints():
    queries = [
        # ── Hierarchy ───────────────────────────────────────────────────────
        "CREATE CONSTRAINT site_id IF NOT EXISTS FOR (s:Site) REQUIRE s.id IS UNIQUE",
        "CREATE CONSTRAINT zone_id IF NOT EXISTS FOR (z:Zone) REQUIRE z.id IS UNIQUE",
        # ── Locations (in a zone) ───────────────────────────────────────────
        "CREATE CONSTRAINT pile_test_location_id IF NOT EXISTS FOR (p:PileTestLocation) REQUIRE p.id IS UNIQUE",
        "CREATE CONSTRAINT dpsh_id IF NOT EXISTS FOR (d:DPSHTest) REQUIRE d.id IS UNIQUE",
        "CREATE CONSTRAINT borehole_id IF NOT EXISTS FOR (b:BoreHole) REQUIRE b.id IS UNIQUE",
        "CREATE CONSTRAINT testpit_id IF NOT EXISTS FOR (t:TestPit) REQUIRE t.id IS UNIQUE",
        # ── Tests ───────────────────────────────────────────────────────────
        "CREATE CONSTRAINT pile_test_id IF NOT EXISTS FOR (t:PileTest) REQUIRE t.id IS UNIQUE",
        "CREATE CONSTRAINT thermal_test_id IF NOT EXISTS FOR (t:ThermalResistivityTest) REQUIRE t.id IS UNIQUE",
        "CREATE CONSTRAINT lab_test_id IF NOT EXISTS FOR (t:LaboratoryTest) REQUIRE t.id IS UNIQUE",
        "CREATE CONSTRAINT aggressivity_id IF NOT EXISTS FOR (a:SoilAggressivity) REQUIRE a.id IS UNIQUE",
        # ── Ground model ────────────────────────────────────────────────────
        "CREATE CONSTRAINT ground_model_id IF NOT EXISTS FOR (g:GroundModel) REQUIRE g.id IS UNIQUE",
        "CREATE CONSTRAINT ground_layer_id IF NOT EXISTS FOR (l:GroundLayer) REQUIRE l.id IS UNIQUE",
        "CREATE CONSTRAINT soil_type_unit IF NOT EXISTS FOR (s:SoilType) REQUIRE s.unit_name IS UNIQUE",
    ]

    for q in queries:
        run_query(q)

    print("Schema constraints created")