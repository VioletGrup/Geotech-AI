from __future__ import annotations

from typing import Dict, Iterable, List, Optional

import pandas as pd

import queries
from logger import get_logger
from neo4j_driver import run_query

logger = get_logger(__name__)


def _nan_to_none(value):
    return None if pd.isna(value) else value


def _records_from_csv(csv_path: str) -> List[dict]:
    df = pd.read_csv(csv_path)
    return df.where(pd.notna(df), None).to_dict(orient="records")


def load_sites(csv_path: str) -> Dict[str, int]:
    count = 0
    for row in _records_from_csv(csv_path):
        run_query(queries.create_site(), {
            "id": row.get("id"),
            "name": row.get("name"),
            "region": row.get("region"),
            "metadata": row.get("metadata"),
        })
        count += 1
    return {"rows_loaded": count}


def load_piles(csv_path: str) -> Dict[str, int]:
    count = 0
    for row in _records_from_csv(csv_path):
        run_query(queries.create_pile(), {
            "id": row.get("id"),
            "diameter": row.get("diameter"),
            "length": row.get("length"),
            "type": row.get("type"),
            "site_id": row.get("site_id"),
            "notes": row.get("notes"),
        })
        count += 1
    return {"rows_loaded": count}


def load_cpts(csv_path: str) -> Dict[str, int]:
    count = 0
    for row in _records_from_csv(csv_path):
        run_query(queries.create_cpt(), {
            "id": row.get("id"),
            "depth": row.get("depth"),
            "qc": row.get("qc"),
            "fs": row.get("fs"),
            "site_id": row.get("site_id"),
            "notes": row.get("notes"),
        })
        count += 1
    return {"rows_loaded": count}


def load_soil_layers(csv_path: str) -> Dict[str, int]:
    count = 0
    for row in _records_from_csv(csv_path):
        run_query(queries.create_soil_layer(), {
            "id": row.get("id"),
            "soil_type": row.get("soil_type"),
            "top_depth": row.get("top_depth"),
            "bottom_depth": row.get("bottom_depth"),
            "site_id": row.get("site_id"),
            "description": row.get("description"),
        })
        count += 1
    return {"rows_loaded": count}


def load_pile_load_tests(csv_path: str) -> Dict[str, int]:
    count = 0
    for row in _records_from_csv(csv_path):
        run_query(queries.create_pile_load_test(), {
            "id": row.get("id"),
            "pile_id": row.get("pile_id"),
            "max_load": row.get("max_load"),
            "test_date": row.get("test_date"),
            "test_type": row.get("test_type"),
            "settlement_10": row.get("settlement_10"),
            "notes": row.get("notes"),
        })
        count += 1
    return {"rows_loaded": count}


def load_relationships(csv_path: str, relationship_type: str) -> Dict[str, int]:
    count = 0
    records = _records_from_csv(csv_path)
    if relationship_type == "pile_soil":
        query = queries.link_pile_soil()
        for row in records:
            run_query(query, {"pile_id": row.get("pile_id"), "soil_id": row.get("soil_id")})
            count += 1
    elif relationship_type == "cpt_soil":
        query = queries.link_cpt_soil()
        for row in records:
            run_query(query, {"cpt_id": row.get("cpt_id"), "soil_id": row.get("soil_id")})
            count += 1
    else:
        raise ValueError("relationship_type must be 'pile_soil' or 'cpt_soil'")
    return {"rows_loaded": count}
