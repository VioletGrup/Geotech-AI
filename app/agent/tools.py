"""
tools.py  —  Copilot agent tools (schema v3, site-scoped).

Discovery workflow the LLM must follow:
  1. tool_list_sites         — find site_id when user mentions a site by name
  2. tool_db_summary         — answer whole-database count questions
  3. tool_site_counts        — answer "how many X in site Y" questions
  4. tool_list_zones         — discover zone ids before drilling into one
  5. tool_zones_by_decision  — list pre-drill or driven zones
  6. tool_zone_detail        — full detail on one zone
  7. tool_pile_test_summary  — pass/fail counts
  8. tool_pile_tests         — individual test rows
  9. tool_pile_refusal_count — how many piles short of embedment (with stats)
 10. tool_pile_refusals      — individual refusal rows
 11. tool_dpsh_refusals      — DPSH probe refusal depths
 12. tool_ground_profile     — soil layers at a borehole or test pit
"""
from typing import Annotated, Optional

from pydantic import Field
from agent_framework import tool

from app.graphrag.retrieve import (
    get_db_soil_types,
    list_sites,
    get_db_summary,
    get_site_counts,
    list_zones,
    get_zones_by_decision,
    get_zone_summary,
    get_pile_test_summary,
    get_pile_tests,
    get_pile_refusal_count,
    get_pile_refusals,
    get_dpsh_refusals,
    get_ground_profile,
    get_zones_no_decision,
    get_undecided_zone_count,
    get_zone_pile_ids
)


# ── Discovery ──────────────────────────────────────────────────────────────────

@tool(description=(
    "List every site in the graph with its name, id, status and zone count. "
    "Call this first whenever the user mentions a site by name to get the correct site_id."
))
def tool_list_sites() -> dict:
    rows = list_sites()
    return {"n_sites": len(rows), "sites": rows}


@tool(description=(
    "Return total counts across the entire database: sites, zones, pile locations, "
    "DPSH probes, boreholes, test pits. "
    "Use for questions like 'how many sites are in the database', "
    "'how many zones in total', 'how many piles in the graph'."
))
def tool_db_summary() -> dict:
    return get_db_summary()


@tool(description=(
    "Return counts for a single site: zones, pile locations, pile tests, DPSH probes, "
    "boreholes, test pits. "
    "Use for 'how many zones in Maryvale', 'how many piles in site X'. "
    "IMPORTANT: site_id is the id value of the site (e.g. 'Maryvale'), NOT the word 'site_id'."
))
def tool_site_counts(
    site_id: Annotated[str, Field(description="The site's id value e.g. 'Maryvale' or 'SITE-001'. Always a string like the site name.")],
) -> dict:
    return get_site_counts(site_id)


@tool(description=(
    "List all zones in a site with their pre-drill/driven decision and content counts. "
    "Use this to discover zone ids before querying a specific zone."
))
def tool_list_zones(
    site_id: Annotated[str, Field(description="Site id")],
) -> dict:
    rows = list_zones(site_id)
    n_pre  = sum(1 for r in rows if r.get("decision") == "Pre-Drill")
    n_driv = sum(1 for r in rows if r.get("decision") == "Driven")
    n_und  = sum(1 for r in rows if not r.get("decision"))
    return {"n_zones": len(rows), "pre_drill": n_pre,
            "driven": n_driv, "undecided": n_und, "zones": rows}


@tool(description=(
    "Return all zones with a given pre-drill/driven decision, or all undecided zones. "
    "decision = 'Pre-Drill', 'Driven', or null for undecided."
))
def tool_zones_by_decision(
    site_id:  Annotated[str, Field(description="Site id")],
    decision: Annotated[Optional[str], Field(
        description="'Pre-Drill', 'Driven', or null for zones without a decision"
    )] = None,
) -> dict:
    rows = get_zones_by_decision(site_id, decision)
    return {"n": len(rows), "decision": decision, "zones": rows}

@tool(description=(
     "Return all zones in a site that have no pre-drill or driven decision set yet. "   
     "Returns a list of zone ids. For just the count, use tool_undecided_zone_count."
))
def tool_zones_no_decision(
    site_id: Annotated[str, Field(description="The site id value e.g. 'Maryvale'")],
) -> dict:
    rows = get_zones_no_decision(site_id)
    return {"n_undecided": len(rows), "zones": rows}

@tool(description=(
    "Return the COUNT of zones with no pre-drill or driven decision in a site. "
    "Use for 'how many zones have no decision yet in Maryvale'. "
    "For the actual list of which zones, use tool_zones_no_decision."
))
def tool_undecided_zone_count(
    site_id: Annotated[str, Field(description="The site id value e.g. 'Maryvale'")],
) -> dict:
    return get_undecided_zone_count(site_id)
    
@tool(description=(
    "Return full detail for a single zone: decision, tracker counts, and counts of "
    "pile locations, pile tests, DPSH probes, boreholes, test pits."
))
def tool_zone_detail(
    site_id: Annotated[str, Field(description="Site id")],
    zone_id: Annotated[str, Field(description="Zone id, e.g. '1.1'")],
) -> dict:
    data = get_zone_summary(site_id, zone_id)
    return {"found": bool(data), "summary": data}

@tool(description=(
        "Return a list of pile ids of all the piles in the specified zone"
))
def tool_zone_pile_ids(
    site_id: Annotated[str, Field(description="Site id")],
    zone_id: Annotated[str, Field(description="Zone to search within")]
) -> dict:
    rows = get_zone_pile_ids(site_id, zone_id)
    return {"n": len(rows), "piles": rows}

@tool(description=(
    "Return all SoilType nodes in the database with their unit_no, name and description."
))
def tool_db_soil_types() -> dict:
    """Return all SoilType nodes in the database with their unit_no, name and description."""
    rows = get_db_soil_types()
    return {"n": len(rows), "soil_types": rows}

# ── Pile tests ─────────────────────────────────────────────────────────────────

@tool(description=(
    "Return a summary count of pile load tests for a site or zone: "
    "total, passed, failed, undecided. "
    "Use for 'how many pile tests passed in site X', 'how many failed in zone 1.1'."
))
def tool_pile_test_summary(
    site_id: Annotated[str, Field(description="Site id")],
    zone_id: Annotated[Optional[str], Field(description="Zone id to filter by")] = None,
) -> dict:
    return get_pile_test_summary(site_id, zone_id)


@tool(description=(
    "Return individual pile load test rows with pass/fail and load proportions "
    "(tension / lateral / compression as % of Ed). "
    "Filter by zone and/or pass status. Use passed=false to list failures."
))
def tool_pile_tests(
    site_id: Annotated[str, Field(description="Site id")],
    zone_id: Annotated[Optional[str], Field(description="Zone id to filter by")] = None,
    passed:  Annotated[Optional[bool], Field(
        description="true = passed only, false = failed only, omit for all"
    )] = None,
    top_k:   Annotated[int, Field(description="Max rows to return", ge=1, le=200)] = 25,
) -> dict:
    rows = get_pile_tests(site_id, zone_id=zone_id, passed=passed, top_k=top_k)
    return {"n": len(rows), "results": rows}


# ── Pile embedment refusal ─────────────────────────────────────────────────────

@tool(description=(
    "Return the COUNT of piles that did not reach their target embedment depth, "
    "plus average and maximum shortfall in metres. "
    "Use for 'how many piles in Maryvale did not reach their embedment depth', "
    "'how many piles fell short in zone 3.2'."
))
def tool_pile_refusal_count(
    site_id: Annotated[str, Field(description="Site id")],
    zone_id: Annotated[Optional[str], Field(description="Zone id to filter by")] = None,
) -> dict:
    return get_pile_refusal_count(site_id, zone_id)


@tool(description=(
    "List individual piles that did not reach their target embedment depth, "
    "with the shortfall (m) for each. Sorted worst-first. "
    "Use after tool_pile_refusal_count to get the actual pile ids."
))
def tool_pile_refusals(
    site_id: Annotated[str, Field(description="Site id")],
    zone_id: Annotated[Optional[str], Field(description="Zone id to filter by")] = None,
    top_k:   Annotated[int, Field(description="Max rows", ge=1, le=200)] = 50,
) -> dict:
    rows = get_pile_refusals(site_id, zone_id=zone_id, top_k=top_k)
    return {"n": len(rows), "results": rows}


# ── DPSH ───────────────────────────────────────────────────────────────────────

@tool(description=(
    "Return DPSH probe refusal depths (m) across a site or zone. "
    "Filter with max_depth to surface only the shallow refusals that influence "
    "pre-drill decisions. Sorted shallowest-first."
))
def tool_dpsh_refusals(
    site_id:   Annotated[str, Field(description="Site id")],
    zone_id:   Annotated[Optional[str], Field(description="Zone id to filter by")] = None,
    max_depth: Annotated[Optional[float], Field(
        description="Only include refusals at or above this depth (m)"
    )] = None,
    top_k:     Annotated[int, Field(description="Max rows", ge=1, le=200)] = 50,
) -> dict:
    rows = get_dpsh_refusals(site_id, zone_id=zone_id, max_depth=max_depth, top_k=top_k)
    return {"n": len(rows), "results": rows}


# ── Ground profile ─────────────────────────────────────────────────────────────

@tool(description=(
    "Return the layered ground profile (soil units by depth) for a borehole or "
    "test pit. Pass its id, e.g. 'BH02' or 'TP05'."
))
def tool_ground_profile(
    site_id:     Annotated[str, Field(description="Site id")],
    location_id: Annotated[str, Field(description="BoreHole or TestPit id, e.g. 'BH02'")],
) -> dict:
    rows = get_ground_profile(site_id, location_id)
    return {"location": location_id, "n_layers": len(rows), "layers": rows}