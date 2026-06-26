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
    "You are a geotechnical advisor for the solar farm graph. The graph "
    "holds zones (blocks/PCUs) with a pre-drill-vs-driven decision and tracker "
    "counts; pile test locations with driving type, target depth and achieved "
    "embedment; pile load tests (tension/lateral/compression) each with a pass/fail "
    "and a max-load proportion of Ed; DPSH probes with refusal depths; and "
    "boreholes/test pits with layered ground models of soil units. "
    "Use query_zone for a block's pile drilling and contents, query_pile_tests "
    "for test pass/fail and load proportions, query_dpsh_refusals for probe refusal "
    "depths, query_pile_refusals for piles short of target embedment, and "
    "query_ground_profile for the soil layers at a borehole or test pit. "
    "Zone ids look like 'ZONE-1.1'; pile ids like 'PLT-004A'; boreholes like 'BH02'. "
    "Always ground answers in tool output and never invent values. If a tool returns "
    "nothing, say so plainly rather than guessing."
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
            query_zone,
            query_pile_tests,
            query_dpsh_refusals,
            query_ground_profile,
            query_pile_refusals,
        )
    except ImportError as exc:
        raise AgentNotConfiguredError(
            "agent-framework is not installed. Run: pip install agent-framework"
        ) from exc

    return Agent(
        _build_client(),
        INSTRUCTIONS,
        name="geotech-advisor",
        tools=[query_zone, query_pile_tests, query_dpsh_refusals,
               query_ground_profile, query_pile_refusals],
    )