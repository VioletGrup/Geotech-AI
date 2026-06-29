from functools import lru_cache

# from app.config import (
#     ANTHROPIC_API_KEY,
#     ANTHROPIC_MODEL,
#     GEMINI_API_KEY,
#     GEMINI_MODEL,
#     GEMINI_BASE_URL,
#     OPENAI_API_KEY,
#     OPENAI_MODEL,
#     AZURE_OPENAI_ENDPOINT,
#     AZURE_OPENAI_API_KEY,
#     AZURE_OPENAI_DEPLOYMENT,
#     AZURE_OPENAI_API_VERSION,
# )

from app.config import (
    GROQ_API_KEY,
    GROQ_BASE_URL,
    GROQ_MODEL
)

INSTRUCTIONS = (
    "You are a geotechnical advisor for solar farm pile construction. "
    "Answer questions using the database tools provided. "

    "RULES — follow exactly: "
    "1. Call ONE tool per turn. Never call two or more tools simultaneously. "
    "2. For any question about a named site or zone, always call tool_list_sites first "
    "   to get the site_id, then call the appropriate tool with that site_id. "
    "3. Never answer factual questions from memory. Always use a tool. "
    "4. Answer concisely. Lead with the number for count questions. "

    "EXAMPLES of correct two-step sequences: "
    "Q: how many [boreholes / pile locations / pile tests / DPSH probes / test pits] in zone X → "
    "   Step 1: tool_list_sites() "
    "   Step 2: tool_zone_detail(site_id=<from step 1>, zone_id=<zone id from question>) "
    "   Answer: report the relevant field (boreholes / pile_locations / pile_tests / dpsh_probes / test_pits). "
    "   NEVER call tool_site_counts or tool_zones_by_decision for zone-level count questions. "
    "   tool_zone_detail returns ALL zone counts in one call — do not make additional calls after it. "
    "Q: how many piles in Maryvale → "
    "   Step 1: tool_list_sites() "
    "   Step 2: tool_site_counts(site_id=<from step 1>) "
    "   Answer: report pile_locations from the result. "
    "Q: which zones are pre-drilled → "
    "   Step 1: tool_list_sites() "
    "   Step 2: tool_zones_by_decision(site_id=<from step 1>, decision='Pre-Drill') "
    "   Answer: list the zones."
    "Q: average pile embedment depth in Maryvale / in zone X → "
    "   Step 1: tool_list_sites() "
    "   Step 2: tool_avg_embedment(site_id=<from step 1>, zone_id=<if zone mentioned>) "
    "   Answer: report avg_embedment_m and avg_target_depth_m from the result. "
)


class AgentNotConfiguredError(RuntimeError):
    """Raised when agent-framework is not installed or no LLM provider is set."""


def _build_client():
    # # Claude first if configured (native Anthropic client from agent-framework-anthropic).
    # if ANTHROPIC_API_KEY:
    #     try:
    #         from agent_framework.anthropic import AnthropicClient
    #     except ImportError as exc:
    #         raise AgentNotConfiguredError(
    #             "agent-framework-anthropic is not installed. "
    #             "Run: pip install agent-framework-anthropic"
    #         ) from exc
    #     return AnthropicClient(api_key=ANTHROPIC_API_KEY, model=ANTHROPIC_MODEL)

    # # Gemini via its OpenAI-compatible endpoint. Must use the chat-completions
    # # client — Gemini's compat layer implements /chat/completions, not /responses.
    # if GEMINI_API_KEY:
    #     try:
    #         from agent_framework.openai import OpenAIChatCompletionClient
    #     except ImportError as exc:
    #         raise AgentNotConfiguredError(
    #             "agent-framework is not installed. Run: pip install agent-framework"
    #         ) from exc
    #     return OpenAIChatCompletionClient(
    #         model=GEMINI_MODEL,
    #         api_key=GEMINI_API_KEY,
    #         base_url=GEMINI_BASE_URL,
    #     )

    # # Lazy import so the FastAPI app boots even before agent-framework is installed.
    # try:
    #     from agent_framework.openai import OpenAIChatClient
    # except ImportError as exc:
    #     raise AgentNotConfiguredError(
    #         "agent-framework is not installed. Run: pip install agent-framework"
    #     ) from exc

    # # OpenAIChatClient also targets Azure OpenAI when azure_endpoint is supplied.
    # if AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY:
    #     return OpenAIChatClient(
    #         model=AZURE_OPENAI_DEPLOYMENT,
    #         azure_endpoint=AZURE_OPENAI_ENDPOINT,
    #         api_key=AZURE_OPENAI_API_KEY,
    #         api_version=AZURE_OPENAI_API_VERSION,
    #     )
    # if OPENAI_API_KEY:
    #     return OpenAIChatClient(model=OPENAI_MODEL, api_key=OPENAI_API_KEY)

    # raise AgentNotConfiguredError(
    #     "No LLM configured. Set ANTHROPIC_API_KEY, GEMINI_API_KEY, OPENAI_API_KEY, "
    #     "or AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY."
    # )
    if GROQ_API_KEY:
        from agent_framework.openai import OpenAIChatCompletionClient

        return OpenAIChatCompletionClient(
            model=GROQ_MODEL, api_key=GROQ_API_KEY, base_url=GROQ_BASE_URL,
    )


@lru_cache(maxsize=1)
def get_agent():
    """Build (once) the geotech advisor agent with its graph-backed tools."""
    try:
        from agent_framework import Agent
        from app.agent.tools import (
            tool_list_sites,
            tool_db_summary,
            tool_site_counts,
            tool_list_zones,
            tool_zones_by_decision,
            tool_zone_detail,
            tool_pile_test_summary,
            tool_pile_tests,
            tool_pile_refusal_count,
            tool_pile_refusals,
            tool_dpsh_refusals,
            tool_ground_profile,
            tool_zone_pile_ids,
            tool_db_soil_types,
            tool_zone_pile_count,
            tool_zone_borehole_count,
            tool_zone_testpit_count,
            tool_zone_dpsh_count,
            tool_zone_dpsh_coordinates,
            tool_avg_embedment,
        )
    except ImportError as exc:
        raise AgentNotConfiguredError(
            "agent-framework is not installed. Run: pip install agent-framework"
        ) from exc

    return Agent(
        _build_client(),
        INSTRUCTIONS,
        name="geotech-advisor",
        tools=[
            tool_list_sites,
            tool_db_summary,
            tool_site_counts,
            tool_list_zones,
            tool_zones_by_decision,
            tool_zone_detail,
            tool_pile_test_summary,
            tool_pile_tests,
            tool_pile_refusal_count,
            tool_pile_refusals,
            tool_dpsh_refusals,
            tool_ground_profile,
            tool_zone_pile_ids,
            tool_db_soil_types,
            tool_zone_pile_count,
            tool_zone_borehole_count,
            tool_zone_testpit_count,
            tool_zone_dpsh_count,
            tool_zone_dpsh_coordinates,
            tool_avg_embedment,
        ],
    )