# Phase 6 Test Results — Full FastAPI Surface

**Scope**: `phase6/intent.py`, `phase6/api.py` (plus two supporting fixes to `phase1/data/tickers.py`)
**Command**: `python -m pytest phase1/tests phase2/tests phase3/tests phase4/tests phase5/tests phase6/tests -v` (full regression: Phase 1–6 together)
**Result**: ✅ 75 passed, 0 failed, 81.51s (52 prior + 23 new Phase 6, on a clean rerun)
**Logging**: confirmed `dump.log` grew to 574 lines across the combined run

## What got built

`phase6/intent.py` — `classify_intent(query)` turns a free-text question into
`{mode, tickers}`. Like Phase 3's sentiment scoring, this uses keyword rules
rather than an LLM call, since no `ANTHROPIC_API_KEY` is configured yet:
- `"compare"`/`" vs "`/`" versus "` + 2+ recognized tickers → `compare`
- `"portfolio"`/`"my stocks"`/`"holdings"` keywords, or 2+ tickers mentioned
  without a compare keyword → `portfolio`
- exactly 1 ticker mentioned → `single`
- no ticker recognized → `unknown` (API returns 400)

`phase6/api.py` — the real, permanent endpoints from `ARCHITECTURE.md`:
`GET /health`, `GET /stock/{ticker}`, `POST /portfolio/analyze`,
`POST /compare`, `POST /query`. All ticker/company-name input goes through
Phase 1's `resolve_ticker`, so callers can pass either a company name
("infosys") or a raw symbol ("INFY.NS").

## Two supporting fixes to phase1/data/tickers.py

Building this phase surfaced two real gaps in the ticker resolver, both
fixed with tests added to `phase1/tests/test_data_layer.py` (20/20 passing,
up from 14):

1. **New `find_mentioned_tickers(text)`** — scans free text for known company
   aliases and returns resolved tickers in order of first appearance,
   handling overlapping substrings correctly (e.g. "tata motors" isn't
   shadowed by a shorter unrelated alias). This is what `classify_intent`
   uses to extract tickers from a query.
2. **Fixed `resolve_ticker` passthrough** — previously, a raw ticker symbol
   not already in our ~20-company curated table (e.g. `"HCLTECH"`) was
   incorrectly rejected, because passthrough only worked if the symbol
   happened to also be a *key* in our internal dictionary. Needed for
   `GET /stock/{ticker}` to accept any valid NSE symbol, not just our demo
   set. Fixed by reordering priority: exact alias match → already-qualified
   `.NS` passthrough (unambiguous) → fuzzy-match typo correction against
   known companies → bare ticker-shaped fallback → error. The reorder was
   necessary because a naive "accept anything ticker-shaped" fix broke the
   existing typo-correction test (`"infosis"` was being passed through
   literally as `"INFOSIS.NS"` instead of being corrected to `INFY.NS`) —
   caught immediately by the existing test suite before it shipped.

## Summary table

| Test | What it proves | Status |
|---|---|---|
| `test_classify_intent_portfolio_query` | original example query 1 → `portfolio`, 3 tickers | PASSED |
| `test_classify_intent_single_query` | original example query 2 → `single`, 1 ticker | PASSED |
| `test_classify_intent_compare_query` | original example query 3 → `compare`, 2 tickers | PASSED |
| `test_classify_intent_unknown_query_no_ticker_mentioned` | no recognizable stock → `unknown` | PASSED |
| `test_classify_intent_portfolio_via_multiple_tickers_without_keyword` | 3 tickers, no keyword → portfolio fallback | PASSED |
| `test_classify_intent_compare_keyword_with_only_one_ticker_falls_back_to_single` | "compare" keyword but only 1 ticker → single | PASSED |
| `test_health_endpoint` | `GET /health` | PASSED |
| `test_get_stock_endpoint_resolves_company_name` | `GET /stock/infosys` resolves + returns full synthesis | PASSED |
| `test_get_stock_endpoint_accepts_raw_ticker` | `GET /stock/RELIANCE.NS` | PASSED |
| `test_get_stock_endpoint_invalid_name_returns_400` | unresolvable input → 400, not a crash | PASSED |
| `test_post_portfolio_analyze_with_company_names` | `POST /portfolio/analyze` with names, not raw symbols | PASSED |
| `test_post_portfolio_analyze_empty_list_returns_400` | empty list rejected | PASSED |
| `test_post_compare_with_company_names` | `POST /compare` with names | PASSED |
| `test_post_compare_single_ticker_returns_400` | compare needs 2+ tickers | PASSED |
| `test_post_query_end_to_end[single/compare]` | full `/query` → intent → correct downstream flow | PASSED |
| `test_post_query_portfolio_end_to_end` | full `/query` portfolio flow | PASSED |
| `test_post_query_unknown_returns_400` | unrecognizable query rejected cleanly | PASSED |

## A transient infrastructure issue during testing (not a code bug)

The first full run of this regression suite took **1 hour 52 minutes**
instead of the usual ~80 seconds, and one test
(`test_get_sentiment_endpoint_known_tickers[INFY.NS]`) failed with a 502.
The logs showed a real DNS/network outage on the machine — DuckDuckGo search
requests failed with `getaddrinfo failed` / `no connections available`, and
one retry gap alone was over 90 minutes. This is exactly the kind of
external failure the Phase 3 "catch, don't raise" design exists for — the
system reported the failure cleanly via a 502 instead of hanging or
crashing the whole suite. Re-ran the single failed test once network
connectivity recovered (3.29s, passed), then reran the full suite cleanly
(81.51s, all 75 passed). No code change was needed.

## Raw pytest output (clean rerun)

```
================== 75 passed, 1 warning in 81.51s (0:01:21) ===================
```
(Phase 1–5 test names omitted here for brevity — unchanged from their own
`TEST_RESULTS.md` files, all passing in this same run alongside the new
Phase 1 additions and Phase 6 tests.)

## Not in scope for this phase

Real LLM-based intent classification (swapping the keyword heuristic for a
Claude call) is deferred until `ANTHROPIC_API_KEY` is configured — the
`classify_intent` function's interface (`{mode, tickers}` in, same shape
out) is designed so that swap won't require changing `api.py`. The Streamlit
UI is Phase 7.
