# Market Analyst

A multi-agent AI stock research system for Indian equities (NSE). Ask a
plain-English question — about one stock, your whole portfolio, or a
head-to-head comparison — and three specialist agents (technical, sentiment,
financial) analyze it in parallel and combine their opinions into one answer.

## What it does

Handles three kinds of queries, routed automatically from plain English:

- **Single stock** — "how is infosys doing"
- **Portfolio** — "how is my portfolio doing"
- **Compare** — "compare mahindra and reliance"

## Architecture

Three agents run **in parallel** for each ticker:

- **Technical** — price/volume indicators (`yfinance`)
- **Sentiment** — recent news headlines (DuckDuckGo search)
- **Financial** — fundamentals: margins, growth, debt

A LangGraph node synthesizes their output into a verdict + confidence +
reasoning per ticker, then rolls up across tickers for portfolio/compare
modes. Query intent (single/portfolio/compare + which tickers) is classified
by an LLM (Groq, via a local MCP server) with a keyword-heuristic fallback if
that server isn't running.

See `ARCHITECTURE.md` for the full design and `PHASES.md` for how it was
built, phase by phase.

## Tech stack

FastAPI · Streamlit · LangGraph · yfinance · DuckDuckGo search · Groq (via
MCP) · SQLite (response cache) · pytest

## Setup

```bash
git clone https://github.com/25Kavya/MARKET-ANALYST.git
cd MARKET-ANALYST
pip install -r requirements.txt
cp .env.example .env   # then fill in GROQ_API_KEY
```

## Running it

Three processes, each in its own terminal:

```bash
python -m phase9.mcp_server              # MCP + Groq intent server (port 8100)
uvicorn phase6.api:app --port 8000       # FastAPI backend
streamlit run phase7/app.py              # UI (port 8501)
```

Open http://localhost:8501 and try the three example queries above. FastAPI
docs are at http://localhost:8000/docs.

If the MCP server isn't running, intent classification silently falls back
to a keyword heuristic — the app still works, just without the LLM's
judgment on ambiguous phrasing.

## Testing

```bash
pytest                                   # 131 passed, 1 skipped
RUN_LIVE_LLM_TESTS=1 pytest phase6/tests/test_intent.py -m live_llm  # real Groq call
```

## Project status

All 9 build phases are complete and tested (131/131 automated checks
passing). `PHASES.md` currently documents Phases 1–8 as final; Phase 9
(MCP-backed Groq intent classification) landed after that and isn't yet
reflected there — see `phase9/TEST_RESULTS.md` for its verification.

**Known gaps:**
- No process supervisor for `phase9/mcp_server.py` — must be started manually.
- No CI pipeline yet.
