# Phase 9 Test Results — MCP-backed LLM Intent Classification

**Scope**: `phase9/mcp_server.py`, `phase9/mcp_client.py`, `phase9/cache_key.py`,
`phase9/cache_store.py`, `phase9/groq_client.py`, plus the integration point in
`phase6/intent.py` (`classify_mode_via_mcp` replacing the old pure-heuristic
classifier as the primary path, with the heuristic kept as a fallback).

Phase 9 is not listed in `PHASES.md` (which stops at Phase 8, "the final
phase") — this doc records the first time its test suite and live server were
actually verified end-to-end, on 2026-08-01.

**Commands**:
- Mocked-only: `python -m pytest phase9/ -v`
- Live MCP+Groq smoke test: `RUN_LIVE_LLM_TESTS=1 python -m pytest phase6/tests/test_intent.py -v -m live_llm` (requires `phase9/mcp_server.py` running separately and a configured `GROQ_API_KEY`)
- Full regression: `python -m pytest`

**Result**: ✅ 131 passed, 1 skipped by design (99 prior + 15 new Phase 9 +
1 more intent test added alongside Phase 9's integration + the live-only test,
which is skipped in the default run and passes when run explicitly with
`RUN_LIVE_LLM_TESTS=1`).

## What was verified

1. **MCP server actually starts and accepts connections.** Prior to this
   session, `dump.log` showed the server was *not* running — every real query
   hit `mcp_client.classify_mode_via_mcp connection failure ... could not
   reach MCP server` and silently fell back to the old keyword heuristic.
   Started with `python -m phase9.mcp_server` (reads `MCP_SERVER_PORT` from
   `.env`, defaults to 8100) — confirmed listening via a direct HTTP request.
2. **Real end-to-end call through the MCP client**, bypassing all mocks:
   `phase9.mcp_client.classify_mode_via_mcp("how is infosys doing", ["INFY.NS"], False, False)`
   returned a live Groq-generated `{"mode": "single", "reasoning": "..."}"`.
3. **Real end-to-end call through the actual integration point**,
   `phase6.intent.classify_intent`, for all three query shapes:
   - `"compare mahindra and reliance"` → `mode=compare`, `tickers=["M&M.NS", "RELIANCE.NS"]`
   - `"how is my portfolio doing"` → `mode=portfolio`
   - `"how is infosys doing"` → `mode=single`, `tickers=["INFY.NS"]`
   No fallback-to-heuristic warnings appeared for any of these — confirming
   the MCP path is what actually answered, not the safety-net heuristic.
4. **SQLite response cache confirmed live**, not just unit-tested: repeat
   queries logged `cache_store hit` (no new Groq call), novel queries logged
   `cache_store miss` → `groq_client.call_groq` → `cache_store set`. Cache
   persists across server restarts (`data/market_analyst.db`).
5. **Server-side logging lands in the shared `dump.log`** (not just console),
   confirmed by grepping for `phase9.groq_client`/`phase9.cache_store` entries
   with real timestamps from this session.
6. **Full regression suite** (`python -m pytest`, all phases 1–9): 131 passed,
   1 skipped, 56.23s — no regressions introduced by having the live MCP server
   running during the test run.
7. **Fallback safety net re-confirmed**: `test_mcp_unavailable_falls_back_to_heuristic`
   (mocked) still passes, and the earlier `dump.log` entries from before the
   server was started are direct evidence the fallback works for real, not
   just under a mock.

## Summary table

| Test | What it proves | Status |
|---|---|---|
| `test_normalize_collapses_case_whitespace_and_punctuation` | cache key normalization ignores trivial text differences | PASSED |
| `test_cache_key_same_for_trivial_rephrasing` | near-identical queries hash to the same cache key | PASSED |
| `test_cache_key_differs_for_genuinely_different_phrasing` | meaningfully different queries get different keys | PASSED |
| `test_cache_key_differs_by_tool_name` | key namespace is per-tool | PASSED |
| `test_cache_key_differs_by_prompt_version` | bumping `PROMPT_VERSION` invalidates old cache entries | PASSED |
| `test_cache_miss_returns_none` | empty cache returns `None`, not an error | PASSED |
| `test_cache_set_then_get_hit` | write-then-read round-trips correctly | PASSED |
| `test_cache_distinguishes_tool_name` | no cross-tool key collisions | PASSED |
| `test_cache_set_overwrites_existing_key` | re-caching a key replaces the old value | PASSED |
| `test_cache_never_stores_failures` | a failed classification is never persisted as a cached "answer" | PASSED |
| `test_cache_concurrent_writes_and_reads_do_not_crash` | SQLite WAL + busy-timeout + retry survive concurrent access | PASSED |
| `test_cache_miss_calls_groq_once_and_caches` | cold path: Groq called exactly once, result cached | PASSED |
| `test_cache_hit_never_calls_groq` | warm path: second identical call never touches Groq | PASSED |
| `test_groq_error_propagates_and_is_not_cached` | a Groq failure raises and leaves no cache entry behind | PASSED |
| `test_invalid_mode_from_groq_raises_and_is_not_cached` | a malformed `mode` from the LLM is rejected, not silently accepted | PASSED |
| `test_mcp_unavailable_falls_back_to_heuristic` (phase6) | connection failure degrades to the old rule-based classifier instead of raising | PASSED |
| `test_classify_intent_live_mcp_and_groq` (phase6, live-only) | real, unmocked round trip: `intent.classify_intent` → MCP server → Groq → correct mode+tickers | PASSED (run explicitly) |

## Raw pytest output (tail, full regression)

```
phase6\tests\test_api.py ............                                    [ 57%]
phase6\tests\test_intent.py ........s                                    [ 64%]
phase7\tests\test_api_client.py ......                                   [ 68%]
phase7\tests\test_app.py ......                                          [ 73%]
phase7\tests\test_portfolio_store.py .......                             [ 78%]
phase8\tests\test_cache.py ......                                        [ 83%]
phase8\tests\test_logging_hardening.py .                                 [ 84%]
phase8\tests\test_market_hardening.py .....                              [ 87%]
phase8\tests\test_partial_failure_regression.py .                        [ 88%]
phase9\tests\test_cache_key.py .....                                     [ 92%]
phase9\tests\test_cache_store.py ......                                  [ 96%]
phase9\tests\test_mcp_server.py ....                                     [100%]

======================= 131 passed, 1 skipped in 56.23s =======================
```

Live-only test run separately:
```
phase6/tests/test_intent.py::test_classify_intent_live_mcp_and_groq PASSED [100%]
======================= 1 passed, 8 deselected in 1.18s =======================
```

## Operational note — this is not automatic yet

Unlike `phase6/api.py`'s FastAPI app or `phase7/app.py`'s Streamlit app, there
is no process supervisor or startup script that launches
`phase9/mcp_server.py` alongside the rest of the stack. It must be started
manually:

```
python -m phase9.mcp_server
```

If it isn't running, `phase6/intent.py` degrades gracefully to the old
keyword heuristic (by design, per `McpUnavailableError` handling) — the
system still answers, just without the LLM's judgment on nuanced/implicit
phrasing. This is safe but easy to miss silently; worth a `dump.log` check
(`grep "mcp unavailable" dump.log`) if intent classification seems off.

## Not in scope for this test session

- Adding `phase9/mcp_server.py` to a startup script / process supervisor so
  it starts automatically — flagged above as an operational gap, not fixed.
- Updating `PHASES.md` to document Phase 9 as a real phase (it currently
  isn't mentioned there at all) — left to the project owner to decide how it
  should be framed relative to the "Phase 8 is final" narrative.
