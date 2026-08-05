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

## Deploying

The backend (FastAPI + MCP server, bundled together via `start.sh`) and the
UI are deployed as two separate free services:

**1. Backend → [Render](https://dashboard.render.com)**
- New → Blueprint → connect this GitHub repo (Render reads `render.yaml`).
- When prompted for `GROQ_API_KEY`, paste your key — it's stored as a Render
  secret, never committed to the repo.
- Deploy, then copy the resulting public URL
  (`https://market-analyst-backend-xxxx.onrender.com`).

**2. UI → [Streamlit Community Cloud](https://share.streamlit.io)**
- New app → this repo → main file path `phase7/app.py`.
- In Advanced settings → Secrets, add:
  ```
  MARKET_ANALYST_API_URL = "https://market-analyst-backend-xxxx.onrender.com"
  ```
  (the URL copied from step 1).
- Deploy. The app is now live at a `*.streamlit.app` URL.

Note: Render's free tier sleeps after inactivity and its filesystem is
ephemeral, so the SQLite intent-cache and any saved portfolio reset on
restart/redeploy — expected for a demo deployment, not a data-loss bug.
