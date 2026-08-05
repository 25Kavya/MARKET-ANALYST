# Phase 5 Test Results — Multi-Ticker Flows (Portfolio + Compare)

**Scope**: `phase5/state.py`, `phase5/nodes.py`, `phase5/graph.py`
**Command**: `python -m pytest phase1/tests phase2/tests phase3/tests phase4/tests phase5/tests -v` (full regression: Phase 1–5 together)
**Result**: ✅ 51 passed, 0 failed, 59.21s (46 prior + 5 new Phase 5)
**Logging**: confirmed `dump.log` grew to 350 lines across the combined run

## What got built

`phase5/graph.py` extends Phase 4's single-ticker graph to N tickers. It
fans out via `Send` to a `ticker_node` per ticker; each `ticker_node` calls
Phase 4's `analyze_ticker()`, which internally fans out to its own 3 agents.
Because LangGraph runs independent branches concurrently regardless of
nesting depth, this gives **two layers of parallelism**: N tickers at once,
each running its 3 agents at once — not N separate sequential single-ticker
runs.

- `state.py` — `MultiTickerState` adds `tickers`, `mode`
  (`"portfolio"`/`"compare"`), and a list-reducer `ticker_syntheses` field.
- `nodes.py` — `ticker_node` wraps `phase4.graph.analyze_ticker`;
  `portfolio_aggregator` rolls up overall verdict, best/worst performer
  (by a confidence-weighted directional score), and risk flags (tickers with
  fewer than 3 contributing agents or any failure notes); `compare_aggregator`
  ranks tickers by the same score and picks a winner with a rationale.
- `graph.py` — `analyze_portfolio(tickers)` and `compare_tickers(tickers)`
  are the two public entry points, both built on the same dispatch pattern.

## Summary table

| Test | What it proves | Status |
|---|---|---|
| `test_dispatch_tickers_returns_one_send_per_ticker` | fan-out targets `ticker_node` once per ticker with the right payload | PASSED |
| `test_analyze_portfolio_real_tickers` | full 3-stock portfolio run end-to-end produces a valid roll-up | PASSED |
| `test_compare_tickers_real` | full 2-stock compare run produces a ranked table + winner + rationale | PASSED |
| `test_portfolio_handles_one_bad_ticker_without_crashing` | one delisted/fake ticker gets flagged as a risk, doesn't crash the other ticker's report | PASSED |
| `test_tickers_run_concurrently_not_ticker_by_ticker` | 3 tickers x 3 mocked 0.4s agents finish in <0.8s total (would be ~1.2s if processed ticker-by-ticker) | PASSED |

## Real-run evidence of two-layer parallelism (manual spot-check before writing tests)

Portfolio run for `["INFY.NS", "RELIANCE.NS", "TMPV.NS"]` — all 9 individual
agent calls (3 tickers x 3 agents) started within ~35ms of each other:

```
19:15:12,923 ticker_node start ticker=INFY.NS
19:15:12,923 ticker_node start ticker=RELIANCE.NS
19:15:12,927 ticker_node start ticker=TMPV.NS
19:15:12,934 nodes.technical_node start ticker=INFY.NS
19:15:12,934 nodes.sentiment_node  start ticker=INFY.NS
19:15:12,951 nodes.technical_node start ticker=RELIANCE.NS
19:15:12,951 nodes.sentiment_node  start ticker=RELIANCE.NS
19:15:12,951 nodes.financial_node start ticker=RELIANCE.NS
19:15:12,951 nodes.financial_node start ticker=INFY.NS
19:15:12,951 nodes.technical_node start ticker=TMPV.NS
19:15:12,955 nodes.sentiment_node  start ticker=TMPV.NS
19:15:12,955 nodes.financial_node start ticker=TMPV.NS
...
19:15:17,830 aggregator ok mode=portfolio tickers=[...]
```

Total wall time ≈ 4.92s, matching only the single slowest call across all 9
(INFY's sentiment search at 4.86s) — not the sum of all 9 (which would be
well over 15s). This is the concrete evidence that tickers are not processed
one-at-a-time.

## A real (non-)bug worth noting

In that same real run, `best_performer` and `worst_performer` both came back
as `"INFY.NS"`. This is **not a bug** — all 3 stocks scored identically
(bullish, 0.67) in that market snapshot, and `max()`/`min()` over tied values
both return the first key encountered. Tests intentionally assert
`best_performer`/`worst_performer` are valid tickers from the input list,
not that they differ, since a genuine tie is a legitimate outcome.

## Raw pytest output (Phase 5 section)

```
phase5/tests/test_multi_ticker.py::test_dispatch_tickers_returns_one_send_per_ticker PASSED [ 92%]
phase5/tests/test_multi_ticker.py::test_analyze_portfolio_real_tickers PASSED [ 94%]
phase5/tests/test_multi_ticker.py::test_compare_tickers_real PASSED      [ 96%]
phase5/tests/test_multi_ticker.py::test_portfolio_handles_one_bad_ticker_without_crashing PASSED [ 98%]
phase5/tests/test_multi_ticker.py::test_tickers_run_concurrently_not_ticker_by_ticker PASSED [100%]

======================= 51 passed, 1 warning in 59.21s ========================
```
(Full Phase 1–4 test names omitted here for brevity — see each phase's own
`TEST_RESULTS.md`; all 46 prior tests passed unchanged in this same run.)

## Not in scope for this phase

Real FastAPI endpoints (`/query`, `/portfolio/analyze`, `/compare`) and
intent classification are Phase 6 — this phase only proves the multi-ticker
orchestration logic works when called directly with an explicit ticker list.
