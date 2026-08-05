from fastapi import FastAPI, HTTPException

from phase1.logging_config import get_logger
from phase3.agents.financial import analyze_financial
from phase3.agents.sentiment import analyze_sentiment

logger = get_logger(__name__)

app = FastAPI(title="Market Analyst — Phase 3 (sentiment + financial, direct routes)")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/stock/{ticker}/sentiment")
def get_sentiment(ticker: str):
    result = analyze_sentiment(ticker)
    if result["status"] == "error":
        logger.warning("api.get_sentiment upstream failure ticker=%s error=%s", ticker, result["error"])
        raise HTTPException(status_code=502, detail=result["error"])
    return result


@app.get("/stock/{ticker}/financial")
def get_financial(ticker: str):
    result = analyze_financial(ticker)
    if result["status"] == "error":
        logger.warning("api.get_financial upstream failure ticker=%s error=%s", ticker, result["error"])
        raise HTTPException(status_code=502, detail=result["error"])
    return result
