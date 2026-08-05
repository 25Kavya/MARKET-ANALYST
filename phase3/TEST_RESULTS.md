# Phase 3 Test Results — Sentiment + Financial Analysts

**Scope**: `phase3/agents/sentiment.py`, `phase3/agents/financial.py`, `phase3/api.py`
**Command**: `python -m pytest phase1/tests phase2/tests phase3/tests -v` (full regression: Phase 1 + 2 + 3 together)
**Result**: ✅ 39 passed, 0 failed, 48.22s (14 Phase 1 + 9 Phase 2 + 16 new Phase 3)
**Logging**: confirmed `dump.log` grew to 118 lines across the combined run

## Design note: agents catch errors, they don't raise

Unlike Phase 2's `technical.py` (which lets `MarketDataError` propagate up to
the API layer), Phase 3's agents catch their own exceptions internally and
return `{"status": "error", "error": "..."}` instead — per the Phase 3 plan
in `PHASES.md` ("confirm errors are caught and logged, not raised"). This is
also what `ARCHITECTURE.md` calls for eventually across all agents, so one
flaky data source doesn't take down a whole multi-ticker query once Phase 4
fans these out in parallel. The temporary `phase3/api.py` routes inspect the
`status` field and translate an agent-level error into an HTTP 502.

## What each agent does

**Sentiment Analyst** (`sentiment.py`) — pulls recent headlines via Phase 1's
`search.py`, then scores them with a keyword lexicon (positive/negative
finance terms) rather than an LLM call, since no `ANTHROPIC_API_KEY` is
configured yet. This keeps the agent fully testable without secrets or paid
API calls; swapping in real LLM summarization later is a drop-in replacement
for `_score_headlines`.

**Financial Analyst** (`financial.py`) — pulls fundamentals via Phase 1's
`market.py` and votes across three signals: profitability (profit margin),
growth (revenue growth), and leverage (debt/equity). Missing data points
count as neutral rather than being penalized.

## Summary table

| Layer | Test | Status |
|---|---|---|
| sentiment agent | `test_analyze_sentiment_returns_sane_output[INFY.NS / RELIANCE.NS / TMPV.NS]` | PASSED |
| sentiment agent | `test_analyze_sentiment_catches_search_failure_and_does_not_raise` (mocked outage) | PASSED |
| financial agent | `test_analyze_financial_returns_sane_output_infy` / `_reliance` / `_tmpv` | PASSED |
| financial agent | `test_analyze_financial_catches_bad_ticker_and_does_not_raise` (real invalid ticker) | PASSED |
| API | `test_health_endpoint` | PASSED |
| API | `test_get_sentiment_endpoint_known_tickers[INFY.NS / RELIANCE.NS / TMPV.NS]` | PASSED |
| API | `test_get_financial_endpoint_known_tickers[INFY.NS / RELIANCE.NS / TMPV.NS]` | PASSED |
| API | `test_get_financial_endpoint_invalid_ticker_returns_502` | PASSED |

## Raw pytest output

```
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-9.1.1, pluggy-1.6.0 -- C:\Users\kavya\AppData\Local\Programs\Python\Python312\python.exe
cachedir: .pytest_cache
rootdir: C:\MARKET-ANALYST
configfile: pytest.ini
plugins: anyio-4.14.2
collecting ... collected 39 items

phase1/tests/test_data_layer.py::test_get_history_returns_rows_for_known_ticker PASSED [  2%]
phase1/tests/test_data_layer.py::test_get_history_raises_for_invalid_ticker PASSED [  5%]
phase1/tests/test_data_layer.py::test_get_fundamentals_returns_expected_fields PASSED [  7%]
phase1/tests/test_data_layer.py::test_search_news_returns_results PASSED [ 10%]
phase1/tests/test_data_layer.py::test_search_news_respects_max_results PASSED [ 12%]
phase1/tests/test_data_layer.py::test_resolve_ticker_exact_aliases[tata motors-TMPV.NS] PASSED [ 15%]
phase1/tests/test_data_layer.py::test_resolve_ticker_exact_aliases[infosys-INFY.NS] PASSED [ 17%]
phase1/tests/test_data_layer.py::test_resolve_ticker_exact_aliases[cupid-CUPID.NS] PASSED [ 20%]
phase1/tests/test_data_layer.py::test_resolve_ticker_exact_aliases[mahindra-M&M.NS] PASSED [ 23%]
phase1/tests/test_data_layer.py::test_resolve_ticker_exact_aliases[reliance-RELIANCE.NS] PASSED [ 25%]
phase1/tests/test_data_layer.py::test_resolve_ticker_passthrough_symbol PASSED [ 28%]
phase1/tests/test_data_layer.py::test_resolve_ticker_fuzzy_match_typo PASSED [ 30%]
phase1/tests/test_data_layer.py::test_resolve_ticker_raises_for_unknown_name PASSED [ 33%]
phase1/tests/test_data_layer.py::test_resolve_ticker_raises_for_empty_name PASSED [ 35%]
phase2/tests/test_technical_agent.py::test_analyze_technical_returns_sane_output[INFY.NS] PASSED [ 38%]
phase2/tests/test_technical_agent.py::test_analyze_technical_returns_sane_output[RELIANCE.NS] PASSED [ 41%]
phase2/tests/test_technical_agent.py::test_analyze_technical_returns_sane_output[TMPV.NS] PASSED [ 43%]
phase2/tests/test_technical_agent.py::test_analyze_technical_raises_for_invalid_ticker PASSED [ 46%]
phase2/tests/test_technical_agent.py::test_health_endpoint PASSED        [ 48%]
phase2/tests/test_technical_agent.py::test_get_technical_endpoint_known_tickers[INFY.NS] PASSED [ 51%]
phase2/tests/test_technical_agent.py::test_get_technical_endpoint_known_tickers[RELIANCE.NS] PASSED [ 53%]
phase2/tests/test_technical_agent.py::test_get_technical_endpoint_known_tickers[TMPV.NS] PASSED [ 56%]
phase2/tests/test_technical_agent.py::test_get_technical_endpoint_invalid_ticker_returns_404 PASSED [ 58%]
phase3/tests/test_api.py::test_health_endpoint PASSED                    [ 61%]
phase3/tests/test_api.py::test_get_sentiment_endpoint_known_tickers[INFY.NS] PASSED [ 64%]
phase3/tests/test_api.py::test_get_sentiment_endpoint_known_tickers[RELIANCE.NS] PASSED [ 66%]
phase3/tests/test_api.py::test_get_sentiment_endpoint_known_tickers[TMPV.NS] PASSED [ 69%]
phase3/tests/test_api.py::test_get_financial_endpoint_known_tickers[INFY.NS] PASSED [ 71%]
phase3/tests/test_api.py::test_get_financial_endpoint_known_tickers[RELIANCE.NS] PASSED [ 74%]
phase3/tests/test_api.py::test_get_financial_endpoint_known_tickers[TMPV.NS] PASSED [ 76%]
phase3/tests/test_api.py::test_get_financial_endpoint_invalid_ticker_returns_502 PASSED [ 79%]
phase3/tests/test_financial_agent.py::test_analyze_financial_returns_sane_output_infy PASSED [ 82%]
phase3/tests/test_financial_agent.py::test_analyze_financial_returns_sane_output_reliance PASSED [ 84%]
phase3/tests/test_financial_agent.py::test_analyze_financial_returns_sane_output_tmpv PASSED [ 87%]
phase3/tests/test_financial_agent.py::test_analyze_financial_catches_bad_ticker_and_does_not_raise PASSED [ 89%]
phase3/tests/test_sentiment_agent.py::test_analyze_sentiment_returns_sane_output[INFY.NS] PASSED [ 92%]
phase3/tests/test_sentiment_agent.py::test_analyze_sentiment_returns_sane_output[RELIANCE.NS] PASSED [ 94%]
phase3/tests/test_sentiment_agent.py::test_analyze_sentiment_returns_sane_output[TMPV.NS] PASSED [ 97%]
phase3/tests/test_sentiment_agent.py::test_analyze_sentiment_catches_search_failure_and_does_not_raise PASSED [100%]

============================== warnings summary ===============================
..\Users\kavya\AppData\Local\Programs\Python\Python312\Lib\site-packages\fastapi\testclient.py:1
  C:\Users\kavya\AppData\Local\Programs\Python\Python312\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
======================= 39 passed, 1 warning in 48.22s ========================
```

## Known limitation carried forward (not a bug)

The `httpx`/`starlette.testclient` deprecation warning is upstream noise, not
a test failure — no action needed unless it becomes a hard error in a future
`fastapi`/`starlette` release.
