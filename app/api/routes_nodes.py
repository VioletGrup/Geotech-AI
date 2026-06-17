from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Any, Optional

from app.db import queries
from app.utils.logger import get_logger
from app.db.neo4j_driver import run_query

router = APIRouter(prefix="/nodes", tags=["nodes"])


# ── Request models ────────────────────────────────────────────────────────────

class PileCreate(BaseModel):
    id: str
    diameter: float
    length: float
    type: str

class PileUpdate(BaseModel):
    diameter: Optional[float] = None
    length: Optional[float] = None
    type: Optional[str] = None

class CPTCreate(BaseModel):
    id: str
    depth: float
    qc: float
    fs: float

class CPTUpdate(BaseModel):
    depth: Optional[float] = None
    qc: Optional[float] = None
    fs: Optional[float] = None

class SoilLayerCreate(BaseModel):
    id: str
    soil_type: str

class SoilLayerUpdate(BaseModel):
    soil_type: Optional[str] = None

class PileLoadTestCreate(BaseModel):
    id: str
    pile_id: str
    max_load: float

class PileLoadTestUpdate(BaseModel):
    max_load: Optional[float] = None

class RelationshipPileSoil(BaseModel):
    pile_id: str
    soil_id: str

class RelationshipCPTSoil(BaseModel):
    cpt_id: str
    soil_id: str

class BulkPileSoil(BaseModel):
    links: list[RelationshipPileSoil]

class BulkCPTSoil(BaseModel):
    links: list[RelationshipCPTSoil]

class SiteCreate(BaseModel):
    id: str
    name: str

class SiteUpdate(BaseModel):
    name: Optional[str] = None

class ZoneCreate(BaseModel):
    id: str
    site_id: str
    name: str

class ZoneUpdate(BaseModel):
    name: Optional[str] = None

class RelationshipPileZone(BaseModel):
    pile_id: str
    zone_id: str

class RelationshipCPTZone(BaseModel):
    cpt_id: str
    zone_id: str

class BulkPileZone(BaseModel):
    links: list[RelationshipPileZone]

class BulkCPTZone(BaseModel):
    links: list[RelationshipCPTZone]


# ── Pile endpoints ────────────────────────────────────────────────────────────

@router.post("/pile", status_code=201)
def add_pile(body: PileCreate):
    """Create a new Pile node."""
    try:
        result = run_query(queries.create_pile(), body.model_dump())
        if not result:
            raise HTTPException(status_code=500, detail="Pile creation returned no result")
        return {"message": "Pile created", "pile": dict(result[0]["p"])}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/pile/{pile_id}")
def edit_pile(pile_id: str, body: PileUpdate):
    """Update properties of an existing Pile node."""
    params = {"id": pile_id, **body.model_dump()}
    try:
        result = run_query(queries.update_pile(), params)
        if not result:
            raise HTTPException(status_code=404, detail=f"Pile '{pile_id}' not found")
        return {"message": "Pile updated", "pile": dict(result[0]["p"])}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/pile/{pile_id}", status_code=200)
def remove_pile(pile_id: str):
    """Delete a Pile node and all its relationships."""
    try:
        run_query(queries.delete_pile(), {"id": pile_id})
        return {"message": f"Pile '{pile_id}' deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── CPTTest endpoints ─────────────────────────────────────────────────────────

@router.post("/cpt", status_code=201)
def add_cpt(body: CPTCreate):
    """Create a new CPTTest node."""
    try:
        result = run_query(queries.create_cpt(), body.model_dump())
        if not result:
            raise HTTPException(status_code=500, detail="CPTTest creation returned no result")
        return {"message": "CPTTest created", "cpt": dict(result[0]["c"])}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/cpt/{cpt_id}")
def edit_cpt(cpt_id: str, body: CPTUpdate):
    """Update properties of an existing CPTTest node."""
    params = {"id": cpt_id, **body.model_dump()}
    try:
        result = run_query(queries.update_cpt(), params)
        if not result:
            raise HTTPException(status_code=404, detail=f"CPTTest '{cpt_id}' not found")
        return {"message": "CPTTest updated", "cpt": dict(result[0]["c"])}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/cpt/{cpt_id}", status_code=200)
def remove_cpt(cpt_id: str):
    """Delete a CPTTest node and all its relationships."""
    try:
        run_query(queries.delete_cpt(), {"id": cpt_id})
        return {"message": f"CPTTest '{cpt_id}' deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── SoilLayer endpoints ───────────────────────────────────────────────────────

@router.post("/soil", status_code=201)
def add_soil_layer(body: SoilLayerCreate):
    """Create a new SoilLayer node."""
    try:
        result = run_query(queries.create_soil_layer(), body.model_dump())
        if not result:
            raise HTTPException(status_code=500, detail="SoilLayer creation returned no result")
        return {"message": "SoilLayer created", "soil_layer": dict(result[0]["s"])}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/soil/{soil_id}")
def edit_soil_layer(soil_id: str, body: SoilLayerUpdate):
    """Update properties of an existing SoilLayer node."""
    params = {"id": soil_id, **body.model_dump()}
    try:
        result = run_query(queries.update_soil_layer(), params)
        if not result:
            raise HTTPException(status_code=404, detail=f"SoilLayer '{soil_id}' not found")
        return {"message": "SoilLayer updated", "soil_layer": dict(result[0]["s"])}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/soil/{soil_id}", status_code=200)
def remove_soil_layer(soil_id: str):
    """Delete a SoilLayer node and all its relationships."""
    try:
        run_query(queries.delete_soil_layer(), {"id": soil_id})
        return {"message": f"SoilLayer '{soil_id}' deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── PileLoadTest endpoints ────────────────────────────────────────────────────

@router.post("/load-test", status_code=201)
def add_pile_load_test(body: PileLoadTestCreate):
    """Create a PileLoadTest node and link it to the given Pile."""
    try:
        result = run_query(queries.create_pile_load_test(), body.model_dump())
        if not result:
            raise HTTPException(status_code=404, detail=f"Pile '{body.pile_id}' not found")
        return {"message": "PileLoadTest created", "load_test": dict(result[0]["t"])}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/load-test/{test_id}")
def edit_pile_load_test(test_id: str, body: PileLoadTestUpdate):
    """Update properties of an existing PileLoadTest node."""
    params = {"id": test_id, **body.model_dump()}
    try:
        result = run_query(queries.update_pile_load_test(), params)
        if not result:
            raise HTTPException(status_code=404, detail=f"PileLoadTest '{test_id}' not found")
        return {"message": "PileLoadTest updated", "load_test": dict(result[0]["t"])}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/load-test/{test_id}", status_code=200)
def remove_pile_load_test(test_id: str):
    """Delete a PileLoadTest node."""
    try:
        run_query(queries.delete_pile_load_test(), {"id": test_id})
        return {"message": f"PileLoadTest '{test_id}' deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Relationship endpoints ────────────────────────────────────────────────────

@router.post("/relationships/pile-soil", status_code=201)
def link_pile_to_soil(body: RelationshipPileSoil):
    """Create an INTERSECTS relationship between a Pile and a SoilLayer."""
    try:
        run_query(queries.link_pile_soil(), body.model_dump())
        return {"message": f"Pile '{body.pile_id}' linked to SoilLayer '{body.soil_id}'"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/relationships/pile-soil", status_code=200)
def unlink_pile_from_soil(pile_id: str, soil_id: str):
    """Remove an INTERSECTS relationship between a Pile and a SoilLayer."""
    try:
        run_query(queries.unlink_pile_soil(), {"pile_id": pile_id, "soil_id": soil_id})
        return {"message": f"Pile '{pile_id}' unlinked from SoilLayer '{soil_id}'"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/relationships/cpt-soil", status_code=201)
def link_cpt_to_soil(body: RelationshipCPTSoil):
    """Create a REPRESENTS relationship between a CPTTest and a SoilLayer."""
    try:
        run_query(queries.link_cpt_soil(), body.model_dump())
        return {"message": f"CPTTest '{body.cpt_id}' linked to SoilLayer '{body.soil_id}'"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/relationships/cpt-soil", status_code=200)
def unlink_cpt_from_soil(cpt_id: str, soil_id: str):
    """Remove a REPRESENTS relationship between a CPTTest and a SoilLayer."""
    try:
        run_query(queries.unlink_cpt_soil(), {"cpt_id": cpt_id, "soil_id": soil_id})
        return {"message": f"CPTTest '{cpt_id}' unlinked from SoilLayer '{soil_id}'"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Bulk relationship endpoints ───────────────────────────────────────────────

@router.post("/relationships/pile-soil/bulk", status_code=201)
def bulk_link_pile_to_soil(body: BulkPileSoil):
    """Create many INTERSECTS relationships at once. Reports per-row failures."""
    created, errors = 0, []
    for i, link in enumerate(body.links):
        try:
            run_query(queries.link_pile_soil(), link.model_dump())
            created += 1
        except Exception as e:
            errors.append(f"row {i + 1} ({link.pile_id}->{link.soil_id}): {e}")
    return {"created": created, "total": len(body.links), "errors": errors}


@router.post("/relationships/cpt-soil/bulk", status_code=201)
def bulk_link_cpt_to_soil(body: BulkCPTSoil):
    """Create many REPRESENTS relationships at once. Reports per-row failures."""
    created, errors = 0, []
    for i, link in enumerate(body.links):
        try:
            run_query(queries.link_cpt_soil(), link.model_dump())
            created += 1
        except Exception as e:
            errors.append(f"row {i + 1} ({link.cpt_id}->{link.soil_id}): {e}")
    return {"created": created, "total": len(body.links), "errors": errors}

# ── Site endpoints ────────────────────────────────────────────────────────────

@router.post("/site", status_code=201)
def add_site(body: SiteCreate):
    """Create a new Site node."""
    try:
        result = run_query(queries.create_site(), body.model_dump())
        if not result:
            raise HTTPException(status_code=500, detail="Site creation returned no result")
        return {"message": "Site created", "site": dict(result[0]["s"])}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/site/{site_id}")
def edit_site(site_id: str, body: SiteUpdate):
    """Update properties of an existing Site node."""
    params = {"id": site_id, **body.model_dump()}
    try:
        result = run_query(queries.update_site(), params)
        if not result:
            raise HTTPException(status_code=404, detail=f"Site '{site_id}' not found")
        return {"message": "Site updated", "site": dict(result[0]["s"])}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/site/{site_id}", status_code=200)
def remove_site(site_id: str):
    """Delete a Site node and all its relationships (zones stay, unlinked)."""
    try:
        run_query(queries.delete_site(), {"id": site_id})
        return {"message": f"Site '{site_id}' deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Zone endpoints ────────────────────────────────────────────────────────────

@router.post("/zone", status_code=201)
def add_zone(body: ZoneCreate):
    """Create a Zone node and link it to the given Site."""
    try:
        result = run_query(queries.create_zone(), body.model_dump())
        if not result:
            raise HTTPException(status_code=404, detail=f"Site '{body.site_id}' not found")
        return {"message": "Zone created", "zone": dict(result[0]["z"])}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/zone/{zone_id}")
def edit_zone(zone_id: str, body: ZoneUpdate):
    """Update properties of an existing Zone node."""
    params = {"id": zone_id, **body.model_dump()}
    try:
        result = run_query(queries.update_zone(), params)
        if not result:
            raise HTTPException(status_code=404, detail=f"Zone '{zone_id}' not found")
        return {"message": "Zone updated", "zone": dict(result[0]["z"])}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/zone/{zone_id}", status_code=200)
def remove_zone(zone_id: str):
    """Delete a Zone node and all its relationships."""
    try:
        run_query(queries.delete_zone(), {"id": zone_id})
        return {"message": f"Zone '{zone_id}' deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Location relationship endpoints (Pile / CPT → Zone) ───────────────────────

@router.post("/relationships/pile-zone", status_code=201)
def link_pile_to_zone(body: RelationshipPileZone):
    """Create a LOCATED_IN relationship between a Pile and a Zone."""
    try:
        run_query(queries.link_pile_zone(), body.model_dump())
        return {"message": f"Pile '{body.pile_id}' located in Zone '{body.zone_id}'"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/relationships/pile-zone", status_code=200)
def unlink_pile_from_zone(pile_id: str, zone_id: str):
    """Remove a LOCATED_IN relationship between a Pile and a Zone."""
    try:
        run_query(queries.unlink_pile_zone(), {"pile_id": pile_id, "zone_id": zone_id})
        return {"message": f"Pile '{pile_id}' removed from Zone '{zone_id}'"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/relationships/cpt-zone", status_code=201)
def link_cpt_to_zone(body: RelationshipCPTZone):
    """Create a LOCATED_IN relationship between a CPTTest and a Zone."""
    try:
        run_query(queries.link_cpt_zone(), body.model_dump())
        return {"message": f"CPTTest '{body.cpt_id}' located in Zone '{body.zone_id}'"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/relationships/cpt-zone", status_code=200)
def unlink_cpt_from_zone(cpt_id: str, zone_id: str):
    """Remove a LOCATED_IN relationship between a CPTTest and a Zone."""
    try:
        run_query(queries.unlink_cpt_zone(), {"cpt_id": cpt_id, "zone_id": zone_id})
        return {"message": f"CPTTest '{cpt_id}' removed from Zone '{zone_id}'"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/relationships/pile-zone/bulk", status_code=201)
def bulk_link_pile_to_zone(body: BulkPileZone):
    """Create many Pile→Zone LOCATED_IN relationships at once."""
    created, errors = 0, []
    for i, link in enumerate(body.links):
        try:
            run_query(queries.link_pile_zone(), link.model_dump())
            created += 1
        except Exception as e:
            errors.append(f"row {i + 1} ({link.pile_id}->{link.zone_id}): {e}")
    return {"created": created, "total": len(body.links), "errors": errors}


@router.post("/relationships/cpt-zone/bulk", status_code=201)
def bulk_link_cpt_to_zone(body: BulkCPTZone):
    """Create many CPT→Zone LOCATED_IN relationships at once."""
    created, errors = 0, []
    for i, link in enumerate(body.links):
        try:
            run_query(queries.link_cpt_zone(), link.model_dump())
            created += 1
        except Exception as e:
            errors.append(f"row {i + 1} ({link.cpt_id}->{link.zone_id}): {e}")
    return {"created": created, "total": len(body.links), "errors": errors}


# ══════════════════════════════════════════════════════════════════════════════
# Real-data nodes (PLT report / pre-drill / refusal map)
# ══════════════════════════════════════════════════════════════════════════════

def _props(model: BaseModel, *, drop: tuple = ("id",)) -> dict:
    """Flatten a model to a property bag for `SET n += $props` (omit unset/None)."""
    return {k: v for k, v in model.model_dump(exclude_none=True).items() if k not in drop}


# ── Pile (enriched) ───────────────────────────────────────────────────────────

class PileReal(BaseModel):
    id: str
    easting: Optional[float] = None
    northing: Optional[float] = None
    reduced_level: Optional[float] = None
    designer: Optional[str] = None
    section_type: Optional[str] = None
    target_depth: Optional[float] = None
    achieved_embedment: Optional[float] = None
    refusal: Optional[bool] = None
    refusal_depth: Optional[float] = None
    # legacy/optional synthetic fields still accepted
    diameter: Optional[float] = None
    length: Optional[float] = None
    type: Optional[str] = None


@router.post("/pile/upsert", status_code=200)
def upsert_pile(body: PileReal):
    """Create or enrich a Pile with real survey/install fields (idempotent)."""
    try:
        result = run_query(queries.upsert_pile(), {"id": body.id, "props": _props(body)})
        return {"message": f"Pile '{body.id}' upserted", "pile": dict(result[0]["p"])}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Zone (block) enrichment ───────────────────────────────────────────────────

class ZoneReal(BaseModel):
    id: str
    name: Optional[str] = None
    pre_drill_decision: Optional[str] = None
    trackers_4string: Optional[int] = None
    trackers_3string: Optional[int] = None
    trackers_2string: Optional[int] = None
    refusal_band: Optional[int] = None
    area: Optional[float] = None


@router.post("/zone/upsert", status_code=200)
def upsert_zone(body: ZoneReal):
    """Create or enrich a Zone (block) with pre-drill decision + tracker counts."""
    try:
        result = run_query(queries.upsert_zone_props(), {"id": body.id, "props": _props(body)})
        return {"message": f"Zone '{body.id}' upserted", "zone": dict(result[0]["z"])}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── InvestigationPoint ────────────────────────────────────────────────────────

class InvestigationPoint(BaseModel):
    id: str
    method: Optional[str] = None          # DPSH | Borehole | TrialPit
    easting: Optional[float] = None
    northing: Optional[float] = None
    refusal_depth: Optional[float] = None
    soil_description: Optional[str] = None
    cbr: Optional[float] = None
    depth_from: Optional[float] = None
    depth_to: Optional[float] = None


@router.post("/investigation", status_code=200)
def add_investigation(body: InvestigationPoint):
    """Create or update a geotechnical investigation point (DPSH/BH/TP)."""
    try:
        result = run_query(queries.upsert_investigation_point(), {"id": body.id, "props": _props(body)})
        return {"message": f"InvestigationPoint '{body.id}' upserted", "point": dict(result[0]["i"])}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── GeotechUnit ───────────────────────────────────────────────────────────────

class GeotechUnit(BaseModel):
    id: str
    name: Optional[str] = None
    description: Optional[str] = None


@router.post("/geotech-unit", status_code=200)
def add_geotech_unit(body: GeotechUnit):
    """Create or update a geotechnical unit."""
    try:
        result = run_query(queries.upsert_geotech_unit(), {"id": body.id, "props": _props(body)})
        return {"message": f"GeotechUnit '{body.id}' upserted", "unit": dict(result[0]["u"])}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── LoadTest (typed) ──────────────────────────────────────────────────────────

class LoadTest(BaseModel):
    id: str
    pile_id: str
    test_type: Optional[str] = None       # compression | tension | lateral
    target_load: Optional[float] = None
    achieved_load: Optional[float] = None
    max_deflection: Optional[float] = None
    result: Optional[str] = None          # pass | refusal | fail


@router.post("/load-test/upsert", status_code=200)
def upsert_load_test(body: LoadTest):
    """Create or update a typed load test, linked to its pile."""
    params = {"id": body.id, "pile_id": body.pile_id, "props": _props(body, drop=("id", "pile_id"))}
    try:
        result = run_query(queries.upsert_load_test(), params)
        if not result:
            raise HTTPException(status_code=404, detail=f"Pile '{body.pile_id}' not found")
        return {"message": f"LoadTest '{body.id}' upserted", "test": dict(result[0]["t"])}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Location / unit relationships ─────────────────────────────────────────────

class RelInvestigationZone(BaseModel):
    ip_id: str
    zone_id: str

class RelPileUnit(BaseModel):
    pile_id: str
    unit_id: str

class RelInvestigationUnit(BaseModel):
    ip_id: str
    unit_id: str

class RelPileProbe(BaseModel):
    pile_id: str
    ip_id: str


@router.post("/relationships/investigation-zone", status_code=201)
def link_investigation_zone(body: RelInvestigationZone):
    try:
        run_query(queries.link_investigation_zone(), body.model_dump())
        return {"message": f"InvestigationPoint '{body.ip_id}' located in Zone '{body.zone_id}'"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/relationships/pile-unit", status_code=201)
def link_pile_unit(body: RelPileUnit):
    try:
        run_query(queries.link_pile_unit(), body.model_dump())
        return {"message": f"Pile '{body.pile_id}' in unit '{body.unit_id}'"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/relationships/investigation-unit", status_code=201)
def link_investigation_unit(body: RelInvestigationUnit):
    try:
        run_query(queries.link_investigation_unit(), body.model_dump())
        return {"message": f"InvestigationPoint '{body.ip_id}' in unit '{body.unit_id}'"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/relationships/pile-probe", status_code=201)
def link_pile_probe(body: RelPileProbe):
    try:
        run_query(queries.link_pile_nearest_probe(), body.model_dump())
        return {"message": f"Pile '{body.pile_id}' nearest probe '{body.ip_id}'"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Bulk variants (used by the ingestion parsers) ─────────────────────────────

class BulkPilesReal(BaseModel):
    piles: list[PileReal]

class BulkZonesReal(BaseModel):
    zones: list[ZoneReal]

class BulkInvestigation(BaseModel):
    points: list[InvestigationPoint]

class BulkLoadTests(BaseModel):
    tests: list[LoadTest]


@router.post("/pile/upsert/bulk", status_code=200)
def bulk_upsert_piles(body: BulkPilesReal):
    done, errors = 0, []
    for i, p in enumerate(body.piles):
        try:
            run_query(queries.upsert_pile(), {"id": p.id, "props": _props(p)}); done += 1
        except Exception as e:
            errors.append(f"row {i + 1} ({p.id}): {e}")
    return {"upserted": done, "total": len(body.piles), "errors": errors}


@router.post("/zone/upsert/bulk", status_code=200)
def bulk_upsert_zones(body: BulkZonesReal):
    done, errors = 0, []
    for i, z in enumerate(body.zones):
        try:
            run_query(queries.upsert_zone_props(), {"id": z.id, "props": _props(z)}); done += 1
        except Exception as e:
            errors.append(f"row {i + 1} ({z.id}): {e}")
    return {"upserted": done, "total": len(body.zones), "errors": errors}


@router.post("/investigation/bulk", status_code=200)
def bulk_investigation(body: BulkInvestigation):
    done, errors = 0, []
    for i, ip in enumerate(body.points):
        try:
            run_query(queries.upsert_investigation_point(), {"id": ip.id, "props": _props(ip)}); done += 1
        except Exception as e:
            errors.append(f"row {i + 1} ({ip.id}): {e}")
    return {"upserted": done, "total": len(body.points), "errors": errors}


@router.post("/load-test/upsert/bulk", status_code=200)
def bulk_upsert_load_tests(body: BulkLoadTests):
    done, errors = 0, []
    for i, t in enumerate(body.tests):
        try:
            r = run_query(queries.upsert_load_test(),
                          {"id": t.id, "pile_id": t.pile_id, "props": _props(t, drop=("id", "pile_id"))})
            if not r:
                errors.append(f"row {i + 1} ({t.id}): pile '{t.pile_id}' not found")
            else:
                done += 1
        except Exception as e:
            errors.append(f"row {i + 1} ({t.id}): {e}")
    return {"upserted": done, "total": len(body.tests), "errors": errors}