from app.db.neo4j_driver import run_query

def create_constraints():
    queries = [
        "CREATE CONSTRAINT pile_id IF NOT EXISTS FOR (p:Pile) REQUIRE p.id IS UNIQUE",
        "CREATE CONSTRAINT cpt_id IF NOT EXISTS FOR (c:CPTTest) REQUIRE c.id IS UNIQUE",
        "CREATE CONSTRAINT soil_id IF NOT EXISTS FOR (s:SoilLayer) REQUIRE s.id IS UNIQUE"
    ]

    for q in queries:
        run_query(q)

    print("Schema constratints created")