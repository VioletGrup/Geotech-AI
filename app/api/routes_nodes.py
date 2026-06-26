"""
routes_nodes.py — write endpoints (schema v4).

v4 change: every node below Site now carries a site_id property and is
MERGEd by (id, site_id) rather than by id alone.  This means the same
Zone id (e.g. "1.1") can exist under multiple sites without collision.

The site_id is passed in the request body for every node type that sits
below Site.  It flows through to the Cypher as both a MATCH filter and a
node property so that MERGE is correctly scoped.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.db import queries
from app.db.neo4j_driver import run_query
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/nodes", tags=["nodes"])


def _props(model: BaseModel, *, drop: tuple) -> dict:
    return {k: v for k, v in model.model_dump(exclude_none=True).items()
            if k not in drop}


def _one(query, params, key, label):
    result = run_query(query, params)
    if not result:
        raise HTTPException(status_code=404,
                            detail=f"{label}: parent node not found — "
                                   "check site_id, zone_id and other FK fields")
    node_id = params.get("id") or params.get("unit_no", "")
    return {"message": f"{label} '{node_id}' saved", "node": dict(result[0][key])}


# ══════════════════════════════════════════════════════════════════════════════
# Pydantic models
# Every node below Site has site_id as a required FK so the MERGE is scoped.
# ══════════════════════════════════════════════════════════════════════════════

class Site(BaseModel):
    id: str
    name: Optional[str] = None
    address: Optional[str] = None
    coordinate_system: Optional[str] = None
    status: Optional[str] = None            # "new" | "completed"

class Zone(BaseModel):
    id: str
    site_id: str                             # FK -> Site (required in v4)
    name: Optional[str] = None
    pre_drill_decision: Optional[str] = None
    trackers_4string: Optional[int] = None
    trackers_3string: Optional[int] = None
    trackers_2string: Optional[int] = None

class PileTestLocation(BaseModel):
    id: str
    site_id: str
    zone_id: Optional[str] = None
    driving_type: Optional[str] = None
    easting: Optional[float] = None
    northing: Optional[float] = None
    reduced_level: Optional[float] = None
    designer: Optional[str] = None
    section_type: Optional[str] = None
    target_depth: Optional[float] = None
    achieved_embedment: Optional[float] = None
    drive_time: Optional[float] = None
    driving_rate: Optional[float] = None

class PileTest(BaseModel):
    id: str
    site_id: str
    pile_location_id: Optional[str] = None
    section_type: Optional[str] = None
    passed: Optional[bool] = None

class TensionPileTest(BaseModel):
    id: str
    site_id: str
    pile_test_id: str
    uplift_applied_force: Optional[float] = None
    uplift_max_deflection: Optional[float] = None
    max_load_proportion_ed: Optional[float] = None

class LateralPileTest(BaseModel):
    id: str
    site_id: str
    pile_test_id: str
    max_applied_force: Optional[float] = None
    max_deflection_top: Optional[float] = None
    max_deflection_bottom: Optional[float] = None
    load_max: Optional[float] = None
    max_load_proportion_ed: Optional[float] = None

class CompressionPileTest(BaseModel):
    id: str
    site_id: str
    pile_test_id: str
    max_applied_force: Optional[float] = None
    max_deflection: Optional[float] = None
    max_load_proportion_ed: Optional[float] = None

class DPSHTest(BaseModel):
    id: str
    site_id: str
    zone_id: Optional[str] = None
    easting: Optional[float] = None
    northing: Optional[float] = None
    refusal_depth: Optional[float] = None

class BoreHole(BaseModel):
    id: str
    site_id: str
    zone_id: Optional[str] = None
    ground_model_id: Optional[str] = None
    series: Optional[str] = None
    elevation: Optional[float] = None
    total_depth: Optional[float] = None
    groundwater_depth: Optional[float] = None

class TestPit(BaseModel):
    id: str
    site_id: str
    zone_id: Optional[str] = None
    ground_model_id: Optional[str] = None
    elevation: Optional[float] = None
    total_depth: Optional[float] = None

class SoilType(BaseModel):
    unit_no: str                             # global PK — no site_id
    origin: Optional[str] = None
    unit_name: Optional[str] = None
    description: Optional[str] = None

class GroundModel(BaseModel):
    id: str
    site_id: str

class GroundLayer(BaseModel):
    id: str
    site_id: str
    ground_model_id: str
    soil_unit_no: Optional[str] = None
    start_depth: Optional[float] = None
    end_depth: Optional[float] = None

class ThermalResistivityTest(BaseModel):
    id: str
    site_id: str
    testpit_id: str
    depth: Optional[float] = None
    thermal_reading: Optional[float] = None
    r_value: Optional[float] = None

class LaboratoryTest(BaseModel):
    id: str
    site_id: str
    location_id: str
    soil_unit_no: Optional[str] = None
    top_depth: Optional[float] = None
    bottom_depth: Optional[float] = None
    moisture_content: Optional[float] = None
    liquid_limit: Optional[float] = None
    plastic_limit: Optional[float] = None
    plasticity_index: Optional[float] = None
    linear_shrinkage: Optional[float] = None
    emerson_class: Optional[int] = None
    iss: Optional[float] = None
    gravel: Optional[float] = None
    sand: Optional[float] = None
    fines: Optional[float] = None
    compaction_mdd: Optional[float] = None
    compaction_omc: Optional[float] = None
    cbr_4day_2_5mm: Optional[int] = None
    cbr_swell: Optional[float] = None

class SoilAggressivity(BaseModel):
    id: str
    site_id: str
    location_id: str
    depth: Optional[float] = None
    ph: Optional[float] = None
    sulfate: Optional[float] = None
    chlorides: Optional[float] = None
    resistivity: Optional[float] = None
    exposure_class_concrete: Optional[str] = None
    exposure_class_steel: Optional[str] = None


# ══════════════════════════════════════════════════════════════════════════════
# Endpoints
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/site", status_code=200)
def add_site(body: Site):
    return _one(queries.upsert_site(),
                {"id": body.id, "props": _props(body, drop=("id",))},
                "s", "Site")

@router.post("/zone", status_code=200)
def add_zone(body: Zone):
    return _one(queries.upsert_zone(),
                {"id": body.id, "site_id": body.site_id,
                 "props": _props(body, drop=("id", "site_id"))},
                "z", "Zone")

@router.post("/pile-test-location", status_code=200)
def add_pile_test_location(body: PileTestLocation):
    return _one(queries.upsert_pile_test_location(),
                {"id": body.id, "site_id": body.site_id, "zone_id": body.zone_id,
                 "props": _props(body, drop=("id", "site_id", "zone_id"))},
                "p", "PileTestLocation")

@router.post("/dpsh", status_code=200)
def add_dpsh(body: DPSHTest):
    return _one(queries.upsert_dpsh(),
                {"id": body.id, "site_id": body.site_id, "zone_id": body.zone_id,
                 "props": _props(body, drop=("id", "site_id", "zone_id"))},
                "d", "DPSHTest")

@router.post("/borehole", status_code=200)
def add_borehole(body: BoreHole):
    return _one(queries.upsert_borehole(),
                {"id": body.id, "site_id": body.site_id,
                 "zone_id": body.zone_id, "ground_model_id": body.ground_model_id,
                 "props": _props(body, drop=("id", "site_id", "zone_id", "ground_model_id"))},
                "b", "BoreHole")

@router.post("/testpit", status_code=200)
def add_testpit(body: TestPit):
    return _one(queries.upsert_testpit(),
                {"id": body.id, "site_id": body.site_id,
                 "zone_id": body.zone_id, "ground_model_id": body.ground_model_id,
                 "props": _props(body, drop=("id", "site_id", "zone_id", "ground_model_id"))},
                "t", "TestPit")

@router.post("/pile-test", status_code=200)
def add_pile_test(body: PileTest):
    return _one(queries.upsert_pile_test(),
                {"id": body.id, "site_id": body.site_id,
                 "pile_location_id": body.pile_location_id,
                 "props": _props(body, drop=("id", "site_id", "pile_location_id"))},
                "t", "PileTest")

@router.post("/tension-test", status_code=200)
def add_tension_test(body: TensionPileTest):
    return _one(queries.upsert_tension_test(),
                {"id": body.id, "site_id": body.site_id, "pile_test_id": body.pile_test_id,
                 "props": _props(body, drop=("id", "site_id", "pile_test_id"))},
                "t", "TensionPileTest")

@router.post("/lateral-test", status_code=200)
def add_lateral_test(body: LateralPileTest):
    return _one(queries.upsert_lateral_test(),
                {"id": body.id, "site_id": body.site_id, "pile_test_id": body.pile_test_id,
                 "props": _props(body, drop=("id", "site_id", "pile_test_id"))},
                "t", "LateralPileTest")

@router.post("/compression-test", status_code=200)
def add_compression_test(body: CompressionPileTest):
    return _one(queries.upsert_compression_test(),
                {"id": body.id, "site_id": body.site_id, "pile_test_id": body.pile_test_id,
                 "props": _props(body, drop=("id", "site_id", "pile_test_id"))},
                "t", "CompressionPileTest")

@router.post("/thermal-test", status_code=200)
def add_thermal_test(body: ThermalResistivityTest):
    return _one(queries.upsert_thermal_test(),
                {"id": body.id, "site_id": body.site_id, "testpit_id": body.testpit_id,
                 "props": _props(body, drop=("id", "site_id", "testpit_id"))},
                "x", "ThermalResistivityTest")

@router.post("/lab-test", status_code=200)
def add_lab_test(body: LaboratoryTest):
    return _one(queries.upsert_lab_test(),
                {"id": body.id, "site_id": body.site_id, "location_id": body.location_id,
                 "soil_unit_no": body.soil_unit_no,
                 "props": _props(body, drop=("id", "site_id", "location_id", "soil_unit_no"))},
                "t", "LaboratoryTest")

@router.post("/aggressivity", status_code=200)
def add_aggressivity(body: SoilAggressivity):
    return _one(queries.upsert_aggressivity(),
                {"id": body.id, "site_id": body.site_id, "location_id": body.location_id,
                 "props": _props(body, drop=("id", "site_id", "location_id"))},
                "a", "SoilAggressivity")

@router.post("/soil-type", status_code=200)
def add_soil_type(body: SoilType):
    result = run_query(queries.upsert_soil_type(),
                       {"unit_no": body.unit_no,
                        "props": _props(body, drop=("unit_no",))})
    return {"message": f"SoilType '{body.unit_no}' saved", "node": dict(result[0]["s"])}

@router.post("/ground-model", status_code=200)
def add_ground_model(body: GroundModel):
    return _one(queries.upsert_ground_model(),
                {"id": body.id, "site_id": body.site_id},
                "g", "GroundModel")

@router.post("/ground-layer", status_code=200)
def add_ground_layer(body: GroundLayer):
    return _one(queries.upsert_ground_layer(),
                {"id": body.id, "site_id": body.site_id,
                 "ground_model_id": body.ground_model_id,
                 "soil_unit_no": body.soil_unit_no,
                 "props": _props(body, drop=("id", "site_id", "ground_model_id", "soil_unit_no"))},
                "l", "GroundLayer")


# ── Bulk import ────────────────────────────────────────────────────────────────

_BULK = {
    "site":               (Site,                    add_site),
    "zone":               (Zone,                    add_zone),
    "pile-test-location": (PileTestLocation,         add_pile_test_location),
    "pile-test":          (PileTest,                 add_pile_test),
    "tension-test":       (TensionPileTest,          add_tension_test),
    "lateral-test":       (LateralPileTest,          add_lateral_test),
    "compression-test":   (CompressionPileTest,      add_compression_test),
    "dpsh":               (DPSHTest,                 add_dpsh),
    "borehole":           (BoreHole,                 add_borehole),
    "testpit":            (TestPit,                  add_testpit),
    "soil-type":          (SoilType,                 add_soil_type),
    "ground-model":       (GroundModel,              add_ground_model),
    "ground-layer":       (GroundLayer,              add_ground_layer),
    "thermal-test":       (ThermalResistivityTest,   add_thermal_test),
    "lab-test":           (LaboratoryTest,           add_lab_test),
    "aggressivity":       (SoilAggressivity,         add_aggressivity),
}


@router.post("/{node_type}/bulk", status_code=200)
def bulk(node_type: str, body: dict):
    if node_type not in _BULK:
        raise HTTPException(status_code=404,
                            detail=f"Unknown node type '{node_type}'")
    Model, handler = _BULK[node_type]
    rows = body.get("rows", [])
    done, errors = 0, []
    for i, row in enumerate(rows):
        try:
            handler(Model(**row))
            done += 1
        except HTTPException as e:
            errors.append(f"row {i+1}: {e.detail}")
        except Exception as e:
            errors.append(f"row {i+1}: {e}")
    return {"saved": done, "total": len(rows), "errors": errors}