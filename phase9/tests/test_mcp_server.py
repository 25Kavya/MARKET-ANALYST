import pytest

from phase9 import cache_store, mcp_server
from phase9.groq_client import GroqError


@pytest.fixture(autouse=True)
def _temp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(cache_store, "DB_PATH", tmp_path / "test_mcp_cache.db")


def test_cache_miss_calls_groq_once_and_caches(monkeypatch):
    calls = []

    def fake_call_groq(system_prompt, user_prompt):
        calls.append(user_prompt)
        return {"mode": "single", "reasoning": "fake"}

    monkeypatch.setattr(mcp_server, "call_groq", fake_call_groq)

    result = mcp_server.classify_intent_mode("how is infosys doing", ["INFY.NS"], False, False)

    assert result == {"mode": "single", "reasoning": "fake"}
    assert len(calls) == 1

    cache_key = mcp_server.compute_cache_key(mcp_server.TOOL_NAME, "how is infosys doing", mcp_server.PROMPT_VERSION)
    assert cache_store.get_cached(mcp_server.TOOL_NAME, cache_key) == result


def test_cache_hit_never_calls_groq(monkeypatch):
    calls = []

    def fake_call_groq(system_prompt, user_prompt):
        calls.append(user_prompt)
        return {"mode": "portfolio", "reasoning": "fake"}

    monkeypatch.setattr(mcp_server, "call_groq", fake_call_groq)

    first = mcp_server.classify_intent_mode("infosys and tcs and reliance", ["INFY.NS", "TCS.NS", "RELIANCE.NS"], False, False)
    second = mcp_server.classify_intent_mode("infosys and tcs and reliance", ["INFY.NS", "TCS.NS", "RELIANCE.NS"], False, False)

    assert first == second
    assert len(calls) == 1  # second call was a cache hit, groq not re-invoked


def test_groq_error_propagates_and_is_not_cached(monkeypatch):
    def failing_call_groq(system_prompt, user_prompt):
        raise GroqError("simulated groq outage")

    monkeypatch.setattr(mcp_server, "call_groq", failing_call_groq)

    with pytest.raises(GroqError):
        mcp_server.classify_intent_mode("compare mahindra and reliance", ["M&M.NS", "RELIANCE.NS"], True, False)

    cache_key = mcp_server.compute_cache_key(mcp_server.TOOL_NAME, "compare mahindra and reliance", mcp_server.PROMPT_VERSION)
    assert cache_store.get_cached(mcp_server.TOOL_NAME, cache_key) is None


def test_invalid_mode_from_groq_raises_and_is_not_cached(monkeypatch):
    def bad_call_groq(system_prompt, user_prompt):
        return {"mode": "not-a-real-mode", "reasoning": "oops"}

    monkeypatch.setattr(mcp_server, "call_groq", bad_call_groq)

    with pytest.raises(GroqError):
        mcp_server.classify_intent_mode("some query", ["INFY.NS"], False, False)

    cache_key = mcp_server.compute_cache_key(mcp_server.TOOL_NAME, "some query", mcp_server.PROMPT_VERSION)
    assert cache_store.get_cached(mcp_server.TOOL_NAME, cache_key) is None
