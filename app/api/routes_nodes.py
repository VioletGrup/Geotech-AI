from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.db.neo4j_driver import run_query
from app.db import queries

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
