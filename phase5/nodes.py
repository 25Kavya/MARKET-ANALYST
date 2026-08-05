import time

from phase1.logging_config import get_logger
from phase4.graph import analyze_ticker

logger = get_logger(__name__)

_DIRECTION = {"bullish": 1, "neutral": 0, "bearish": -1, "unknown": 0}


def _direction_score(synthesis):
    return _DIRECTION.get(synthesis["verdict"], 0) * synthesis["confidence"]


def ticker_node(state):
    ticker = state["ticker"]
    logger.info("phase5.nodes.ticker_node start ticker=%s", ticker)
    synthesis = analyze_ticker(ticker)
    logger.info("phase5.nodes.ticker_node done ticker=%s verdict=%s", ticker, synthesis["verdict"])
    return {"ticker_syntheses": [synthesis]}


def portfolio_aggregator(ticker_syntheses):
    per_ticker = {s["ticker"]: s for s in ticker_syntheses}
    scores = {ticker: _direction_score(s) for ticker, s in per_ticker.items()}

    verdict_counts = {"bullish": 0, "bearish": 0, "neutral": 0}
    for s in ticker_syntheses:
        if s["verdict"] in verdict_counts:
            verdict_counts[s["verdict"]] += 1
    overall_verdict = max(verdict_counts, key=verdict_counts.get) if any(verdict_counts.values()) else "unknown"

    best_performer = max(scores, key=scores.get)
    worst_performer = min(scores, key=scores.get)
    risk_flags = [
        s["ticker"] for s in ticker_syntheses
        if s["notes"] or len(s["contributing_agents"]) < 3
    ]

    return {
        "mode": "portfolio",
        "tickers": list(per_ticker.keys()),
        "overall_verdict": overall_verdict,
        "best_performer": best_performer,
        "worst_performer": worst_performer,
        "risk_flags": risk_flags,
        "per_ticker": per_ticker,
    }


def compare_aggregator(ticker_syntheses):
    per_ticker = {s["ticker"]: s for s in ticker_syntheses}
    scores = {ticker: _direction_score(s) for ticker, s in per_ticker.items()}

    ranking = sorted(
        ({"ticker": ticker, "score": score, "verdict": per_ticker[ticker]["verdict"]}
         for ticker, score in scores.items()),
        key=lambda row: row["score"],
        reverse=True,
    )
    winner = ranking[0]["ticker"]
    rationale = (
        f"{winner} ranks highest with a combined score of {ranking[0]['score']:.2f} "
        f"(verdict: {ranking[0]['verdict']}), ahead of "
        f"{', '.join(r['ticker'] for r in ranking[1:])}"
    )

    return {
        "mode": "compare",
        "tickers": list(per_ticker.keys()),
        "ranking": ranking,
        "winner": winner,
        "rationale": rationale,
        "per_ticker": per_ticker,
    }


def aggregator(state):
    start = time.monotonic()
    mode = state["mode"]
    ticker_syntheses = state["ticker_syntheses"]

    if mode == "portfolio":
        report = portfolio_aggregator(ticker_syntheses)
    elif mode == "compare":
        report = compare_aggregator(ticker_syntheses)
    else:
        raise ValueError(f"unknown mode: {mode!r}")

    elapsed = time.monotonic() - start
    logger.info(
        "phase5.nodes.aggregator ok mode=%s tickers=%s elapsed=%.3fs",
        mode, report["tickers"], elapsed,
    )
    return {"report": report}
