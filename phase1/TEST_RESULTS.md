# Phase 1 Test Results — Data Layer

**Scope**: `phase1/data/market.py`, `phase1/data/search.py`, `phase1/data/tickers.py`
**Command**: `python -m pytest phase1/tests/test_data_layer.py -v`
**Result**: ✅ 14 passed, 0 failed, 10.13s
**Logging**: confirmed writing to `dump.log` during this run (28 lines for the first run; see `dump.log` at repo root)

## Summary table

| Module | Test | Status |
|---|---|---|
| market.py | `test_get_history_returns_rows_for_known_ticker` — real OHLCV fetch for INFY.NS | PASSED |
| market.py | `test_get_history_raises_for_invalid_ticker` — bad ticker raises `MarketDataError` | PASSED |
| market.py | `test_get_fundamentals_returns_expected_fields` — real fundamentals fetch for INFY.NS | PASSED |
| search.py | `test_search_news_returns_results` — real DuckDuckGo query returns titles/urls | PASSED |
| search.py | `test_search_news_respects_max_results` — result count capped correctly | PASSED |
| tickers.py | `test_resolve_ticker_exact_aliases[tata motors]` → `TATAMOTORS.NS` | PASSED |
| tickers.py | `test_resolve_ticker_exact_aliases[infosys]` → `INFY.NS` | PASSED |
| tickers.py | `test_resolve_ticker_exact_aliases[cupid]` → `CUPID.NS` | PASSED |
| tickers.py | `test_resolve_ticker_exact_aliases[mahindra]` → `M&M.NS` | PASSED |
| tickers.py | `test_resolve_ticker_exact_aliases[reliance]` → `RELIANCE.NS` | PASSED |
| tickers.py | `test_resolve_ticker_passthrough_symbol` — `INFY.NS`/`TCS` pass through correctly | PASSED |
| tickers.py | `test_resolve_ticker_fuzzy_match_typo` — `"infosis"` → `INFY.NS` | PASSED |
| tickers.py | `test_resolve_ticker_raises_for_unknown_name` — gibberish raises `TickerResolutionError` | PASSED |
| tickers.py | `test_resolve_ticker_raises_for_empty_name` — blank input raises `TickerResolutionError` | PASSED |

## Raw pytest output

```
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-9.1.1, pluggy-1.6.0 -- C:\Users\kavya\AppData\Local\Programs\Python\Python312\python.exe
cachedir: .pytest_cache
rootdir: C:\MARKET-ANALYST
configfile: pytest.ini
plugins: anyio-4.14.2
collecting ... collected 14 items

phase1/tests/test_data_layer.py::test_get_history_returns_rows_for_known_ticker PASSED [  7%]
phase1/tests/test_data_layer.py::test_get_history_raises_for_invalid_ticker PASSED [ 14%]
phase1/tests/test_data_layer.py::test_get_fundamentals_returns_expected_fields PASSED [ 21%]
phase1/tests/test_data_layer.py::test_search_news_returns_results PASSED        [ 28%]
phase1/tests/test_data_layer.py::test_search_news_respects_max_results PASSED   [ 35%]
phase1/tests/test_data_layer.py::test_resolve_ticker_exact_aliases[tata motors-TATAMOTORS.NS] PASSED [ 42%]
phase1/tests/test_data_layer.py::test_resolve_ticker_exact_aliases[infosys-INFY.NS] PASSED [ 50%]
phase1/tests/test_data_layer.py::test_resolve_ticker_exact_aliases[cupid-CUPID.NS] PASSED [ 57%]
phase1/tests/test_data_layer.py::test_resolve_ticker_exact_aliases[mahindra-M&M.NS] PASSED [ 64%]
phase1/tests/test_data_layer.py::test_resolve_ticker_exact_aliases[reliance-RELIANCE.NS] PASSED [ 71%]
phase1/tests/test_data_layer.py::test_resolve_ticker_passthrough_symbol PASSED  [ 78%]
phase1/tests/test_data_layer.py::test_resolve_ticker_fuzzy_match_typo PASSED    [ 85%]
phase1/tests/test_data_layer.py::test_resolve_ticker_raises_for_unknown_name PASSED [ 92%]
phase1/tests/test_data_layer.py::test_resolve_ticker_raises_for_empty_name PASSED [100%]

============================= 14 passed in 11.64s =============================
```

Re-verified after moving Phase 1 into its own `phase1/` folder — all 14 tests
still pass and `dump.log` still populates correctly from the new location.

## Issue found & fixed during this run

`phase1/logging_config.py` (originally `backend/logging_config.py` before the
Phase 1 files were moved into `phase1/`) called `logging.basicConfig(...)` to attach
the console + `dump.log` handlers. Under `pytest`, the test runner attaches its
own handler to the root logger before test modules are imported, which makes
`logging.basicConfig()` a silent no-op (by design, it only configures the root
logger if it has no handlers yet) — `dump.log` stayed empty on the first run.

**Fix**: configure a dedicated `market_analyst` logger (with `propagate=False`)
and attach the stream + file handlers directly to it instead of relying on root
logger auto-configuration. Verified on the next run: `dump.log` populated with
28 lines covering every data-layer call (request, result, timing, warnings).
