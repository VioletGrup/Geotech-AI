from app.db.neo4j_driver import run_query

def get_similar_cases(qc = 0, soil_type = None):
    query = """
    MATCH (c:CPTTTest)<-[:REPRESENTS]-(s:SoilLayer)<-[:INTERSECTS]-(p:Pile)
    MATCH (p)-[:HAS_LOAD_TEST]->(t:PileLoadTest)
    WHERE ($qc = 0 OR c.qc >= $qc - 2000 AND c.qc <= $qc + 2000)
    AND ($soil_type IS NULL OR s.soil_type = $soil_type)
    RETURN  p.id AS pile, 
            t.max_load AS capacity
            s.soil_type AS soil
    LIMIT 10
    """

    return run_query(query, {
        "qc": qc,
        "soil_type": soil_type
        })