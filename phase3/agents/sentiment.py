import time

from phase1.data.search import SearchError, search_news
from phase1.logging_config import get_logger

logger = get_logger(__name__)

# Heuristic keyword lexicon. This is a placeholder for a real LLM-based
# summarizer (to be swapped in for a Groq call, now that GROQ_API_KEY is
# configured) — kept as-is for now since it's already built and tested.
_POSITIVE_WORDS = [
    "surge", "surges", "rally", "rallies", "gain", "gains", "growth", "profit",
    "profits", "beat", "beats", "upgrade", "upgraded", "bullish", "record high",
    "strong", "outperform", "buy rating", "expansion", "robust", "soar", "soars",
    "jump", "jumps", "wins", "win", "boost", "boosts", "positive",
]
_NEGATIVE_WORDS = [
    "fall", "falls", "drop", "drops", "decline", "declines", "loss", "losses",
    "miss", "misses", "downgrade", "downgraded", "bearish", "weak", "probe",
    "fraud", "lawsuit", "recall", "layoff", "layoffs", "slump", "plunge",
    "plunges", "sell rating", "concern", "concerns", "crash", "crashes",
    "scandal", "penalty",
]


def _score_headlines(headlines):
    pos_count = 0
    neg_count = 0
    for item in headlines:
        text = f"{item.get('title', '')} {item.get('snippet', '')}".lower()
        pos_count += sum(1 for word in _POSITIVE_WORDS if word in text)
        neg_count += sum(1 for word in _NEGATIVE_WORDS if word in text)

    total = pos_count + neg_count
    if total == 0:
        return 0.0, 0, 0
    score = (pos_count - neg_count) / total
    return score, pos_count, neg_count


def analyze_sentiment(ticker, company_query=None, max_results=8):
    start = time.monotonic()
    query = company_query or f"{ticker.replace('.NS', '')} stock news"
    logger.info("sentiment.analyze_sentiment request ticker=%s query=%r", ticker, query)

    try:
        headlines = search_news(query, max_results=max_results)
    except SearchError as exc:
        logger.error("sentiment.analyze_sentiment search failed ticker=%s error=%s", ticker, exc)
        return {
            "ticker": ticker,
            "status": "error",
            "error": str(exc),
        }

    score, pos_count, neg_count = _score_headlines(headlines)

    if score > 0.2:
        verdict = "bullish"
    elif score < -0.2:
        verdict = "bearish"
    else:
        verdict = "neutral"

    confidence = round(min(abs(score), 1.0), 2)
    reasoning = [
        f"{len(headlines)} headlines analyzed, {pos_count} positive signal(s), "
        f"{neg_count} negative signal(s) found"
    ]

    result = {
        "ticker": ticker,
        "status": "ok",
        "query": query,
        "headlines": headlines,
        "sentiment_score": round(score, 2),
        "verdict": verdict,
        "confidence": confidence,
        "reasoning": reasoning,
    }

    elapsed = time.monotonic() - start
    logger.info(
        "sentiment.analyze_sentiment ok ticker=%s verdict=%s confidence=%.2f elapsed=%.2fs",
        ticker, verdict, confidence, elapsed,
    )
    return result
