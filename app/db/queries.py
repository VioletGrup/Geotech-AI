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

# ── Retrieval ─────────────────────────────────────────────────────────────────

def get_similar_piles():
    return """
    MATCH (c:CPTTest)-[:REPRESENTS]->(s:SoilLayer)<-[:INTERSECTS]-(p:Pile)
    MATCH (p)-[:HAS_LOAD_TEST]->(t:PileLoadTest)
    WHERE c.qc >= $qc - 2000 AND c.qc <= $qc + 2000
    RETURN p.id AS pile, t.max_load AS load, s.soil_type AS soil
    LIMIT 10
    """