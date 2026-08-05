# Build Phases

Each phase ends only when its own tests pass (per `RULES.md` — test after
every addition, log via `dump.log`, secrets via `.env`). Don't start a phase
until the previous one is green.

## Phase 0 — Scaffolding
- Repo structure per `ARCHITECTURE.md` §5, `requirements.txt`, `.env` (from
  `.env.example`), `backend/logging_config.py` (console + `dump.log`
  handlers), empty FastAPI app with `/health`, empty Streamlit app that pings
  it.
- **Test**: `pytest` runs (even with 0 real tests, harness works), `GET
  /health` returns 200, Streamlit loads and shows backend status.

## Phase 1 — Data layer
- `data/market.py` (yfinance: history + fundamentals), `data/search.py`
  (DuckDuckGo wrapper with retry/backoff), `data/tickers.py` (company name →
  NSE symbol, e.g. "infosys" → `INFY.NS`).
- **Test**: standalone script/pytest hitting real APIs — fetch INFY.NS OHLCV,
  fetch its fundamentals, resolve 5–10 known company names, run one
  DuckDuckGo search and confirm results come back. Confirm calls are landing
  in `dump.log`.
- **Status**: ✅ done — 14/14 tests passed, see `TEST_RESULTS.md`.

### Phase 1 in plain terms

Before we can build the "AI analyst" part, the system needs a reliable way to
*fetch raw data* about stocks. That's all Phase 1 is — no AI, no predictions
yet, just plumbing to pull information from the internet. Three small tools
were built:

1. **A stock-price fetcher** (`market.py`) — connects to Yahoo Finance (via a
   library called `yfinance`) and pulls two things for any stock: its recent
   price history (daily open/high/low/close/volume) and its "fundamentals"
   (P/E ratio, market cap, profit margins, etc. — the numbers a financial
   analyst would look at).
2. **A news fetcher** (`search.py`) — connects to DuckDuckGo (free web
   search, no account/API key needed) and pulls recent news headlines about a
   company. This is what will later feed the "sentiment analyst" agent — is
   the news about this company good or bad?
3. **A name-to-symbol translator** (`tickers.py`) — you and I type "Infosys"
   or "Mahindra", but the stock market only understands codes like
   `INFY.NS` or `M&M.NS`. This little dictionary + fuzzy-matching (so even a
   typo like "infosis" still works) converts what a human types into the
   code the other two tools need.

All three were tested using real live data (real prices, real news), not
fake/pretend data — 14 checks total, covering both the "happy path" (does it
work for a real stock) and the "does it fail safely" path (what happens if
you give it a fake ticker or a gibberish company name). All 14 passed.

One real bug was found and fixed along the way: a logging system meant to
write everything the tools do into `dump.log` (so later, if something goes
wrong, we can look back and see exactly what was requested and what came
back) came out completely empty on the first test run — silently broken by a
conflict with the testing tool itself. This was diagnosed, fixed, and
re-verified so the log file now fills up correctly. Documented in
`TEST_RESULTS.md`.

Bottom line: we now have working, tested "hands" that can reach out and grab
stock prices, company financials, and news for any Indian stock. Next phase
builds the first actual "brain" — the Technical Analyst agent — that uses
this price data to say something like "this stock looks bullish/bearish."

## Phase 2 — Walking skeleton (one agent, end-to-end)
- Build only the **Technical Analyst** agent (`graph/agents/technical.py`)
  using Phase 1's data layer. Wire it directly to a temporary
  `GET /stock/{ticker}/technical` FastAPI route — no LangGraph yet.
- Goal: prove the full path (UI → API → agent → data source → response)
  works before adding orchestration complexity.
- **Test**: call the route for 2–3 tickers via Swagger/`curl`, verify
  indicator output looks sane, verify Streamlit can render it.
- **Status**: ✅ done — code lives in `phase2/` (`agents/technical.py`,
  `api.py`, `tests/`), 9/9 new tests passed (23/23 with Phase 1 regression),
  see `phase2/TEST_RESULTS.md`. Streamlit check deferred to Phase 7 (UI
  doesn't exist yet). Along the way, found and fixed a real data issue: the
  Phase 1 ticker table pointed "tata motors" at `TATAMOTORS.NS`, which is now
  delisted following Tata Motors' 2025 demerger — repointed to `TMPV.NS`.

## Phase 3 — Remaining agents
- Build **Sentiment Analyst** and **Financial Analyst** the same way as
  Phase 2: standalone function, temporary direct route, tested independently.
- **Test**: each agent tested alone against 2–3 tickers, including one
  failure case (bad ticker) to confirm errors are caught and logged, not
  raised.
- **Status**: ✅ done — code lives in `phase3/` (`agents/sentiment.py`,
  `agents/financial.py`, `api.py`, `tests/`), 16/16 new tests passed (39/39
  with Phase 1+2 regression), see `phase3/TEST_RESULTS.md`. Sentiment scoring
  uses a keyword heuristic rather than an LLM call, since no
  `ANTHROPIC_API_KEY` is configured yet — swappable later without changing
  the agent's interface. Both agents catch their own data-source failures and
  return `status: "error"` instead of raising, per this phase's test
  requirement.

### Phase 3 in plain terms

Where we are so far: Phase 1 built the "hands" (fetch prices, fetch news).
Phase 2 built the first "brain" — an analyst that only looks at price charts
(technical analysis). Phase 3 builds the other two brains the system needs.

**1. The Sentiment Analyst** — this one reads the news. It goes out, grabs a
handful of recent headlines about the company (using the news-fetcher from
Phase 1), and then figures out if the news sounds good or bad. Since a paid
AI (Claude) isn't hooked up yet, it doesn't use AI to read the headlines —
instead it uses a simple "good words / bad words" checklist (words like
"surge," "profit," "record high" count as good; words like "loss,"
"downgrade," "lawsuit" count as bad). It counts how many good vs bad words
show up across the headlines and turns that into a verdict: is the news mood
currently positive, negative, or mixed. Think of it like a basic mood-ring
for news, not a deep reader — a placeholder that can be upgraded to a real AI
reader later without changing how the rest of the system talks to it.

**2. The Financial Analyst** — this one ignores price charts and news
entirely, and instead looks at the company's actual business health: is it
profitable, is it growing, is it in a lot of debt. It checks three things:
- **Profit margin** — how much of every rupee of sales actually becomes profit
- **Revenue growth** — is the business growing or shrinking
- **Debt levels** — is the company loaded with debt or financially conservative

Each of those three votes "good/bad/okay," and the majority decides the
overall verdict — same voting idea as the Technical Analyst from Phase 2,
just applied to different numbers.

**A design rule applied to both**: if either agent hits a problem (e.g., a
stock that doesn't exist, or the news search temporarily fails), it doesn't
crash — it quietly reports "something went wrong here" and hands back an
error note instead of blowing up. This matters because in the next phase,
all these agents will run at the same time for every stock in a portfolio —
one bad stock symbol shouldn't bring down the whole report for everything
else.

Testing: both agents were run against real stocks (Infosys, Reliance, Tata
Motors' successor) and confirmed to give sensible output, plus deliberately
broken (a fake search failure, a fake stock ticker) to confirm they fail
quietly instead of crashing. All 16 new checks passed, bringing the running
total across all 3 phases to 39/39 passing.

Bottom line: all three specialist opinions now work independently —
technical (chart-based), sentiment (news-based), and financial
(fundamentals-based). Phase 4 is where these three get made to run together,
at the same time, for the same stock, and their opinions get combined into
one final answer.

## Phase 4 — LangGraph orchestration (single ticker)
- Define `GraphState`/`TickerResult` schemas (`graph/state.py`). Build
  `dispatch` node using `Send` to fan out to the 3 existing agents in
  parallel, and `per_ticker_synthesizer` to combine their output for one
  ticker. Remove the Phase 2/3 temporary direct routes once the graph
  replaces them.
- **Test**: compiled graph invoked for a single ticker; confirm all 3 agents
  actually ran concurrently (check timestamps in `dump.log`), confirm
  synthesis output has a verdict + confidence + reasoning.
- **Status**: ✅ done — code lives in `phase4/` (`state.py`, `nodes.py`,
  `graph.py`, `tests/`), 7/7 new tests passed (46/46 with Phase 1–3
  regression), see `phase4/TEST_RESULTS.md`. Concurrency verified two ways:
  a real run's `dump.log` timestamps (all 3 agents started within ~13ms of
  each other) and a mocked-delay test (3×0.5s agents finish in <1s total,
  not ~1.5s). `technical_node` normalizes Phase 2's raised
  `MarketDataError` into the same `status: "ok"/"error"` shape Phase 3's
  agents already return, so the synthesizer treats all three uniformly and
  degrades gracefully when one or more agents fail.

### Phase 4 in plain terms

Phases 1–3 built three independent specialist opinions. Phase 4 is where
they actually get run together and combined into one answer — the "master
node" idea from the original request.

**What changed**: instead of calling one analyst at a time and waiting for
each to finish before starting the next, the system now fires all three at
once — like asking three different people the same question over three
phone calls placed simultaneously instead of one after another — and only
moves on once all three have answered. This matters because the slowest step
(searching the web for news) previously would have made everything wait in
line behind it; now it just happens alongside the others, so the total wait
time is however long the *slowest* analyst takes, not the *sum* of all
three.

**How it was proven to actually be parallel** (not just claimed): first, by
watching the real timestamps in the log file — all three analysts logged
"starting now" within about a hundredth of a second of each other, and the
total time taken matched only the slowest one, not the sum of all three.
Second, with a controlled test: three fake analysts were told to each take
exactly half a second, and the whole thing finished in under a second total
— proof they ran side-by-side rather than one after another (which would
have taken closer to a second and a half).

**Handling a bad stock symbol gracefully**: when tested with a fake ticker,
two of the three analysts (technical, financial) correctly said "I couldn't
get data for this," while the news-based analyst still returned an opinion
(since news search doesn't check if a ticker is real). The system didn't
crash — it combined whatever did come back, and clearly noted what failed
and why. This is exactly the safety net the architecture called for: one
broken data source for one stock shouldn't take down an entire portfolio
report.

Bottom line: the three analysts now run as a team instead of one at a time,
and the combined "master" verdict comes back as fast as the slowest member
of the team, with the whole thing tested and confirmed working for real
stocks. Next phase extends this same team-based approach to handle multiple
stocks at once (a full portfolio, or a head-to-head comparison).

## Phase 5 — Multi-ticker flows
- Add `final_aggregator` logic for `portfolio` (roll-up: overall health,
  best/worst performer, risk flags) and `compare` (side-by-side table +
  winner rationale).
- **Test**: run the graph with a 3-stock portfolio and a 2-stock compare,
  confirm per-ticker parallelism still holds across tickers too (N tickers ×
  3 agents all firing concurrently, not ticker-by-ticker).
- **Status**: ✅ done — code lives in `phase5/` (`state.py`, `nodes.py`,
  `graph.py`, `tests/`), 5/5 new tests passed (51/51 with Phase 1–4
  regression), see `phase5/TEST_RESULTS.md`. Two-layer concurrency verified:
  a real 3-stock portfolio run showed all 9 agent calls (3 tickers × 3
  agents) starting within ~35ms of each other, and a mocked-delay test
  proved 3 tickers don't get processed one-at-a-time (would take ~3x longer
  if they did).

### Phase 5 in plain terms

Phase 4 got three analysts working as a team for one stock at a time. Phase
5 makes that same team approach work across a whole list of stocks
simultaneously — a portfolio, or a head-to-head comparison — which is
exactly what the original two use cases from the very first ask needed
("how's my portfolio doing" and "compare X and Y").

**What changed**: instead of running the 3-analyst team for stock A, waiting
for it to finish, then running the team again for stock B, and so on, the
system now kicks off the entire 3-analyst team for *every* stock in the list
at the same time. So checking a 3-stock portfolio takes roughly the same
amount of time as checking a single stock — not three times as long. This
was proven two ways: a real run against 3 real stocks showed all 9
individual analyst calls (3 stocks × 3 analysts each) starting within about
35 thousandths of a second of each other; and a controlled test with fake
analysts confirmed 3 stocks finished in under a second combined, instead of
the ~1.2 seconds it would take if stocks were handled one at a time.

**Portfolio mode** looks at all the stocks together and produces one
combined picture: an overall health verdict, which stock is doing best,
which is doing worst, and a list of any stocks flagged as "risky" (e.g. a
stock where one of the three analysts couldn't get any data — a sign the
opinion on that stock is less reliable than the others).

**Compare mode** takes two (or more) stocks and directly ranks them against
each other, picking a "winner" and explaining why in plain language — this
answers a question like "compare Mahindra and Reliance" directly.

**Handling a broken stock inside a portfolio**: tested by mixing one real
stock with one fake one. The fake one correctly got flagged in the risk list
(because two of its three analysts couldn't find any data for it), but the
rest of the portfolio's report still came back complete and usable — one bad
entry didn't spoil the whole report.

Bottom line: the system can now genuinely answer all three original example
questions — single stock, portfolio, and comparison — with the multi-agent
approach running efficiently in parallel at every level. All 51 checks
across every phase built so far are passing. Next phase connects this to
real, permanent API addresses and adds a step that reads a plain-English
question (like "how's my portfolio doing") and automatically figures out
which of these three modes to run and which stocks are involved.

## Phase 6 — Full FastAPI surface
- Add `intent_router` node (LLM classifies `single | portfolio | compare` +
  resolves tickers). Wire up the real endpoints: `POST /query`,
  `POST /portfolio/analyze`, `POST /compare`, `GET /stock/{ticker}`.
- **Test**: hit `/query` with the 3 example queries from the original ask
  ("how's my portfolio doing", "how is infosys doing", "compare mahindra and
  reliance") and confirm correct intent + tickers + routing each time.
- **Status**: ✅ done — code lives in `phase6/` (`intent.py`, `api.py`,
  `tests/`), 23/23 new tests passed (75/75 with Phase 1–5 regression), see
  `phase6/TEST_RESULTS.md`. Intent classification uses keyword rules rather
  than an LLM call, since no `ANTHROPIC_API_KEY` is configured yet — same
  approach as Phase 3's sentiment scoring, swappable later without changing
  `api.py`. All 3 original example queries route correctly. Along the way,
  fixed two real gaps in Phase 1's `resolve_ticker` (added
  `find_mentioned_tickers()`, and fixed raw-symbol passthrough that was
  incorrectly rejecting valid tickers outside our curated ~20-company list)
  — both caught and locked in by new Phase 1 tests before shipping. Also hit
  a real ~2-hour DNS/network outage mid-test-run; the system degraded
  gracefully (502, not a crash) exactly as Phase 3's error-handling design
  intended, and a clean rerun confirmed no code issue.

### Phase 6 in plain terms

Phase 5 could already answer all three kinds of questions — single stock,
portfolio, comparison — but only if you told it exactly which mode to run
and handed it exact ticker symbols. Phase 6 is what makes it actually
usable: it can now read an ordinary typed question and figure out, on its
own, what you're asking for and which stocks you mean.

**What changed**: a new "intent reader" looks at the words in your question.
If it sees something like "compare" plus two company names, it knows you
want a head-to-head comparison. If it sees "portfolio" or spots several
company names listed together, it treats it as a portfolio check. If it
finds just one company name and nothing else, it treats it as a single-stock
question. If it can't find any recognizable company at all, it says so
plainly instead of guessing. As with the news-reader in Phase 3, this uses a
simple rule-based checklist rather than a full AI reader for now (no paid AI
key is hooked up yet) — swapping in a smarter AI reader later won't require
changing anything else in the system.

**The system now has permanent front doors**: real, fixed web addresses
that always exist — one for asking a plain-English question, one for
checking a specific stock, one for a portfolio, one for a head-to-head
comparison. Anyone (or any future UI) can now talk to the system through
these without needing to know how the multi-agent machinery underneath
works. You can also type either a company name ("infosys") or the official
trading symbol ("INFY.NS") anywhere — the system converts one into the
other automatically.

**Two small but real bugs got caught and fixed while building this**: first,
the piece that pulls stock names out of a sentence needed to be built fresh
(it didn't exist before). Second, an existing piece meant to convert a
symbol like "HCLTECH" into its proper trading form was incorrectly refusing
to do so for any company not already in the small demo list — fixed so it
now accepts any properly-shaped stock symbol and lets the real data source
be the judge of whether it exists, the same way it already worked for
company names.

**An unplanned real-world test**: partway through testing, the machine
genuinely lost its news-search connection for an extended stretch (a DNS
outage, nothing to do with this code). Rather than crashing or hanging the
whole system, the affected request came back with a clean "this part
failed" response while everything else kept working — exactly the safety
behavior built into Phase 3, now proven under a real, unplanned failure
rather than just a simulated one.

Bottom line: the system can now be asked a question in plain English through
a permanent, real address, and it correctly figures out on its own whether
you're asking about one stock, a portfolio, or a comparison — matching all
three original example questions from the very first ask. 75 checks across
every phase are passing. Next phase adds the actual visual interface
(Streamlit) so this can be used in a browser instead of through raw API
calls.

## Phase 7 — Streamlit UI
- Chat query box, portfolio manager (add/remove holdings, persisted
  locally), result rendering (verdict cards, indicator charts, sentiment
  headlines, comparison tables) — calling FastAPI only, never agents
  directly.
- **Test**: manually exercise all 3 query types in the running Streamlit app
  in a browser, including editing the portfolio and re-querying.
- **Status**: ✅ done — code lives in `phase7/` (`portfolio_store.py`,
  `api_client.py`, `app.py`, `tests/`), 19/19 new tests passed (94/94 with
  Phase 1–6 regression), see `phase7/TEST_RESULTS.md`. Tested three ways:
  plain unit tests for portfolio persistence, `TestClient`-backed tests for
  the API wrapper, and Streamlit's own headless `AppTest` framework (backed
  by a real live FastAPI server in a background thread) for the UI itself —
  then confirmed for real by starting both servers and checking in an actual
  browser. Two real bugs fixed along the way: a `st.table()` call crashing
  PyArrow serialization on a dict mixing numbers and a string, and
  `ApiClient`'s backend URL being cached at import time instead of read
  fresh per instance (would have silently broken pointing it at a test
  server). Indicator/price charts are out of scope — the backend only
  returns latest-snapshot values, not a time series, so indicators are shown
  as a metrics table instead.

### Phase 7 in plain terms

Every previous phase built real, working machinery, but you could only talk
to it through raw web addresses and JSON — fine for testing, not for an
actual person to use. Phase 7 puts an actual screen in front of it.

**What was built**: a web page with three things on it — a plain-English
question box (type "how is infosys doing" and hit Ask), a portfolio manager
where you can add or remove stock holdings by name (they get automatically
converted to their official trading symbol) and click "Analyze Portfolio,"
and a simple two-box form to compare any two stocks head-to-head. Whatever
comes back is shown as a clear verdict, a confidence percentage, and
expandable sections showing what the chart-reader, news-reader, and
numbers-reader each individually thought.

**An important design rule**: this screen never talks to the analysts
directly — it only ever talks to the same permanent web addresses built in
Phase 6, the same way any other outside program would. That keeps the
"front of house" (what you see) cleanly separated from the "back of house"
(how the analysis actually happens).

**How something this visual gets automatically tested without a person
clicking a mouse**: Streamlit (the tool used to build the screen) has its
own built-in way to simulate a person using the page — typing into boxes,
clicking buttons — entirely from a test script, without opening an actual
browser window. Combined with actually starting a real backend server in
the background during the test, this let every golden-path scenario (ask a
single-stock question, ask a comparison question, add a holding and analyze
a portfolio, get a graceful error message for a nonsense question) be
proven end-to-end automatically. On top of that, both real servers were
started for real and the page was checked in an actual browser by hand, as
the final confirmation.

**Two real bugs caught while building this**: first, one part of the page
tried to display a mix of numbers and a text label (like "increasing") in
the same table column, which a lower-level library couldn't handle
cleanly — fixed by converting everything to plain text before display, so
the table always renders cleanly instead of relying on an internal
auto-recovery that was silently papering over it. Second, the piece that
remembers which web address to talk to was reading that setting only once,
the very first time it was ever used in a session — meaning if a test later
tried to point it at a different (test) server, it would have silently kept
using the old address instead. Fixed so it checks the setting fresh every
time it's needed.

Bottom line: the system now has an actual usable screen, not just raw web
addresses — you can type a question, manage a portfolio, and compare stocks
through a real interface, with 94 checks passing across every phase built so
far and a live human check in a real browser confirming it works. The last
remaining phase is about polish and robustness rather than new features:
handling flaky data sources more gracefully, avoiding unnecessary repeat
lookups, and a final end-to-end pass over everything built.

## Phase 8 — Hardening
- Partial-failure handling (one agent/data source fails without failing the
  whole query), caching for yfinance/DuckDuckGo calls, rate-limit backoff,
  log review/cleanup, final regression pass across all 3 query types end to
  end.
- **Test**: force one data source to fail (e.g. bad ticker mid-portfolio) and
  confirm the rest of the report still returns with a clear error note for
  the failed piece.
- **Status**: ✅ done — code lives in `phase8/` (`cache.py`, `tests/`), plus
  hardening edits to `phase1/data/market.py`, `phase1/data/search.py`, and
  `phase1/logging_config.py`. 13/13 new tests passed (107/107 with Phase
  1–7 regression), see `phase8/TEST_RESULTS.md`. Caching verified live (a
  repeated real `get_history` call went from 5.67s to ~0s) and via the
  regression suite itself, which dropped from 94.67s to 42.59s after
  hardening landed. Added retry+backoff to `market.py` (previously only
  `search.py` had it), being careful to retry only genuine transient
  exceptions and never a permanently-invalid-ticker's empty result. Added
  log rotation (2 MB / 3 backups) so `dump.log` can't grow unbounded. The
  required bad-ticker-mid-portfolio regression was re-verified with the new
  hardening layer in place.

### Phase 8 in plain terms

Every previous phase focused on making the system *work*. Phase 8 focuses
on making it work *well* over time — the unglamorous but important cleanup
pass before calling this done.

**Caching, so it doesn't ask the same question twice needlessly**: if you
ask about Infosys, then ask again a minute later, the system used to go
fetch everything from scratch both times — hitting Yahoo Finance and
DuckDuckGo again for information that hasn't changed. Now it remembers
recent answers for a few minutes (5 minutes for prices/financials, 10
minutes for news, since news changes even more slowly) and reuses them
instantly instead of re-fetching. This was proven very concretely: the exact
same real request that took 5.67 seconds the first time took effectively
0 seconds the second time. As a side effect, the entire test suite for the
whole project got more than twice as fast (95 seconds down to 43 seconds),
since tests that check the same stock across different phases were
previously all separately re-fetching it.

**A safety rule for that memory**: if a lookup fails, the failure itself is
never "remembered" — only genuine successes get cached. That way, a
temporary internet hiccup doesn't get treated as if that stock will be
broken forever; the very next attempt tries fresh.

**Retrying automatically on genuine hiccups**: the price-and-financials
fetcher didn't have any "try again" logic before (unlike the news-search
piece, which already did) — if there was a brief network blip, it would
just give up immediately. Now it quietly retries once before giving up.
Importantly, it's careful NOT to retry when a stock symbol simply doesn't
exist (like a typo or a delisted company) — retrying something that will
never succeed would just waste several seconds for nothing, so that case
still fails immediately as before.

**Keeping the activity log from growing forever**: the log file that
records everything the system does was previously going to just keep
growing indefinitely the longer the system ran. It now automatically caps
itself at a reasonable size and keeps a few recent backups instead of one
ever-expanding file.

**One more check on the core safety promise**: with all of the above now
sitting underneath the system, it was worth re-confirming that the original
promise still holds — if one stock in a portfolio has a problem, the rest of
the portfolio's report should still come back complete, with a clear note
about just the broken part. It does.

Bottom line: this is the final phase. The system can be asked plain-English
questions about Indian stocks — single stock, portfolio, or comparison —
through a real browser interface, backed by three specialist AI-style
analysts (chart-based, news-based, fundamentals-based) that run in parallel
and get combined into one answer, with graceful handling of bad data and
now with sensible caching and retry behavior underneath. 107 automated
checks pass across all 8 phases, plus a confirmed working manual check in a
real browser.
