# Market Analyst — Multi-Agent Architecture

## 1. Overview

A multi-agent system that answers natural-language questions about Indian stocks
(single stock, portfolio, or comparison) by fanning out to specialist analyst
agents in parallel and synthesizing their findings into one prediction/report.

```
User (Streamlit UI)
      │  HTTP
      ▼
FastAPI backend  ──────────────►  LangGraph Orchestrator (Master Node)
                                         │
                        ┌────────────────┼────────────────┐
                        ▼                ▼                ▼
                 Technical Agent  Sentiment Agent   Financial Agent
                        │                │                │
                        ▼                ▼                ▼
                    yfinance        DuckDuckGo         yfinance
                   (price/OHLCV)    (news/web)       (fundamentals)
                        │                │                │
                        └────────────────┼────────────────┘
                                         ▼
                               Synthesizer / Predictor
                                         │
                                         ▼
                              Final structured report
```

## 2. Query types → routing

| # | Example query | Tickers resolved | Orchestrator behavior |
|---|---|---|---|
| 1 | "how's my portfolio doing" (Tata Motors, Infosys, Cupid...) | N tickers from stored portfolio | Fan out 3 agents × N tickers in parallel → per-ticker synthesis → portfolio roll-up |
| 2 | "how is infosys doing" | 1 ticker | Fan out 3 agents × 1 ticker → single synthesis |
| 3 | "compare mahindra and reliance" | 2 (or more) tickers | Fan out 3 agents × each ticker → per-ticker synthesis → comparison synthesis |

All three cases reduce to the same primitive: **run the 3 agents for each
resolved ticker in parallel, then synthesize.** Portfolio and Compare just add
a roll-up step after the per-ticker synthesis.

## 3. Components

### 3.1 UI Layer — Streamlit
- Chat-style query box.
- Portfolio manager (add/remove holdings: ticker, qty, buy price — stored locally, e.g. JSON/SQLite).
- Renders: per-stock verdict cards, indicator charts (price + SMA/RSI), sentiment headlines, comparison tables.
- Talks to backend only via FastAPI HTTP calls (no direct agent/tool calls from UI) — keeps UI and backend independently testable.

### 3.2 API Layer — FastAPI
Endpoints:
- `POST /query` — free-text query, backend classifies intent + tickers, runs graph, returns report. Main entrypoint for the UI.
- `POST /portfolio/analyze` — body: list of holdings → runs the "portfolio" flow directly (skips intent classification).
- `POST /compare` — body: list of tickers → runs the "compare" flow directly.
- `GET /stock/{ticker}` — runs the "single stock" flow directly.
- `GET /health` — liveness check.
- (Optional) `GET /docs` — free Swagger UI from FastAPI for manual testing.

Having both a generic `/query` (LLM does intent+ticker extraction) and direct
endpoints (`/portfolio/analyze`, `/compare`, `/stock/{ticker}`) lets you test
each agent/flow without depending on the NLU step.

### 3.3 Orchestration — LangGraph

**Graph nodes:**
1. `intent_router` — (only used by `/query`) classifies query into `single | portfolio | compare` and extracts/resolves ticker symbols (e.g. "infosys" → `INFY.NS`, "mahindra" → `M&M.NS`, "reliance" → `RELIANCE.NS`). Uses an LLM call with a small structured-output schema.
2. `dispatch` — master/orchestrator node. For each resolved ticker, uses LangGraph's `Send` API to fan out to the 3 agent nodes concurrently (this is the "parallel fire" step).
3. `technical_agent`, `sentiment_agent`, `financial_agent` — run per ticker, per branch, fully independent of each other (no shared state during execution).
4. `per_ticker_synthesizer` — joins the 3 agent outputs for one ticker into a single verdict (bullish/bearish/neutral + confidence + reasoning).
5. `final_aggregator` — joins all per-ticker syntheses:
   - single → passes through
   - portfolio → computes overall portfolio health, best/worst performer, risk flags
   - compare → produces side-by-side table + "winner" rationale

**State shape (conceptual):**
```python
class TickerResult(TypedDict):
    ticker: str
    technical: dict   # indicators, trend, support/resistance, verdict
    sentiment: dict   # headlines, sentiment score, key events, verdict
    financial: dict   # fundamentals, ratios, verdict
    synthesis: dict    # combined verdict, confidence, reasoning

class GraphState(TypedDict):
    query: str
    intent: Literal["single", "portfolio", "compare"]
    tickers: list[str]
    results: dict[str, TickerResult]   # keyed by ticker
    final_report: dict
```

Use LangGraph's `Send(node_name, payload)` from the `dispatch` node to fan out
one `Send` per `(ticker, agent)` pair — this is what gives true parallel
execution instead of a sequential loop.

### 3.4 Agents

**Technical Analyst**
- Tool: yfinance OHLCV history (`yf.Ticker(x).history(...)`).
- Computes: SMA/EMA crossovers, RSI, MACD, Bollinger Bands, volume trend, recent support/resistance.
- Output: trend direction, key levels, verdict (bullish/bearish/neutral), confidence.

**Sentiment Analyst**
- Tool: DuckDuckGo web/news search (`duckduckgo-search` / `ddgs` package — free, no API key).
- Query pattern: `"{company name} stock news"`, restricted to recent results.
- LLM step: summarize headlines → sentiment score, key events (earnings, management changes, regulatory news), notable risks.
- Output: sentiment label, score, top 3-5 cited headlines/links, verdict.

**Financial Analyst**
- Tool: yfinance fundamentals (`Ticker.info`, `Ticker.financials`, `Ticker.balance_sheet`, `Ticker.cashflow`).
- Computes: P/E, EPS growth, revenue growth, debt/equity, ROE, margins, sector comparison if available.
- Output: fundamental health verdict, key ratios, red flags.

**Master Node (Orchestrator)**
- Not a "4th analyst" — it's the `dispatch` + `final_aggregator` logic in the graph. Responsibilities:
  - Resolve tickers, decide flow type
  - Fire the 3 agents in parallel per ticker
  - Handle partial failures gracefully (e.g. sentiment search times out → still return technical + financial with a note, don't fail the whole query)
  - Synthesize final prediction with weighted reasoning across the 3 dimensions
  - Roll up for portfolio/compare cases

### 3.5 Data Layer
- `data/market.py` — thin wrapper around yfinance (history, info, financials) with basic in-memory caching (e.g. 5–15 min TTL) to avoid re-fetching on repeated queries and to soften yfinance rate limits.
- `data/search.py` — thin wrapper around DuckDuckGo search with retry/backoff.
- `data/tickers.py` — Indian company-name → NSE ticker symbol resolution (small lookup table + fallback fuzzy match), since users will type "infosys" not "INFY.NS".

## 4. Tech stack

| Layer | Choice |
|---|---|
| Orchestration | LangGraph (StateGraph + `Send` for fan-out) |
| LLM | Groq (Groq API) via `langchain-groq` or direct SDK |
| Market data | `yfinance` |
| Web/news search | `duckduckgo-search` (`ddgs`) |
| Backend API | FastAPI + Uvicorn |
| UI | Streamlit |
| Data validation | Pydantic (shared schemas between agents, API, and UI) |
| Caching | `functools.lru_cache` / `diskcache` (simple) — Redis only if you outgrow it |

## 5. Suggested repo structure

```
MARKET-ANALYST/
├── backend/
│   ├── main.py                 # FastAPI app + routes
│   ├── graph/
│   │   ├── state.py            # GraphState, TickerResult schemas
│   │   ├── router.py           # intent_router node
│   │   ├── dispatch.py         # master node: fan-out via Send
│   │   ├── agents/
│   │   │   ├── technical.py
│   │   │   ├── sentiment.py
│   │   │   └── financial.py
│   │   ├── synthesizer.py      # per_ticker_synthesizer + final_aggregator
│   │   └── build_graph.py      # wires nodes/edges into a compiled graph
│   ├── data/
│   │   ├── market.py           # yfinance wrapper
│   │   ├── search.py           # duckduckgo wrapper
│   │   └── tickers.py          # name → NSE symbol resolution
│   └── schemas.py               # shared Pydantic models (API req/resp)
├── frontend/
│   └── app.py                   # Streamlit app
├── tests/
│   ├── test_agents.py
│   ├── test_graph.py
│   └── test_api.py
├── requirements.txt
├── .env.example                 # GROQ_API_KEY, etc.
└── ARCHITECTURE.md
```

## 6. Non-functional notes

- **Parallelism**: rely on LangGraph `Send` (or `asyncio.gather` inside a single dispatch node) — don't loop synchronously over tickers/agents.
- **Partial failure tolerance**: each agent node should catch its own exceptions and return a `status: "error"` result rather than raising, so one flaky data source doesn't kill the whole query.
- **Rate limits**: yfinance and DuckDuckGo are both unofficial/free — add basic retry+backoff and short-lived caching.
- **Testability**: FastAPI's direct endpoints (`/stock/{ticker}`, `/compare`, `/portfolio/analyze`) let you test each flow with `curl`/Swagger without needing the LLM intent-classification step.
- **Extensibility**: adding a 4th analyst (e.g. macro/sector analyst) later is just one more node + one more branch in `dispatch`/`synthesizer` — the graph shape doesn't change.
