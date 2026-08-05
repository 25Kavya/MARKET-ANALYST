# Phase 8 Test Results — Hardening

**Scope**: `phase8/cache.py`, plus hardening changes to `phase1/data/market.py`, `phase1/data/search.py`, `phase1/logging_config.py`
**Command**: `python -m pytest phase1/tests phase2/tests phase3/tests phase4/tests phase5/tests phase6/tests phase7/tests phase8/tests -v` (full regression: all 8 phases together)
**Result**: ✅ 107 passed, 0 failed, 58.81s (94 prior + 13 new Phase 8)
**Regression check before writing new tests**: reran all 94 prior tests after the hardening changes landed — still 94/94 passing, and the suite ran in **42.59s instead of 94.67s**, a direct real-world demonstration of caching cutting redundant work across the test session.

## What got hardened

1. **Caching** (`phase8/cache.py` — generic `ttl_cache` decorator, applied to
   `market.get_history`, `market.get_fundamentals`, and `search.search_news`):
   an in-memory, thread-safe, TTL-based cache keyed by function arguments.
   Failed calls are never cached — a bad ticker or a transient outage always
   re-runs next time rather than being "remembered" as a permanent failure.
   TTLs: 5 minutes for price/fundamentals, 10 minutes for news search
   (matching `ARCHITECTURE.md`'s suggested 5–15 minute range). Verified live:
   a repeated real `get_history("INFY.NS")` call went from 5.67s to
   effectively 0s.
2. **Retry + backoff for `market.py`** (it previously had none, unlike
   `search.py` which already had this): 2 attempts with backoff, but
   **only** around the actual network/API call — not around the "empty
   result" check that fires for a permanently invalid ticker, so a bad
   ticker still fails fast instead of wasting time on retries that could
   never succeed.
3. **Log rotation** (`phase1/logging_config.py`): swapped the plain
   `FileHandler` for a `RotatingFileHandler` (2 MB per file, 3 backups), so
   `dump.log` no longer grows unbounded across long-running sessions.
4. **Re-verified partial-failure tolerance** end-to-end with the new
   caching/retry layer in place — a bad ticker mid-portfolio still degrades
   gracefully instead of failing the whole request.

## Summary table

| Test | What it proves | Status |
|---|---|---|
| `test_ttl_cache_returns_cached_value_within_ttl` | repeated call within TTL doesn't re-run the function | PASSED |
| `test_ttl_cache_distinguishes_different_arguments` | different args → different cache entries | PASSED |
| `test_ttl_cache_expires_after_ttl` | call after TTL expiry re-runs the function | PASSED |
| `test_ttl_cache_does_not_cache_exceptions` | a failed call is never cached as a "result" | PASSED |
| `test_ttl_cache_supports_custom_key_fn` | custom cache-key logic works (e.g. ignore a param) | PASSED |
| `test_ttl_cache_object_get_set_clear` | the underlying `TTLCache` object's API works standalone | PASSED |
| `test_dump_log_uses_a_rotating_file_handler` | `dump.log` handler is a `RotatingFileHandler` with the configured size/backup count | PASSED |
| `test_get_history_retries_transient_error_then_succeeds` | a simulated network error on attempt 1 recovers on attempt 2 | PASSED |
| `test_get_history_raises_after_exhausting_retries` | a persistent failure raises `MarketDataError` after `_MAX_RETRIES` attempts | PASSED |
| `test_get_history_does_not_retry_permanently_invalid_ticker` | an empty-result (invalid ticker) response is NOT retried — fails fast | PASSED |
| `test_get_history_caches_repeated_calls` | second identical call doesn't hit the (mocked) network layer at all | PASSED |
| `test_get_history_cache_key_distinguishes_period` | different `period` argument correctly bypasses the cache | PASSED |
| `test_bad_ticker_mid_portfolio_still_returns_full_report_with_hardening_in_place` | Phase 8's required check: bad ticker in a 3-stock portfolio still returns a full report with clear per-agent error notes for the failed ticker, with caching/retry now in the path | PASSED |

## Raw pytest output (tail)

```
phase8/tests/test_cache.py::test_ttl_cache_returns_cached_value_within_ttl PASSED [ 88%]
phase8/tests/test_cache.py::test_ttl_cache_distinguishes_different_arguments PASSED [ 89%]
phase8/tests/test_cache.py::test_ttl_cache_expires_after_ttl PASSED      [ 90%]
phase8/tests/test_cache.py::test_ttl_cache_does_not_cache_exceptions PASSED [ 91%]
phase8/tests/test_cache.py::test_ttl_cache_supports_custom_key_fn PASSED [ 92%]
phase8/tests/test_cache.py::test_ttl_cache_object_get_set_clear PASSED   [ 93%]
phase8/tests/test_logging_hardening.py::test_dump_log_uses_a_rotating_file_handler PASSED [ 94%]
phase8/tests/test_market_hardening.py::test_get_history_retries_transient_error_then_succeeds PASSED [ 95%]
phase8/tests/test_market_hardening.py::test_get_history_raises_after_exhausting_retries PASSED [ 96%]
phase8/tests/test_market_hardening.py::test_get_history_does_not_retry_permanently_invalid_ticker PASSED [ 97%]
phase8/tests/test_market_hardening.py::test_get_history_caches_repeated_calls PASSED [ 98%]
phase8/tests/test_market_hardening.py::test_get_history_cache_key_distinguishes_period PASSED [ 99%]
phase8/tests/test_partial_failure_regression.py::test_bad_ticker_mid_portfolio_still_returns_full_report_with_hardening_in_place PASSED [100%]

======================= 107 passed, 1 warning in 58.81s =======================
```
(Phase 1–7 test names omitted here for brevity — unchanged from their own
`TEST_RESULTS.md` files, all 94 passing in this same run alongside the 13
new Phase 8 tests.)

## A note on the phase1 → phase8 dependency direction

`phase1/data/market.py` and `phase1/data/search.py` import
`phase8.cache.ttl_cache`, so an earlier phase's module now depends on a
later phase's module. This is intentional: caching only has real effect if
it wraps the actual call sites every other phase already uses, and
`phase8/cache.py` itself has no dependency back on `phase1.data.*` (only on
`phase1.logging_config`, which has no dependencies of its own), so there is
no import cycle — just an unusual-looking but valid dependency direction.
This mirrors the precedent set in Phase 6, which also modified Phase 1's
`tickers.py` to add functionality a later phase needed.

## Not in scope for this phase

Redis or any external cache store — the in-memory `TTLCache` is sufficient
at this project's scale, per `ARCHITECTURE.md`'s explicit guidance ("Redis
only if you outgrow it"). Distinguishing exception *types* more precisely
for retry (e.g. only retrying on `requests.exceptions.ConnectionError`
specifically rather than any `Exception`) was considered but skipped, since
yfinance doesn't expose a clean, stable exception hierarchy to key off of —
the existing bare `except Exception` (already used by `search.py`) was kept
for consistency.
