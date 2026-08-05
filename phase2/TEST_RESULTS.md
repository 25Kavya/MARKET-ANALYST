# Phase 2 Test Results — Technical Analyst (walking skeleton)

**Scope**: `phase2/agents/technical.py`, `phase2/api.py`
**Command**: `python -m pytest phase1/tests phase2/tests -v` (full regression: Phase 1 + Phase 2 together)
**Result**: ✅ 23 passed, 0 failed, 16.69s (14 from Phase 1, 9 new from Phase 2)
**Logging**: confirmed `dump.log` grew to 59 lines across the combined run

## Summary table

| Layer | Test | Status |
|---|---|---|
| agent | `test_analyze_technical_returns_sane_output[INFY.NS]` — indicators, verdict, confidence all sane | PASSED |
| agent | `test_analyze_technical_returns_sane_output[RELIANCE.NS]` | PASSED |
| agent | `test_analyze_technical_returns_sane_output[TMPV.NS]` | PASSED |
| agent | `test_analyze_technical_raises_for_invalid_ticker` — bad ticker propagates `MarketDataError` | PASSED |
| API | `test_health_endpoint` — `GET /health` returns `{"status": "ok"}` | PASSED |
| API | `test_get_technical_endpoint_known_tickers[INFY.NS]` — full UI→API→agent→data path | PASSED |
| API | `test_get_technical_endpoint_known_tickers[RELIANCE.NS]` | PASSED |
| API | `test_get_technical_endpoint_known_tickers[TMPV.NS]` | PASSED |
| API | `test_get_technical_endpoint_invalid_ticker_returns_404` — bad ticker → clean 404, not a crash | PASSED |

## What the agent computes

For a given ticker, `analyze_technical()` pulls ~6 months of daily OHLCV via
Phase 1's `market.get_history` and derives:
- SMA20 / SMA50 (trend)
- RSI(14) (overbought/oversold)
- MACD + signal line (momentum)
- Bollinger Bands (20, 2σ)
- Volume trend (last 5 days vs prior 20)
- Support/resistance (20-day low/high)

Three independent signals (trend, MACD, RSI) each vote bullish/bearish/neutral;
the majority becomes the verdict, and confidence = agreeing votes / 3. All
three signals plus their reasoning strings are returned so the final
synthesizer (Phase 4+) can use them as-is.

## Raw pytest output

```
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-9.1.1, pluggy-1.6.0 -- C:\Users\kavya\AppData\Local\Programs\Python\Python312\python.exe
cachedir: .pytest_cache
rootdir: C:\MARKET-ANALYST
configfile: pytest.ini
plugins: anyio-4.14.2
collecting ... collected 23 items

phase1/tests/test_data_layer.py::test_get_history_returns_rows_for_known_ticker PASSED [  4%]
phase1/tests/test_data_layer.py::test_get_history_raises_for_invalid_ticker PASSED [  8%]
phase1/tests/test_data_layer.py::test_get_fundamentals_returns_expected_fields PASSED [ 13%]
phase1/tests/test_data_layer.py::test_search_news_returns_results PASSED [ 17%]
phase1/tests/test_data_layer.py::test_search_news_respects_max_results PASSED [ 21%]
phase1/tests/test_data_layer.py::test_resolve_ticker_exact_aliases[tata motors-TMPV.NS] PASSED [ 26%]
phase1/tests/test_data_layer.py::test_resolve_ticker_exact_aliases[infosys-INFY.NS] PASSED [ 30%]
phase1/tests/test_data_layer.py::test_resolve_ticker_exact_aliases[cupid-CUPID.NS] PASSED [ 34%]
phase1/tests/test_data_layer.py::test_resolve_ticker_exact_aliases[mahindra-M&M.NS] PASSED [ 39%]
phase1/tests/test_data_layer.py::test_resolve_ticker_exact_aliases[reliance-RELIANCE.NS] PASSED [ 43%]
phase1/tests/test_data_layer.py::test_resolve_ticker_passthrough_symbol PASSED [ 47%]
phase1/tests/test_data_layer.py::test_resolve_ticker_fuzzy_match_typo PASSED [ 52%]
phase1/tests/test_data_layer.py::test_resolve_ticker_raises_for_unknown_name PASSED [ 56%]
phase1/tests/test_data_layer.py::test_resolve_ticker_raises_for_empty_name PASSED [ 60%]
phase2/tests/test_technical_agent.py::test_analyze_technical_returns_sane_output[INFY.NS] PASSED [ 65%]
phase2/tests/test_technical_agent.py::test_analyze_technical_returns_sane_output[RELIANCE.NS] PASSED [ 69%]
phase2/tests/test_technical_agent.py::test_analyze_technical_returns_sane_output[TMPV.NS] PASSED [ 73%]
phase2/tests/test_technical_agent.py::test_analyze_technical_raises_for_invalid_ticker PASSED [ 78%]
phase2/tests/test_technical_agent.py::test_health_endpoint PASSED        [ 82%]
phase2/tests/test_technical_agent.py::test_get_technical_endpoint_known_tickers[INFY.NS] PASSED [ 86%]
phase2/tests/test_technical_agent.py::test_get_technical_endpoint_known_tickers[RELIANCE.NS] PASSED [ 91%]
phase2/tests/test_technical_agent.py::test_get_technical_endpoint_known_tickers[TMPV.NS] PASSED [ 95%]
phase2/tests/test_technical_agent.py::test_get_technical_endpoint_invalid_ticker_returns_404 PASSED [100%]

============================== warnings summary ===============================
..\Users\kavya\AppData\Local\Programs\Python\Python312\Lib\site-packages\fastapi\testclient.py:1
  C:\Users\kavya\AppData\Local\Programs\Python\Python312\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
======================= 23 passed, 1 warning in 16.69s ========================
```

## Real-world data issue found & fixed during this run

The original Phase 1 ticker table mapped "tata motors" → `TATAMOTORS.NS`.
Tata Motors completed a corporate demerger in 2025 splitting into separate
commercial-vehicle and passenger-vehicle entities; `TATAMOTORS.NS` is now
delisted on Yahoo Finance (confirmed via a direct 404 from the API, not a bug
in our code). The Phase 2 walking-skeleton test caught this immediately
because the API route correctly returned 404 instead of a fake result.

**Fix**: updated `phase1/data/tickers.py` so "tata motors" resolves to
`TMPV.NS` (Tata Motors Passenger Vehicles Ltd), the Yahoo Finance successor
symbol. Updated the corresponding expectations in
`phase1/tests/test_data_layer.py` and `phase2/tests/test_technical_agent.py`.
Re-ran the full suite — all 23 tests pass.

## Non-goal for this phase (per PHASES.md)

Streamlit rendering isn't tested here — the UI doesn't exist yet (Phase 7).
This phase only proves the FastAPI route works correctly end-to-end; the
temporary `/stock/{ticker}/technical` route will be removed once Phase 4
wires the Technical Analyst into the LangGraph orchestration.
