import time

from phase1.data.market import MarketDataError, get_fundamentals
from phase1.logging_config import get_logger

logger = get_logger(__name__)


def _profitability_vote(profit_margins):
    if profit_margins is None:
        return "neutral", "insufficient data for profit margin"
    if profit_margins > 0.15:
        return "bullish", f"healthy profit margin at {profit_margins:.1%}"
    if profit_margins > 0.05:
        return "neutral", f"moderate profit margin at {profit_margins:.1%}"
    return "bearish", f"thin/negative profit margin at {profit_margins:.1%}"


def _growth_vote(revenue_growth):
    if revenue_growth is None:
        return "neutral", "insufficient data for revenue growth"
    if revenue_growth > 0.10:
        return "bullish", f"strong revenue growth at {revenue_growth:.1%}"
    if revenue_growth >= 0:
        return "neutral", f"modest revenue growth at {revenue_growth:.1%}"
    return "bearish", f"revenue declining at {revenue_growth:.1%}"


def _leverage_vote(debt_to_equity):
    if debt_to_equity is None:
        return "neutral", "insufficient data for debt-to-equity"
    if debt_to_equity < 50:
        return "bullish", f"low leverage, debt/equity at {debt_to_equity:.1f}"
    if debt_to_equity <= 100:
        return "neutral", f"moderate leverage, debt/equity at {debt_to_equity:.1f}"
    return "bearish", f"high leverage, debt/equity at {debt_to_equity:.1f}"


def analyze_financial(ticker):
    start = time.monotonic()
    logger.info("financial.analyze_financial request ticker=%s", ticker)

    try:
        info = get_fundamentals(ticker)
    except MarketDataError as exc:
        logger.error("financial.analyze_financial failed ticker=%s error=%s", ticker, exc)
        return {
            "ticker": ticker,
            "status": "error",
            "error": str(exc),
        }

    votes = [
        _profitability_vote(info.get("profitMargins")),
        _growth_vote(info.get("revenueGrowth")),
        _leverage_vote(info.get("debtToEquity")),
    ]

    counts = {"bullish": 0, "bearish": 0, "neutral": 0}
    for label, _ in votes:
        counts[label] += 1

    verdict = max(counts, key=counts.get)
    confidence = round(counts[verdict] / len(votes), 2)
    reasoning = [reason for _, reason in votes]

    result = {
        "ticker": ticker,
        "status": "ok",
        "ratios": {
            "shortName": info.get("shortName"),
            "sector": info.get("sector"),
            "marketCap": info.get("marketCap"),
            "trailingPE": info.get("trailingPE"),
            "priceToBook": info.get("priceToBook"),
            "returnOnEquity": info.get("returnOnEquity"),
            "debtToEquity": info.get("debtToEquity"),
            "revenueGrowth": info.get("revenueGrowth"),
            "profitMargins": info.get("profitMargins"),
        },
        "verdict": verdict,
        "confidence": confidence,
        "reasoning": reasoning,
    }

    elapsed = time.monotonic() - start
    logger.info(
        "financial.analyze_financial ok ticker=%s verdict=%s confidence=%.2f elapsed=%.2fs",
        ticker, verdict, confidence, elapsed,
    )
    return result
