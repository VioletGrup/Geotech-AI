from typing import Annotated, Optional

from pydantic import Field
from agent_framework import tool

from app.graphrag.retrieve import (
    get_zone_summary,
    get_pile_tests,
    get_dpsh_refusals,
    get_ground_profile,
    get_pile_refusals,
)


@tool(
    description="Summarise a zone (block/PCU): its pre-drill-vs-driven decision, "
    "tracker counts, and how many pile locations, DPSH probes, boreholes and test "
    "pits sit in it. Pass the full zone id, e.g. 'ZONE-1.1'."
)
def query_zone(
    zone_id: Annotated[str, Field(description="Zone id, e.g. 'ZONE-1.1'")],
) -> dict:
    rows = get_zone_summary(zone_id)
    return {"zone": zone_id, "found": bool(rows), "summary": rows[0] if rows else None}


@tool(
    description="List pile load tests with their pass/fail result and the per-type "
    "load proportions (tension/lateral/compression, % of Ed). Filter by zone id "
    "and/or pass status. Use passed=false to find failures."
)
def query_pile_tests(
    zone_id: Annotated[Optional[str], Field(description="Zone id to filter by, e.g. 'ZONE-13.1'")] = None,
    passed: Annotated[Optional[bool], Field(description="True for passed, False for failed tests")] = None,
    top_k: Annotated[int, Field(description="Max rows", ge=1, le=200)] = 25,
) -> dict:
    rows = get_pile_tests(zone_id=zone_id, passed=passed, top_k=top_k)
    return {"n": len(rows), "results": rows}


@tool(
    description="Return DPSH probe refusal depths (m), optionally filtered to a zone "
    "or to shallow refusals (max_depth). Shallow refusal drives the pile drilling."
)
def query_dpsh_refusals(
    zone_id: Annotated[Optional[str], Field(description="Zone id to filter by")] = None,
    max_depth: Annotated[Optional[float], Field(description="Only refusals at or above this depth (m)")] = None,
    top_k: Annotated[int, Field(description="Max rows", ge=1, le=200)] = 50,
) -> dict:
    rows = get_dpsh_refusals(zone_id=zone_id, max_depth=max_depth, top_k=top_k)
    return {"n": len(rows), "results": rows}


@tool(
    description="Return the layered ground profile (soil units by depth) for a "
    "borehole or test pit, from its ground model. Pass the location id, e.g. 'BH02' or 'TP05'."
)
def query_ground_profile(
    location_id: Annotated[str, Field(description="BoreHole or TestPit id, e.g. 'BH02'")],
) -> dict:
    rows = get_ground_profile(location_id)
    return {"location": location_id, "n_layers": len(rows), "layers": rows}


@tool(
    description="List piles that hit refusal — achieved embedment below target depth — "
    "with the shortfall (m). Optionally filter by zone."
)
def query_pile_refusals(
    zone_id: Annotated[Optional[str], Field(description="Zone id to filter by")] = None,
    top_k: Annotated[int, Field(description="Max rows", ge=1, le=200)] = 50,
) -> dict:
    rows = get_pile_refusals(zone_id=zone_id, top_k=top_k)
    return {"n": len(rows), "results": rows}