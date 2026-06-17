# ── Pile ──────────────────────────────────────────────────────────────────────

def create_pile():
    return """
    CREATE (p:Pile {
        id: $id,
        diameter: $diameter,
        length: $length,
        type: $type
    })
    RETURN p
    """

def update_pile():
    return """
    MATCH (p:Pile {id: $id})
    SET p.diameter = coalesce($diameter, p.diameter),
        p.length   = coalesce($length,   p.length),
        p.type     = coalesce($type,     p.type)
    RETURN p
    """

def delete_pile():
    return """
    MATCH (p:Pile {id: $id})
    DETACH DELETE p
    """

def retrieve_pile_id():
    return """
    MATCH (p:Pile {id: $id})
    RETURN p
    """

# ── CPTTest ───────────────────────────────────────────────────────────────────

def create_cpt():
    return """
    CREATE (c:CPTTest {
        id: $id,
        depth: $depth,
        qc: $qc,
        fs: $fs
    })
    RETURN c
    """

def update_cpt():
    return """
    MATCH (c:CPTTest {id: $id})
    SET c.depth = coalesce($depth, c.depth),
        c.qc    = coalesce($qc,    c.qc),
        c.fs    = coalesce($fs,    c.fs)
    RETURN c
    """

def delete_cpt():
    return """
    MATCH (c:CPTTest {id: $id})
    DETACH DELETE c
    """

def retrieve_cpt_id():
    return """
    MATCH (c: CPTTest {id: $id})
    RETURN c
    """

# ── SoilLayer ─────────────────────────────────────────────────────────────────

def create_soil_layer():
    return """
    CREATE (s:SoilLayer {
        id: $id,
        soil_type: $soil_type
    })
    RETURN s
    """

def update_soil_layer():
    return """
    MATCH (s:SoilLayer {id: $id})
    SET s.soil_type = coalesce($soil_type, s.soil_type)
    RETURN s
    """

def delete_soil_layer():
    return """
    MATCH (s:SoilLayer {id: $id})
    DETACH DELETE s
    """

def retrieve_soil_id():
    return """
    MATCH (s: SoilLayer {id: $id})
    RETURN s
    """
# ── PileLoadTest ──────────────────────────────────────────────────────────────

def create_pile_load_test():
    return """
    MATCH (p:Pile {id: $pile_id})
    CREATE (t:PileLoadTest {id: $id, max_load: $max_load})
    CREATE (p)-[:HAS_LOAD_TEST]->(t)
    RETURN t
    """

def update_pile_load_test():
    return """
    MATCH (t:PileLoadTest {id: $id})
    SET t.max_load = coalesce($max_load, t.max_load)
    RETURN t
    """

def delete_pile_load_test():
    return """
    MATCH (t:PileLoadTest {id: $id})
    DETACH DELETE t
    """

# ── Relationships ─────────────────────────────────────────────────────────────

def link_pile_soil():
    return """
    MATCH (p:Pile {id: $pile_id})
    MATCH (s:SoilLayer {id: $soil_id})
    MERGE (p)-[:INTERSECTS]->(s)
    """

def unlink_pile_soil():
    return """
    MATCH (p:Pile {id: $pile_id})-[r:INTERSECTS]->(s:SoilLayer {id: $soil_id})
    DELETE r
    """

def link_cpt_soil():
    return """
    MATCH (c:CPTTest {id: $cpt_id})
    MATCH (s:SoilLayer {id: $soil_id})
    MERGE (c)-[:REPRESENTS]->(s)
    """

def unlink_cpt_soil():
    return """
    MATCH (c:CPTTest {id: $cpt_id})-[r:REPRESENTS]->(s:SoilLayer {id: $soil_id})
    DELETE r
    """

# ── Site ──────────────────────────────────────────────────────────────────────

def create_site():
    return """
    CREATE (s:Site {
        id: $id,
        name: $name
    })
    RETURN s
    """

def update_site():
    return """
    MATCH (s:Site {id: $id})
    SET s.name = coalesce($name, s.name)
    RETURN s
    """

def delete_site():
    return """
    MATCH (s:Site {id: $id})
    DETACH DELETE s
    """

# ── Zone ──────────────────────────────────────────────────────────────────────

def create_zone():
    # A Zone always belongs to a Site; fail (no rows) if the site is missing.
    return """
    MATCH (site:Site {id: $site_id})
    CREATE (z:Zone {id: $id, name: $name})
    CREATE (site)-[:HAS_ZONE]->(z)
    RETURN z
    """

def update_zone():
    return """
    MATCH (z:Zone {id: $id})
    SET z.name = coalesce($name, z.name)
    RETURN z
    """

def delete_zone():
    return """
    MATCH (z:Zone {id: $id})
    DETACH DELETE z
    """

# ── Location relationships (Pile / CPT → Zone) ────────────────────────────────

def link_pile_zone():
    return """
    MATCH (p:Pile {id: $pile_id})
    MATCH (z:Zone {id: $zone_id})
    MERGE (p)-[:LOCATED_IN]->(z)
    """

def unlink_pile_zone():
    return """
    MATCH (p:Pile {id: $pile_id})-[r:LOCATED_IN]->(z:Zone {id: $zone_id})
    DELETE r
    """

def link_cpt_zone():
    return """
    MATCH (c:CPTTest {id: $cpt_id})
    MATCH (z:Zone {id: $zone_id})
    MERGE (c)-[:LOCATED_IN]->(z)
    """

def unlink_cpt_zone():
    return """
    MATCH (c:CPTTest {id: $cpt_id})-[r:LOCATED_IN]->(z:Zone {id: $zone_id})
    DELETE r
    """

# ── Real-data nodes (upsert pattern: MERGE on id, SET property bag) ────────────
# Parsers re-run idempotently; optional fields are simply omitted from $props.

def upsert_pile():
    # Enriches an existing Pile or creates one. Real fields (easting, northing,
    # reduced_level, designer, section_type, target_depth, achieved_embedment,
    # refusal, refusal_depth) arrive in $props.
    return """
    MERGE (p:Pile {id: $id})
    SET p += $props
    RETURN p
    """

def upsert_zone_props():
    # Enriches a Zone with block fields (pre_drill_decision, tracker counts, etc).
    return """
    MERGE (z:Zone {id: $id})
    SET z += $props
    RETURN z
    """

def upsert_investigation_point():
    return """
    MERGE (i:InvestigationPoint {id: $id})
    SET i += $props
    RETURN i
    """

def upsert_geotech_unit():
    return """
    MERGE (u:GeotechUnit {id: $id})
    SET u += $props
    RETURN u
    """

def upsert_load_test():
    # Typed load test (compression/tension/lateral), linked to its pile.
    return """
    MATCH (p:Pile {id: $pile_id})
    MERGE (t:LoadTest {id: $id})
    SET t += $props
    MERGE (p)-[:HAS_LOAD_TEST]->(t)
    RETURN t
    """

# ── Location / unit relationships ─────────────────────────────────────────────

def link_investigation_zone():
    return """
    MATCH (i:InvestigationPoint {id: $ip_id})
    MATCH (z:Zone {id: $zone_id})
    MERGE (i)-[:LOCATED_IN]->(z)
    """

def link_pile_unit():
    return """
    MATCH (p:Pile {id: $pile_id})
    MATCH (u:GeotechUnit {id: $unit_id})
    MERGE (p)-[:IN_UNIT]->(u)
    """

def link_investigation_unit():
    return """
    MATCH (i:InvestigationPoint {id: $ip_id})
    MATCH (u:GeotechUnit {id: $unit_id})
    MERGE (i)-[:IN_UNIT]->(u)
    """

def link_pile_nearest_probe():
    return """
    MATCH (p:Pile {id: $pile_id})
    MATCH (i:InvestigationPoint {id: $ip_id})
    MERGE (p)-[:NEAREST_PROBE]->(i)
    """

# ── Retrieval ─────────────────────────────────────────────────────────────────

def get_similar_piles():
    return """
    MATCH (c:CPTTest)-[:REPRESENTS]->(s:SoilLayer)<-[:INTERSECTS]-(p:Pile)
    MATCH (p)-[:HAS_LOAD_TEST]->(t:PileLoadTest)
    WHERE c.qc >= $qc - 2000 AND c.qc <= $qc + 2000
    RETURN p.id AS pile, t.max_load AS load, s.soil_type AS soil
    LIMIT 20
    """