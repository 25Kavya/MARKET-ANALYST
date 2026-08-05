# Phase 7 Test Results — Streamlit UI

**Scope**: `phase7/portfolio_store.py`, `phase7/api_client.py`, `phase7/app.py`
**Command**: `python -m pytest phase1/tests phase2/tests phase3/tests phase4/tests phase5/tests phase6/tests phase7/tests -v` (full regression: Phase 1–7 together)
**Result**: ✅ 94 passed, 0 failed, 94.67s (75 prior + 19 new Phase 7)
**Logging**: confirmed `dump.log` grew to 847 lines across the combined run
**Manual browser check**: performed by the user directly against the real running app — confirmed working

## What got built

- `portfolio_store.py` — local JSON persistence for portfolio holdings
  (add/remove by company name or ticker, resolved via Phase 1's
  `resolve_ticker`, deduped by ticker).
- `api_client.py` — `ApiClient`, a thin wrapper around the Phase 6 API
  (`query`, `get_stock`, `portfolio_analyze`, `compare`, `health`). Talks
  HTTP only — the UI never imports agents/graphs directly, per
  `ARCHITECTURE.md`. The backend URL (`MARKET_ANALYST_API_URL`, default
  `http://localhost:8000`) is read fresh at each `ApiClient()` construction,
  not cached at import time, specifically so tests can point it at a
  throwaway test server.
- `app.py` — the Streamlit UI: a free-text query box, a portfolio manager
  (add/remove holdings, "Analyze Portfolio" button), a two-stock compare
  form, and result rendering (verdict + confidence, per-agent tabs for
  technical/sentiment/financial, portfolio roll-up, compare ranking table).

## How this got tested without a real browser (until the final manual check)

Three layers of automated testing, then a manual browser pass:

1. **`portfolio_store.py`** — plain pytest against a temp file path, no
   server needed.
2. **`api_client.py`** — tested against the real Phase 6 FastAPI app via
   `fastapi.testclient.TestClient` (same technique used in every prior
   phase).
3. **`app.py`** — tested with Streamlit's own headless testing framework,
   `streamlit.testing.v1.AppTest`, which actually re-executes the app
   script and simulates real widget interactions (typing into inputs,
   clicking buttons) without a browser. Backed by a **real live FastAPI
   server** started in a background thread (see `conftest.py`) so these
   tests exercise the true end-to-end path: UI interaction → real HTTP →
   real FastAPI → real LangGraph orchestration → real yfinance/DuckDuckGo
   calls.
4. **Manual browser verification** — both servers (`uvicorn phase6.api:app`
   on port 8010, `streamlit run phase7/app.py` on port 8501) were started
   for real, and the user opened `http://localhost:8501` in an actual
   browser and confirmed it works.

## Summary table

| Test | What it proves | Status |
|---|---|---|
| `test_load_portfolio_returns_empty_list_when_file_missing` | fresh install has no holdings | PASSED |
| `test_add_holding_resolves_name_and_persists` | "infosys" → `INFY.NS`, saved to disk | PASSED |
| `test_add_holding_twice_updates_instead_of_duplicating` | re-adding a ticker updates, doesn't duplicate | PASSED |
| `test_add_multiple_holdings` | multiple distinct holdings coexist | PASSED |
| `test_remove_holding_by_ticker` / `_by_name` | removal works via either input form | PASSED |
| `test_add_holding_raises_for_unresolvable_name` | garbage input rejected, not silently stored | PASSED |
| `test_health` / `test_query_single` / `test_get_stock_resolves_company_name` / `test_portfolio_analyze` / `test_compare` | `ApiClient` methods work against the real API | PASSED |
| `test_error_response_raises_api_error` | a 4xx API response raises `ApiError`, not a silent bad result | PASSED |
| `test_app_loads_without_error` | app script runs cleanly with no widgets touched | PASSED |
| `test_query_single_stock_golden_path` | typing "how is infosys doing" + clicking Ask produces a real single-stock result | PASSED |
| `test_query_compare_golden_path` | typing the compare example query produces a real compare result | PASSED |
| `test_query_unknown_shows_error_not_crash` | an unrecognizable query shows an error message, not a crash | PASSED |
| `test_add_holding_then_analyze_portfolio` | filling the add-holding form + Analyze Portfolio produces a real report | PASSED |
| `test_compare_form_golden_path` | the two-box compare form produces a real ranking | PASSED |

## Bugs found and fixed while building this

1. **`st.table()` on a dict with mixed value types crashed PyArrow
   serialization.** The technical indicators dict mixes numbers (`sma20`,
   `rsi14`, ...) with a string (`volume_trend: "increasing"`); passing that
   dict straight to `st.table()` makes Streamlit build a single-column
   DataFrame with mixed Python types, which PyArrow can't convert
   (`Could not convert 'increasing' with type str: tried to convert to
   double`). Streamlit has an internal auto-recovery for this, but it still
   logs a scary traceback. **Fix**: added `_as_table_rows()` in `app.py` to
   stringify every value into a clean two-column (`metric`, `value`) table
   before rendering — applied to both the technical indicators table and the
   financial ratios table.
2. **`ApiClient`'s backend URL was cached at import time**, which would have
   silently broken any test that starts a live test server *after*
   `phase7.api_client` was already imported elsewhere in the same pytest
   session (import caching means the env var read wouldn't re-run). **Fix**:
   moved the `os.getenv("MARKET_ANALYST_API_URL", ...)` call from a
   module-level constant into `ApiClient.__init__`, so it's read fresh every
   time a client is constructed.
3. **Test-script bugs (not app bugs)**, caught while writing the AppTest
   suite: `AppTest`'s `session_state` doesn't support dict-style `.get()` —
   it needs bracket/attribute access (`at.session_state["key"]`). And
   `st.form_submit_button` widgets are addressed via `at.button(...)` in
   `AppTest`, not a separate `form_submit_button` accessor (which doesn't
   exist). Both fixed in the test file itself.

## Raw pytest output (tail)

```
================== 94 passed, 1 warning in 94.67s (0:01:34) ===================
```
(Phase 1–6 test names omitted here for brevity — unchanged from their own
`TEST_RESULTS.md` files, all passing in this same run alongside the 19 new
Phase 7 tests.)

## Not in scope for this phase

Real indicator/price history charts (a line chart over time) aren't
included — Phase 2's technical agent only returns the *latest* snapshot
values (SMA, RSI, etc.), not the full historical time series, so a chart
would currently have nothing to plot beyond a single point per indicator.
Adding that would mean widening the technical agent's return shape, which is
outside this UI-only phase's scope. Indicators are shown as a metrics table
instead, which faithfully matches what the backend actually returns. LLM-
based intent classification (Phase 6) and sentiment scoring (Phase 3) remain
keyword-heuristic-based pending `ANTHROPIC_API_KEY` configuration.
