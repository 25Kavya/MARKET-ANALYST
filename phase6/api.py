from typing import List

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from phase1.data.tickers import TickerResolutionError, resolve_ticker
from phase1.logging_config import get_logger
from phase4.graph import analyze_ticker
from phase5.graph import analyze_portfolio, compare_tickers
from phase6.intent import classify_intent

logger = get_logger(__name__)

app = FastAPI(title="Market Analyst — Phase 6 (full API surface)")


class QueryRequest(BaseModel):
    query: str


class TickerListRequest(BaseModel):
    tickers: List[str]


def _resolve_many(names):
    resolved = []
    for name in names:
        try:
            resolved.append(resolve_ticker(name))
        except TickerResolutionError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    return resolved


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/stock/{ticker}")
def get_stock(ticker: str):
    try:
        resolved = resolve_ticker(ticker)
    except TickerResolutionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return analyze_ticker(resolved)


@app.post("/portfolio/analyze")
def post_portfolio_analyze(body: TickerListRequest):
    if not body.tickers:
        raise HTTPException(status_code=400, detail="tickers list must not be empty")
    resolved = _resolve_many(body.tickers)
    return analyze_portfolio(resolved)


@app.post("/compare")
def post_compare(body: TickerListRequest):
    if len(body.tickers) < 2:
        raise HTTPException(status_code=400, detail="compare requires at least 2 tickers")
    resolved = _resolve_many(body.tickers)
    return compare_tickers(resolved)


@app.post("/query")
def post_query(body: QueryRequest):
    intent = classify_intent(body.query)
    mode = intent["mode"]
    tickers = intent["tickers"]

    if mode == "unknown" or not tickers:
        raise HTTPException(status_code=400, detail="could not identify any stock in the query")

    if mode == "single":
        result = analyze_ticker(tickers[0])
    elif mode == "portfolio":
        result = analyze_portfolio(tickers)
    else:
        result = compare_tickers(tickers)

    return {"intent": intent, "result": result}
