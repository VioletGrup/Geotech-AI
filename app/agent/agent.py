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
    "You have access to a graph database of real project data. "

    "CRITICAL RULE — ONE TOOL PER TURN: "
    "You must call only ONE tool at a time. Wait for the result before calling the next tool. "
    "NEVER call two tools in the same response. This will cause an error. "

    "WORKFLOW for any question about a named site: "
    "Turn 1: Call tool_list_sites with no arguments. "
    "Turn 2: Read the site_id from the result. Call the appropriate tool with that site_id. "
    "Turn 3: Answer using the returned data. "

    "TOOL SELECTION — use the first matching rule: "
    "- Question about totals across ALL sites → tool_db_summary() "
    "- Question mentions a site name (any question about Maryvale, site X, etc.) → "
    "  first call tool_list_sites, then use the returned site_id for: "
    "  counts of zones/piles/boreholes/etc at SITE level → tool_site_counts(site_id=...) "
    "  counts/details for a SPECIFIC ZONE (boreholes in zone 7.2, piles in zone 1.1) → tool_zone_detail(site_id=..., zone_id=...) "
    "  list of pile ids in a zone → tool_zone_pile_ids(site_id=..., zone_id=...) "
    "  list of zones → tool_list_zones(site_id=...) "
    "  zones with no decision → tool_zones_by_decision(site_id=..., decision=null) "
    "  pile embedment shortfall count → tool_pile_refusal_count(site_id=...) "
    "  pile embedment shortfall list → tool_pile_refusals(site_id=...) "
    "  pile test pass/fail counts → tool_pile_test_summary(site_id=...) "
    "  DPSH refusal depths → tool_dpsh_refusals(site_id=...) "
    "  ground profile at a borehole → tool_ground_profile(site_id=..., location_id=...) "

    "NEVER answer a factual question about counts or data from memory. "
    "If you have not called a tool yet, call one before answering. "
    "Only say a question is unsupported if no tool in the list above can help. "
    "Unsupported (say so): average embedment by soil type; spatial joins between piles and soil. "

    "Answer concisely. Lead with the number for count questions. "
    "Do not add CONFIDENCE or REASONING lines."
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
            tool_undecided_zone_count,
            tool_zone_detail,
            tool_pile_test_summary,
            tool_pile_tests,
            tool_pile_refusal_count,
            tool_pile_refusals,
            tool_dpsh_refusals,
            tool_ground_profile,
            tool_zone_pile_ids,
            tool_zone_pile_ids,
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
            tool_undecided_zone_count,
            tool_zone_detail,
            tool_pile_test_summary,
            tool_pile_tests,
            tool_pile_refusal_count,
            tool_pile_refusals,
            tool_dpsh_refusals,
            tool_ground_profile,
            tool_zone_pile_ids,
            tool_zone_pile_ids,        
            ],
    )