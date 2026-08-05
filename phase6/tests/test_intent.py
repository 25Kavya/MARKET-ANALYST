import os

import pytest

import phase6.intent as intent_module
from phase6.intent import classify_intent
from phase9.mcp_client import McpUnavailableError


@pytest.fixture(autouse=True)
def _fake_mcp(monkeypatch):
    """Reproduce the old heuristic's decision via a fake MCP call, so these
    tests stay fast/deterministic and don't depend on a live MCP server or
    Groq call (mirrors how test_sentiment_agent.py monkeypatches search_news
    for its failure-path test)."""

    def fake_classify_mode_via_mcp(query, tickers, is_compare_keyword, is_portfolio_keyword):
        mode = intent_module._heuristic_mode(is_compare_keyword, is_portfolio_keyword, tickers)
        return {"mode": mode, "reasoning": "fake"}

    monkeypatch.setattr(intent_module, "classify_mode_via_mcp", fake_classify_mode_via_mcp)


def test_classify_intent_portfolio_query():
    query = "hows my portfolio doing (tata motors, infosys, cupid ......etc and other indian stocks)"
    result = classify_intent(query)

    assert result["mode"] == "portfolio"
    assert result["tickers"] == ["TMPV.NS", "INFY.NS", "CUPID.NS"]


def test_classify_intent_single_query():
    result = classify_intent("how is infosys doing")

    assert result["mode"] == "single"
    assert result["tickers"] == ["INFY.NS"]


def test_classify_intent_compare_query():
    result = classify_intent("compare the stocks between the mahindra and reliance")

    assert result["mode"] == "compare"
    assert result["tickers"] == ["M&M.NS", "RELIANCE.NS"]


def test_classify_intent_unknown_query_no_ticker_mentioned():
    result = classify_intent("what is the weather today")

    assert result["mode"] == "unknown"
    assert result["tickers"] == []


def test_classify_intent_portfolio_via_multiple_tickers_without_keyword():
    # no "portfolio"/"compare" keyword, but 3 companies mentioned -> portfolio fallback
    result = classify_intent("infosys and reliance and tcs")

    assert result["mode"] == "portfolio"
    assert set(result["tickers"]) == {"INFY.NS", "RELIANCE.NS", "TCS.NS"}


def test_classify_intent_compare_keyword_with_only_one_ticker_falls_back_to_single():
    result = classify_intent("compare infosys please")

    assert result["mode"] == "single"
    assert result["tickers"] == ["INFY.NS"]


def test_guardrail_corrects_inconsistent_llm_mode(monkeypatch):
    # LLM says "compare" but only one ticker was actually extracted -- the
    # guardrail must not trust that and should fall back to the heuristic's
    # downgrade rule instead of propagating a nonsensical route.
    monkeypatch.setattr(
        intent_module, "classify_mode_via_mcp",
        lambda query, tickers, is_compare_keyword, is_portfolio_keyword: {"mode": "compare", "reasoning": "bad"},
    )

    result = classify_intent("how is infosys doing")

    assert result["mode"] == "single"
    assert result["tickers"] == ["INFY.NS"]


def test_mcp_unavailable_falls_back_to_heuristic(monkeypatch, caplog):
    def raise_unavailable(query, tickers, is_compare_keyword, is_portfolio_keyword):
        raise McpUnavailableError("simulated MCP outage")

    monkeypatch.setattr(intent_module, "classify_mode_via_mcp", raise_unavailable)

    with caplog.at_level("WARNING"):
        result = classify_intent("compare the stocks between the mahindra and reliance")

    assert result["mode"] == "compare"
    assert result["tickers"] == ["M&M.NS", "RELIANCE.NS"]
    assert any("mcp unavailable" in record.message for record in caplog.records)


@pytest.mark.live_llm
@pytest.mark.skipif(
    not os.getenv("RUN_LIVE_LLM_TESTS"),
    reason="set RUN_LIVE_LLM_TESTS=1 to run (costs a real Groq call, requires "
           "phase9/mcp_server.py running separately, and a configured GROQ_API_KEY)",
)
def test_classify_intent_live_mcp_and_groq(monkeypatch):
    # Real end-to-end smoke test. Deliberately gated behind an explicit env
    # var rather than just "GROQ_API_KEY is set", since that key is already
    # configured in this project's .env -- gating on it alone would make this
    # test run (and fail, since no server is up) on every default `pytest`
    # invocation instead of only when explicitly opted into.
    monkeypatch.undo()  # bypass the autouse fake_mcp fixture for this one test

    result = classify_intent("how is infosys doing")

    assert result["mode"] in {"single", "portfolio", "compare", "unknown"}
    assert result["tickers"] == ["INFY.NS"]
