from phase1.data.tickers import find_mentioned_tickers
from phase1.logging_config import get_logger
from phase9.mcp_client import McpUnavailableError, classify_mode_via_mcp

logger = get_logger(__name__)

_COMPARE_KEYWORDS = ["compare", " vs ", " vs.", " versus "]
_PORTFOLIO_KEYWORDS = ["portfolio", "my stocks", "my holdings", "holdings"]

_VALID_MODES = {"single", "portfolio", "compare"}


def _heuristic_mode(is_compare_query, is_portfolio_query, tickers):
    """Keyword-rule fallback — used directly when the MCP/Groq path is
    unavailable, and also as the correction target when the LLM's mode
    fails the consistency guardrail below."""
    if is_compare_query and len(tickers) >= 2:
        return "compare"
    elif is_portfolio_query or len(tickers) >= 2:
        return "portfolio"
    elif len(tickers) == 1:
        return "single"
    else:
        return "unknown"


def _guardrail_mode(mode, is_compare_query, is_portfolio_query, tickers):
    """Never fully trust the LLM's (possibly stale-cached) mode — correct it
    back to the heuristic whenever it's inconsistent with the deterministic
    ticker count, e.g. "compare" with fewer than 2 tickers."""
    if mode not in _VALID_MODES:
        return _heuristic_mode(is_compare_query, is_portfolio_query, tickers)
    if mode == "compare" and len(tickers) < 2:
        return _heuristic_mode(is_compare_query, is_portfolio_query, tickers)
    if mode == "single" and len(tickers) != 1:
        return _heuristic_mode(is_compare_query, is_portfolio_query, tickers)
    if mode == "portfolio" and len(tickers) == 0 and not is_portfolio_query:
        return _heuristic_mode(is_compare_query, is_portfolio_query, tickers)
    return mode


def classify_intent(query):
    tickers = find_mentioned_tickers(query)

    padded = f" {query.lower()} "
    is_compare_query = any(kw in padded for kw in _COMPARE_KEYWORDS)
    is_portfolio_query = any(kw in padded for kw in _PORTFOLIO_KEYWORDS)

    try:
        llm_result = classify_mode_via_mcp(query, tickers, is_compare_query, is_portfolio_query)
        mode = _guardrail_mode(llm_result.get("mode"), is_compare_query, is_portfolio_query, tickers)
    except McpUnavailableError as exc:
        logger.warning(
            "intent.classify_intent mcp unavailable, falling back to heuristic query=%r error=%s",
            query, exc,
        )
        mode = _heuristic_mode(is_compare_query, is_portfolio_query, tickers)

    result = {"query": query, "mode": mode, "tickers": tickers}
    logger.info("intent.classify_intent query=%r mode=%s tickers=%s", query, mode, tickers)
    return result
