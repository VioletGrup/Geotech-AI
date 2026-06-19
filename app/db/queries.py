"""Cypher for the Add-data write path (schema v3).

Each node create MERGEs the node, sets a property bag, and wires its
foreign-key relationships in the same statement, so the frontend only needs
node forms (no separate relationship tabs). Idempotent via MERGE.

Retrieval queries for the Copilot agent live in app/graphrag/retrieve.py.
"""

# ── Site ──────────────────────────────────────────────────────────────────────

def upsert_site():
    return """
    MERGE (s:Site {id: $id})
    SET s += $props
    RETURN s
    """

# ── Zone (block / PCU) — linked to a Site ─────────────────────────────────────

def upsert_zone():
    return """
    MERGE (z:Zone {id: $id})
    SET z += $props
    WITH z
    OPTIONAL MATCH (s:Site {id: $site_id})
    FOREACH (_ IN CASE WHEN s IS NULL THEN [] ELSE [1] END | MERGE (s)-[:HAS_ZONE]->(z))
    RETURN z
    """

# ── PileTestLocation — LOCATED_IN a Zone ──────────────────────────────────────

def upsert_pile_test_location():
    return """
    MERGE (p:PileTestLocation {id: $id})
    SET p += $props
    WITH p
    OPTIONAL MATCH (z:Zone {id: $zone_id})
    FOREACH (_ IN CASE WHEN z IS NULL THEN [] ELSE [1] END | MERGE (p)-[:LOCATED_IN]->(z))
    RETURN p
    """

# ── PileTest (container) — HAS_TEST from a PileTestLocation ───────────────────
# Holds section_type + passed; the three typed sub-tests hang off it.

def upsert_pile_test():
    return """
    MERGE (t:PileTest {id: $id})
    SET t += $props
    WITH t
    OPTIONAL MATCH (p:PileTestLocation {id: $pile_location_id})
    FOREACH (_ IN CASE WHEN p IS NULL THEN [] ELSE [1] END | MERGE (p)-[:HAS_TEST]->(t))
    RETURN t
    """

# ── Typed sub-tests — each hangs off a PileTest ───────────────────────────────

def upsert_tension_test():
    return """
    MATCH (pt:PileTest {id: $pile_test_id})
    MERGE (t:TensionPileTest {id: $id})
    SET t += $props
    MERGE (pt)-[:HAS_TENSION_TEST]->(t)
    RETURN t
    """

def upsert_lateral_test():
    return """
    MATCH (pt:PileTest {id: $pile_test_id})
    MERGE (t:LateralPileTest {id: $id})
    SET t += $props
    MERGE (pt)-[:HAS_LATERAL_TEST]->(t)
    RETURN t
    """

def upsert_compression_test():
    return """
    MATCH (pt:PileTest {id: $pile_test_id})
    MERGE (t:CompressionPileTest {id: $id})
    SET t += $props
    MERGE (pt)-[:HAS_COMPRESSION_TEST]->(t)
    RETURN t
    """

# ── DPSHTest — LOCATED_IN a Zone ──────────────────────────────────────────────

def upsert_dpsh():
    return """
    MERGE (d:DPSHTest {id: $id})
    SET d += $props
    WITH d
    OPTIONAL MATCH (z:Zone {id: $zone_id})
    FOREACH (_ IN CASE WHEN z IS NULL THEN [] ELSE [1] END | MERGE (d)-[:LOCATED_IN]->(z))
    RETURN d
    """

# ── BoreHole — LOCATED_IN a Zone ──────────────────────────────────────────────

def upsert_borehole():
    return """
    MERGE (b:BoreHole {id: $id})
    SET b += $props
    WITH b
    OPTIONAL MATCH (z:Zone {id: $zone_id})
    FOREACH (_ IN CASE WHEN z IS NULL THEN [] ELSE [1] END | MERGE (b)-[:LOCATED_IN]->(z))
    RETURN b
    """

# ── TestPit — LOCATED_IN a Zone ───────────────────────────────────────────────

def upsert_testpit():
    return """
    MERGE (t:TestPit {id: $id})
    SET t += $props
    WITH t
    OPTIONAL MATCH (z:Zone {id: $zone_id})
    FOREACH (_ IN CASE WHEN z IS NULL THEN [] ELSE [1] END | MERGE (t)-[:LOCATED_IN]->(z))
    RETURN t
    """

# ── SoilType (material vocabulary) ────────────────────────────────────────────

def upsert_soil_type():
    return """
    MERGE (s:SoilType {unit_name: $unit_name})
    SET s += $props
    RETURN s
    """

# ── GroundModel — HAS_GROUND_MODEL from a BoreHole or TestPit ─────────────────

def upsert_ground_model():
    return """
    MERGE (g:GroundModel {id: $id})
    WITH g
    OPTIONAL MATCH (loc {id: $location_id}) WHERE loc:BoreHole OR loc:TestPit
    FOREACH (_ IN CASE WHEN loc IS NULL THEN [] ELSE [1] END | MERGE (loc)-[:HAS_GROUND_MODEL]->(g))
    RETURN g
    """

# ── GroundLayer — HAS_LAYER from GroundModel, OF_MATERIAL to SoilType ──────────

def upsert_ground_layer():
    return """
    MATCH (g:GroundModel {id: $ground_model_id})
    MERGE (l:GroundLayer {id: $id})
    SET l += $props
    MERGE (g)-[:HAS_LAYER]->(l)
    WITH l
    OPTIONAL MATCH (s:SoilType {unit_name: $soil_unit_name})
    FOREACH (_ IN CASE WHEN s IS NULL THEN [] ELSE [1] END | MERGE (l)-[:OF_MATERIAL]->(s))
    RETURN l
    """

# ── ThermalResistivityTest — HAS_THERMAL_TEST from a TestPit ──────────────────

def upsert_thermal_test():
    return """
    MATCH (tp:TestPit {id: $testpit_id})
    MERGE (x:ThermalResistivityTest {id: $id})
    SET x += $props
    MERGE (tp)-[:HAS_THERMAL_TEST]->(x)
    RETURN x
    """

# ── LaboratoryTest — HAS_LAB_TEST from BoreHole|TestPit, OF_MATERIAL optional ──

def upsert_lab_test():
    return """
    MATCH (loc {id: $location_id}) WHERE loc:BoreHole OR loc:TestPit
    MERGE (t:LaboratoryTest {id: $id})
    SET t += $props
    MERGE (loc)-[:HAS_LAB_TEST]->(t)
    WITH t
    OPTIONAL MATCH (s:SoilType {unit_name: $soil_unit_name})
    FOREACH (_ IN CASE WHEN s IS NULL THEN [] ELSE [1] END | MERGE (t)-[:OF_MATERIAL]->(s))
    RETURN t
    """

# ── SoilAggressivity — HAS_AGGRESSIVITY_TEST from BoreHole|TestPit ────────────

def upsert_aggressivity():
    return """
    MATCH (loc {id: $location_id}) WHERE loc:BoreHole OR loc:TestPit
    MERGE (a:SoilAggressivity {id: $id})
    SET a += $props
    MERGE (loc)-[:HAS_AGGRESSIVITY_TEST]->(a)
    RETURN a
    """