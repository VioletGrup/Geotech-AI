"""
queries.py — Cypher write path (schema v4).

Retrieval queries live in app/graphrag/retrieve.py.
"""

# ── Site (globally unique) ────────────────────────────────────────────────────

def upsert_site():
    return """
    MERGE (s:Site {id: $id})
    SET s += $props
    RETURN s
    """

# ── Zone — scoped: MERGE by (id, site) ───────────────────────────────────────

def upsert_zone():
    return """
    MATCH (s:Site {id: $site_id})
    MERGE (z:Zone {id: $id, site_id: $site_id})
    SET z += $props
    MERGE (s)-[:HAS_ZONE]->(z)
    RETURN z
    """

# ── PileTestLocation — scoped under zone ─────────────────────────────────────

def upsert_pile_test_location():
    return """
    MATCH (s:Site {id: $site_id})-[:HAS_ZONE]->(z:Zone {id: $zone_id, site_id: $site_id})
    MERGE (p:PileTestLocation {id: $id, site_id: $site_id})
    SET p += $props
    MERGE (p)-[:LOCATED_IN]->(z)
    RETURN p
    """

# ── PileTest container ────────────────────────────────────────────────────────

def upsert_pile_test():
    return """
    MATCH (s:Site {id: $site_id})-[:HAS_ZONE]->(:Zone {site_id: $site_id})
          <-[:LOCATED_IN]-(p:PileTestLocation {id: $pile_location_id, site_id: $site_id})
    MERGE (t:PileTest {id: $id, site_id: $site_id})
    SET t += $props
    MERGE (p)-[:HAS_TEST]->(t)
    RETURN t
    """

# ── Typed sub-tests ───────────────────────────────────────────────────────────

def upsert_tension_test():
    return """
    MATCH (pt:PileTest {id: $pile_test_id, site_id: $site_id})
    MERGE (t:TensionPileTest {id: $id, site_id: $site_id})
    SET t += $props
    MERGE (pt)-[:HAS_TENSION_TEST]->(t)
    RETURN t
    """

def upsert_lateral_test():
    return """
    MATCH (pt:PileTest {id: $pile_test_id, site_id: $site_id})
    MERGE (t:LateralPileTest {id: $id, site_id: $site_id})
    SET t += $props
    MERGE (pt)-[:HAS_LATERAL_TEST]->(t)
    RETURN t
    """

def upsert_compression_test():
    return """
    MATCH (pt:PileTest {id: $pile_test_id, site_id: $site_id})
    MERGE (t:CompressionPileTest {id: $id, site_id: $site_id})
    SET t += $props
    MERGE (pt)-[:HAS_COMPRESSION_TEST]->(t)
    RETURN t
    """

# ── DPSHTest ──────────────────────────────────────────────────────────────────

def upsert_dpsh():
    return """
    MATCH (s:Site {id: $site_id})-[:HAS_ZONE]->(z:Zone {id: $zone_id, site_id: $site_id})
    MERGE (d:DPSHTest {id: $id, site_id: $site_id})
    SET d += $props
    MERGE (d)-[:LOCATED_IN]->(z)
    RETURN d
    """

# ── BoreHole ──────────────────────────────────────────────────────────────────

def upsert_borehole():
    return """
    MATCH (s:Site {id: $site_id})-[:HAS_ZONE]->(z:Zone {id: $zone_id, site_id: $site_id})
    MERGE (b:BoreHole {id: $id, site_id: $site_id})
    SET b += $props
    MERGE (b)-[:LOCATED_IN]->(z)
    FOREACH (_ IN CASE WHEN $ground_model_id IS NULL THEN [] ELSE [1] END |
        MERGE (g:GroundModel {id: $ground_model_id, site_id: $site_id})
        MERGE (b)-[:HAS_GROUND_MODEL]->(g)
    )
    RETURN b
    """

# ── TestPit ───────────────────────────────────────────────────────────────────

def upsert_testpit():
    return """
    MATCH (s:Site {id: $site_id})-[:HAS_ZONE]->(z:Zone {id: $zone_id, site_id: $site_id})
    MERGE (t:TestPit {id: $id, site_id: $site_id})
    SET t += $props
    MERGE (t)-[:LOCATED_IN]->(z)
    FOREACH (_ IN CASE WHEN $ground_model_id IS NULL THEN [] ELSE [1] END |
        MERGE (g:GroundModel {id: $ground_model_id, site_id: $site_id})
        MERGE (t)-[:HAS_GROUND_MODEL]->(g)
    )
    RETURN t
    """

# ── SoilType (global vocabulary — no site_id) ────────────────────────────────

def upsert_soil_type():
    return """
    MERGE (s:SoilType {unit_no: $unit_no})
    SET s += $props
    RETURN s
    """

# ── GroundModel ───────────────────────────────────────────────────────────────

def upsert_ground_model():
    return """
    MERGE (g:GroundModel {id: $id, site_id: $site_id})
    RETURN g
    """

# ── GroundLayer ───────────────────────────────────────────────────────────────

def upsert_ground_layer():
    return """
    MATCH (g:GroundModel {id: $ground_model_id, site_id: $site_id})
    MERGE (l:GroundLayer {id: $id, site_id: $site_id})
    SET l += $props
    MERGE (g)-[:HAS_LAYER]->(l)
    WITH l
    FOREACH (_ IN CASE WHEN $soil_unit_no IS NULL THEN [] ELSE [1] END |
        MERGE (s:SoilType {unit_no: $soil_unit_no})
        MERGE (l)-[:OF_MATERIAL]->(s)
    )
    RETURN l
    """

# ── ThermalResistivityTest ────────────────────────────────────────────────────

def upsert_thermal_test():
    return """
    MATCH (tp:TestPit {id: $testpit_id, site_id: $site_id})
    MERGE (x:ThermalResistivityTest {id: $id, site_id: $site_id})
    SET x += $props
    MERGE (tp)-[:HAS_THERMAL_TEST]->(x)
    RETURN x
    """

# ── LaboratoryTest ────────────────────────────────────────────────────────────

def upsert_lab_test():
    return """
    MATCH (loc {id: $location_id, site_id: $site_id})
    WHERE loc:BoreHole OR loc:TestPit
    MERGE (t:LaboratoryTest {id: $id, site_id: $site_id})
    SET t += $props
    MERGE (loc)-[:HAS_LAB_TEST]->(t)
    WITH t
    OPTIONAL MATCH (s:SoilType {unit_no: $soil_unit_no})
    FOREACH (_ IN CASE WHEN s IS NULL THEN [] ELSE [1] END |
        MERGE (t)-[:OF_MATERIAL]->(s)
    )
    RETURN t
    """

# ── SoilAggressivity ──────────────────────────────────────────────────────────

def upsert_aggressivity():
    return """
    MATCH (loc {id: $location_id, site_id: $site_id})
    WHERE loc:BoreHole OR loc:TestPit
    MERGE (a:SoilAggressivity {id: $id, site_id: $site_id})
    SET a += $props
    MERGE (loc)-[:HAS_AGGRESSIVITY_TEST]->(a)
    RETURN a
    """
