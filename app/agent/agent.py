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
    "You have access to a graph database of real geotechnical investigation data. "

    "TOOL PARAMETER RULES — critical, follow exactly: "
    "(1) The parameter site_id is always the actual string id of the site, e.g. 'Maryvale'. "
    "    Never pass the word 'site_id' or a variable name — pass the real value. "
    "(2) Call tool_list_sites first if you don't know the exact site_id. "
    "(3) For whole-database questions ('how many sites total', 'how many zones across all sites'), "
    "    call tool_db_summary. "
    "(4) For counts within one site ('how many piles in Maryvale'), call tool_site_counts. "
    "(5) For pile embedment shortfall ('piles that did not reach depth'), call tool_pile_refusal_count "
    "    then tool_pile_refusals for the list. "
    "(6) For pile test pass/fail counts, call tool_pile_test_summary. "
    "(7) Never guess any number — always retrieve from the graph. "

    "AVAILABLE TOOLS (call ONLY these, never invent tool names): tool_list_sites, tool_db_summary, tool_site_counts, tool_list_zones, tool_zones_by_decision, tool_zone_detail, tool_pile_test_summary, tool_pile_tests, tool_pile_refusal_count, tool_pile_refusals, tool_dpsh_refusals, tool_ground_profile. "
    "If a question cannot be answered with these tools, explain that clearly — do NOT invent or guess tool names like tool_pile_zone_summary. "
    "Unsupported queries (say so, don't attempt): average embedment depth by soil type; joining piles to borehole soil profiles; spatial intersection queries. "

    "CONFIDENCE: After answering, add a line starting with 'CONFIDENCE:' followed by a number "
    "0-100 indicating how certain you are based on the data retrieved. "
    "Then add 'REASONING:' followed by 1-3 sentences naming which tool(s) you called and "
    "quoting the EXACT numbers from the tool output verbatim — never recall or round. "
    "Example: 'Called tool_site_counts for Maryvale which returned pile_locations=113.' "

    "Answer concisely. Lead with the number for count questions."
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
        ],
    )