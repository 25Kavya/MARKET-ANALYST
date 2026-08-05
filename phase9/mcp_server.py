import os

from mcp.server.fastmcp import FastMCP

from phase1.logging_config import get_logger
from phase9 import cache_store
from phase9.cache_key import compute_cache_key
from phase9.groq_client import GroqError, call_groq

logger = get_logger(__name__)

TOOL_NAME = "classify_intent_mode"
PROMPT_VERSION = "v1"

_SYSTEM_PROMPT = (
    "You classify a user's natural-language question about Indian stocks into "
    "exactly one mode: \"single\" (one stock), \"portfolio\" (multiple holdings, "
    "no direct comparison implied), or \"compare\" (an explicit head-to-head "
    "comparison between stocks). You are given the extracted ticker symbols and "
    "two keyword hints already detected by a simple rule-based pass; use them as "
    "context, but read the actual query for nuance the keyword hints might miss "
    "(e.g. implicit comparisons like \"which of these is the better buy\"). "
    "Respond with a JSON object: {\"mode\": \"single\"|\"portfolio\"|\"compare\", "
    "\"reasoning\": \"<one short sentence>\"}."
)

_mcp_port = int(os.getenv("MCP_SERVER_PORT", "8100"))
mcp = FastMCP("market-analyst-intent", host="127.0.0.1", port=_mcp_port)


def _build_user_prompt(query, tickers, is_compare_keyword, is_portfolio_keyword):
    return (
        f"Query: {query!r}\n"
        f"Extracted tickers: {tickers}\n"
        f"Keyword hint - looks like a comparison: {is_compare_keyword}\n"
        f"Keyword hint - looks like a portfolio question: {is_portfolio_keyword}"
    )


@mcp.tool()
def classify_intent_mode(query: str, tickers: list, is_compare_keyword: bool, is_portfolio_keyword: bool) -> dict:
    """Decide single/portfolio/compare mode for a query, checking the SQLite
    cache before ever calling Groq, and caching a fresh Groq answer."""
    cache_key = compute_cache_key(TOOL_NAME, query, PROMPT_VERSION)

    cached = cache_store.get_cached(TOOL_NAME, cache_key)
    if cached is not None:
        return cached

    user_prompt = _build_user_prompt(query, tickers, is_compare_keyword, is_portfolio_keyword)

    try:
        result = call_groq(_SYSTEM_PROMPT, user_prompt)
    except GroqError as exc:
        logger.error("mcp_server.classify_intent_mode groq failure query=%r error=%s", query, exc)
        raise

    if result.get("mode") not in {"single", "portfolio", "compare"}:
        logger.error("mcp_server.classify_intent_mode invalid mode from groq result=%r", result)
        raise GroqError(f"Groq returned an invalid mode: {result.get('mode')!r}")

    cache_store.set_cached(TOOL_NAME, cache_key, PROMPT_VERSION, query, result)
    return result


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
