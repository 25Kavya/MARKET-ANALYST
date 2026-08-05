import time

from phase1.data.market import MarketDataError
from phase1.logging_config import get_logger
from phase2.agents.technical import analyze_technical
from phase3.agents.financial import analyze_financial
from phase3.agents.sentiment import analyze_sentiment

logger = get_logger(__name__)

_AGENT_ORDER = ["technical", "sentiment", "financial"]


def technical_node(state):
    ticker = state["ticker"]
    logger.info("nodes.technical_node start ticker=%s", ticker)
    try:
        result = analyze_technical(ticker)
        result = {**result, "agent": "technical", "status": "ok"}
    except MarketDataError as exc:
        logger.error("nodes.technical_node failed ticker=%s error=%s", ticker, exc)
        result = {"agent": "technical", "status": "error", "error": str(exc)}
    return {"agent_results": [result]}


def sentiment_node(state):
    ticker = state["ticker"]
    logger.info("nodes.sentiment_node start ticker=%s", ticker)
    result = {**analyze_sentiment(ticker), "agent": "sentiment"}
    return {"agent_results": [result]}


def financial_node(state):
    ticker = state["ticker"]
    logger.info("nodes.financial_node start ticker=%s", ticker)
    result = {**analyze_financial(ticker), "agent": "financial"}
    return {"agent_results": [result]}


def synthesizer(state):
    start = time.monotonic()
    ticker = state["ticker"]
    by_agent = {r["agent"]: r for r in state["agent_results"]}

    votes = {"bullish": 0, "bearish": 0, "neutral": 0}
    contributing = []
    notes = []
    reasoning = []

    for agent_name in _AGENT_ORDER:
        result = by_agent.get(agent_name)
        if result is None:
            notes.append(f"{agent_name} did not report a result")
            continue
        if result.get("status") == "error":
            notes.append(f"{agent_name} unavailable: {result.get('error')}")
            continue

        verdict = result.get("verdict")
        votes[verdict] += 1
        contributing.append(agent_name)
        agent_confidence = result.get("confidence")
        agent_reasons = "; ".join(result.get("reasoning", []))
        reasoning.append(f"{agent_name} ({verdict}, confidence {agent_confidence}): {agent_reasons}")

    if contributing:
        overall_verdict = max(votes, key=votes.get)
        confidence = round(votes[overall_verdict] / len(contributing), 2)
    else:
        overall_verdict = "unknown"
        confidence = 0.0

    synthesis = {
        "ticker": ticker,
        "verdict": overall_verdict,
        "confidence": confidence,
        "contributing_agents": contributing,
        "notes": notes,
        "reasoning": reasoning,
        "agent_results": by_agent,
    }

    elapsed = time.monotonic() - start
    logger.info(
        "nodes.synthesizer ok ticker=%s verdict=%s confidence=%.2f contributing=%s elapsed=%.3fs",
        ticker, overall_verdict, confidence, contributing, elapsed,
    )
    return {"synthesis": synthesis}
