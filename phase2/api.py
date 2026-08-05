from fastapi import FastAPI, HTTPException

from phase1.data.market import MarketDataError
from phase1.logging_config import get_logger
from phase2.agents.technical import analyze_technical

logger = get_logger(__name__)

app = FastAPI(title="Market Analyst — Phase 2 (walking skeleton)")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/stock/{ticker}/technical")
def get_technical(ticker: str):
    try:
        return analyze_technical(ticker)
    except MarketDataError as exc:
        logger.warning("api.get_technical failed ticker=%s error=%s", ticker, exc)
        raise HTTPException(status_code=404, detail=str(exc)) from exc
