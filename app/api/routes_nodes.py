"""Add-data endpoints (schema v3).

One endpoint per node type. Each model carries the node's own fields plus the
foreign keys for its relationships; the create wires those edges. Bulk variants
back the frontend "many" mode and CSV/parser imports.
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
    """Property bag for `SET n += $props`: drop id + foreign keys, omit None."""
    return {k: v for k, v in model.model_dump(exclude_none=True).items() if k not in drop}


def _one(query, params, key, label):
    result = run_query(query, params)
    if not result:
        raise HTTPException(status_code=404, detail=f"{label}: a referenced parent was not found")
    return {"message": f"{label} '{params['id']}' saved", "node": dict(result[0][key])}


# ══════════════════════════════════════════════════════════════════════════════
# Models  (FK fields are listed first; everything else is a node property)
# ══════════════════════════════════════════════════════════════════════════════

class Site(BaseModel):
    id: str
    name: Optional[str] = None
    address: Optional[str] = None
    coordinate_system: Optional[str] = None

class Zone(BaseModel):
    id: str
    site_id: Optional[str] = None            # FK -> Site
    name: Optional[str] = None
    pre_drill_decision: Optional[str] = None
    trackers_4string: Optional[int] = None
    trackers_3string: Optional[int] = None
    trackers_2string: Optional[int] = None

class PileTestLocation(BaseModel):
    id: str
    zone_id: Optional[str] = None            # FK -> Zone
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

class PileTest(BaseModel):                    # container
    id: str
    pile_location_id: Optional[str] = None   # FK -> PileTestLocation
    section_type: Optional[str] = None
    passed: Optional[bool] = None

class TensionPileTest(BaseModel):
    id: str
    pile_test_id: str                        # FK -> PileTest (required)
    uplift_applied_force: Optional[float] = None
    uplift_max_deflection: Optional[float] = None
    max_load_proportion_ed: Optional[float] = None

class LateralPileTest(BaseModel):
    id: str
    pile_test_id: str                        # FK -> PileTest (required)
    max_applied_force: Optional[float] = None
    max_deflection_top: Optional[float] = None
    load_max: Optional[float] = None
    max_load_proportion_ed: Optional[float] = None

class CompressionPileTest(BaseModel):
    id: str
    pile_test_id: str                        # FK -> PileTest (required)
    max_applied_force: Optional[float] = None
    max_deflection: Optional[float] = None
    max_load_proportion_ed: Optional[float] = None

class DPSHTest(BaseModel):
    id: str
    zone_id: Optional[str] = None            # FK -> Zone
    easting: Optional[float] = None
    northing: Optional[float] = None
    refusal_depth: Optional[float] = None

class BoreHole(BaseModel):
    id: str
    zone_id: Optional[str] = None            # FK -> Zone
    series: Optional[str] = None
    elevation: Optional[float] = None
    total_depth: Optional[float] = None
    groundwater_depth: Optional[float] = None

class TestPit(BaseModel):
    id: str
    zone_id: Optional[str] = None            # FK -> Zone
    elevation: Optional[float] = None
    total_depth: Optional[float] = None

class SoilType(BaseModel):
    unit_name: str
    description: Optional[str] = None

class GroundModel(BaseModel):
    id: str
    location_id: Optional[str] = None        # FK -> BoreHole | TestPit

class GroundLayer(BaseModel):
    id: str
    ground_model_id: str                     # FK -> GroundModel (required)
    soil_unit_name: Optional[str] = None     # FK -> SoilType
    order: Optional[int] = None
    start_depth: Optional[float] = None
    end_depth: Optional[float] = None
    condition: Optional[str] = None

class ThermalResistivityTest(BaseModel):
    id: str
    testpit_id: str                          # FK -> TestPit (required)
    depth: Optional[float] = None
    thermal_reading: Optional[float] = None
    r_value: Optional[float] = None

class LaboratoryTest(BaseModel):
    id: str
    location_id: str                         # FK -> BoreHole | TestPit (required)
    soil_unit_name: Optional[str] = None     # FK -> SoilType
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
    location_id: str                         # FK -> BoreHole | TestPit (required)
    depth: Optional[float] = None
    ph: Optional[float] = None
    sulfate: Optional[float] = None
    chlorides: Optional[float] = None
    resistivity: Optional[float] = None
    exposure_class_concrete: Optional[str] = None
    exposure_class_steel: Optional[str] = None


# ══════════════════════════════════════════════════════════════════════════════
# Endpoints — each (a) single create, (b) bulk create
# ══════════════════════════════════════════════════════════════════════════════

def _make(path, label, query, key, id_field, fk_fields):
    """Register POST /nodes/<path> and /nodes/<path>/bulk for a node type."""
    drop = (id_field, *fk_fields)

    @router.post(f"/{path}", status_code=200, name=f"add_{path}")
    def add(body, _q=query, _k=key, _l=label, _idf=id_field, _drop=drop, _fk=fk_fields):  # type: ignore
        params = {"id": body.__dict__[_idf], "props": _props(body, drop=_drop)}
        params["id"] = getattr(body, _idf)
        for fk in _fk:
            params[fk] = getattr(body, fk, None)
        try:
            return _one(_q, params, _k, _l)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return add


# Site / Zone
@router.post("/site", status_code=200)
def add_site(body: Site):
    return _one(queries.upsert_site(), {"id": body.id, "props": _props(body, drop=("id",))}, "s", "Site")

@router.post("/zone", status_code=200)
def add_zone(body: Zone):
    p = {"id": body.id, "site_id": body.site_id, "props": _props(body, drop=("id", "site_id"))}
    return _one(queries.upsert_zone(), p, "z", "Zone")

# Locations
@router.post("/pile-test-location", status_code=200)
def add_pile_test_location(body: PileTestLocation):
    p = {"id": body.id, "zone_id": body.zone_id, "props": _props(body, drop=("id", "zone_id"))}
    return _one(queries.upsert_pile_test_location(), p, "p", "PileTestLocation")

@router.post("/dpsh", status_code=200)
def add_dpsh(body: DPSHTest):
    p = {"id": body.id, "zone_id": body.zone_id, "props": _props(body, drop=("id", "zone_id"))}
    return _one(queries.upsert_dpsh(), p, "d", "DPSHTest")

@router.post("/borehole", status_code=200)
def add_borehole(body: BoreHole):
    p = {"id": body.id, "zone_id": body.zone_id, "props": _props(body, drop=("id", "zone_id"))}
    return _one(queries.upsert_borehole(), p, "b", "BoreHole")

@router.post("/testpit", status_code=200)
def add_testpit(body: TestPit):
    p = {"id": body.id, "zone_id": body.zone_id, "props": _props(body, drop=("id", "zone_id"))}
    return _one(queries.upsert_testpit(), p, "t", "TestPit")

# Tests
@router.post("/pile-test", status_code=200)
def add_pile_test(body: PileTest):
    p = {"id": body.id, "pile_location_id": body.pile_location_id,
         "props": _props(body, drop=("id", "pile_location_id"))}
    return _one(queries.upsert_pile_test(), p, "t", "PileTest")

@router.post("/tension-test", status_code=200)
def add_tension_test(body: TensionPileTest):
    p = {"id": body.id, "pile_test_id": body.pile_test_id, "props": _props(body, drop=("id", "pile_test_id"))}
    return _one(queries.upsert_tension_test(), p, "t", "TensionPileTest")

@router.post("/lateral-test", status_code=200)
def add_lateral_test(body: LateralPileTest):
    p = {"id": body.id, "pile_test_id": body.pile_test_id, "props": _props(body, drop=("id", "pile_test_id"))}
    return _one(queries.upsert_lateral_test(), p, "t", "LateralPileTest")

@router.post("/compression-test", status_code=200)
def add_compression_test(body: CompressionPileTest):
    p = {"id": body.id, "pile_test_id": body.pile_test_id, "props": _props(body, drop=("id", "pile_test_id"))}
    return _one(queries.upsert_compression_test(), p, "t", "CompressionPileTest")

@router.post("/thermal-test", status_code=200)
def add_thermal_test(body: ThermalResistivityTest):
    p = {"id": body.id, "testpit_id": body.testpit_id, "props": _props(body, drop=("id", "testpit_id"))}
    return _one(queries.upsert_thermal_test(), p, "x", "ThermalResistivityTest")

@router.post("/lab-test", status_code=200)
def add_lab_test(body: LaboratoryTest):
    p = {"id": body.id, "location_id": body.location_id, "soil_unit_name": body.soil_unit_name,
         "props": _props(body, drop=("id", "location_id", "soil_unit_name"))}
    return _one(queries.upsert_lab_test(), p, "t", "LaboratoryTest")

@router.post("/aggressivity", status_code=200)
def add_aggressivity(body: SoilAggressivity):
    p = {"id": body.id, "location_id": body.location_id, "props": _props(body, drop=("id", "location_id"))}
    return _one(queries.upsert_aggressivity(), p, "a", "SoilAggressivity")

# Ground model
@router.post("/soil-type", status_code=200)
def add_soil_type(body: SoilType):
    p = {"id": body.unit_name, "unit_name": body.unit_name, "props": _props(body, drop=("unit_name",))}
    result = run_query(queries.upsert_soil_type(), {"unit_name": body.unit_name, "props": p["props"]})
    return {"message": f"SoilType '{body.unit_name}' saved", "node": dict(result[0]["s"])}

@router.post("/ground-model", status_code=200)
def add_ground_model(body: GroundModel):
    p = {"id": body.id, "location_id": body.location_id}
    return _one(queries.upsert_ground_model(), p, "g", "GroundModel")

@router.post("/ground-layer", status_code=200)
def add_ground_layer(body: GroundLayer):
    p = {"id": body.id, "ground_model_id": body.ground_model_id, "soil_unit_name": body.soil_unit_name,
         "props": _props(body, drop=("id", "ground_model_id", "soil_unit_name"))}
    return _one(queries.upsert_ground_layer(), p, "l", "GroundLayer")


# ── Bulk import (generic: dispatch by node type) ──────────────────────────────

_BULK = {
    "site": (Site, add_site),
    "zone": (Zone, add_zone),
    "pile-test-location": (PileTestLocation, add_pile_test_location),
    "pile-test": (PileTest, add_pile_test),
    "tension-test": (TensionPileTest, add_tension_test),
    "lateral-test": (LateralPileTest, add_lateral_test),
    "compression-test": (CompressionPileTest, add_compression_test),
    "dpsh": (DPSHTest, add_dpsh),
    "borehole": (BoreHole, add_borehole),
    "testpit": (TestPit, add_testpit),
    "soil-type": (SoilType, add_soil_type),
    "ground-model": (GroundModel, add_ground_model),
    "ground-layer": (GroundLayer, add_ground_layer),
    "thermal-test": (ThermalResistivityTest, add_thermal_test),
    "lab-test": (LaboratoryTest, add_lab_test),
    "aggressivity": (SoilAggressivity, add_aggressivity),
}


@router.post("/{node_type}/bulk", status_code=200)
def bulk(node_type: str, body: dict):
    if node_type not in _BULK:
        raise HTTPException(status_code=404, detail=f"Unknown node type '{node_type}'")
    Model, handler = _BULK[node_type]
    rows = body.get("rows", [])
    done, errors = 0, []
    for i, row in enumerate(rows):
        try:
            handler(Model(**row))
            done += 1
        except HTTPException as e:
            errors.append(f"row {i + 1}: {e.detail}")
        except Exception as e:
            errors.append(f"row {i + 1}: {e}")
    return {"saved": done, "total": len(rows), "errors": errors}