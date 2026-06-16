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
    "You are a solar-farm geotechnical advisor. For any question about pile "
    "load capacity, call predict_pile_capacity. For case lookups, call "
    "query_similar_cases. Always report the analog cases behind any number, the "
    "model_status (trained model vs fallback average), and how many cases support "
    "it. Never state a capacity that is not present in tool output. Flag low "
    "confidence when fewer than three cases support a prediction."
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
        from app.agent.tools import predict_pile_capacity, query_similar_cases
    except ImportError as exc:
        raise AgentNotConfiguredError(
            "agent-framework is not installed. Run: pip install agent-framework"
        ) from exc

    return Agent(
        _build_client(),
        INSTRUCTIONS,
        name="geotech-advisor",
        tools=[predict_pile_capacity, query_similar_cases],
    )