import pandas as pd
from app.db.neo4j_driver import run_query
from app.db.queries import create_pile

def load_piles(csv_path):
    df = pd.read_csv(csv_path)

    for _, row in df.iterrows():
        run_query(create_pile(), {
            "id": row["id"],
            "diameter": row["diameter"],
            "length": row["length"],
            "type": row["type"]
        })
    
    print("Piles loaded successfully")