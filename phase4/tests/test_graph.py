import re
import time
from datetime import datetime
from pathlib import Path

import pytest
from langgraph.types import Send

import phase4.nodes as nodes_module
from phase4.graph import analyze_ticker, dispatch

_KNOWN_TICKERS = ["INFY.NS", "RELIANCE.NS", "TMPV.NS"]
_DUMP_LOG_PATH = Path(__file__).resolve().parent.parent.parent / "dump.log"


def test_dispatch_returns_sends_for_all_three_agents():
    sends = dispatch({"ticker": "INFY.NS"})

    assert len(sends) == 3
    assert all(isinstance(s, Send) for s in sends)

    targets = {s.node for s in sends}
    assert targets == {"technical_node", "sentiment_node", "financial_node"}
    assert all(s.arg == {"ticker": "INFY.NS"} for s in sends)


@pytest.mark.parametrize("ticker", _KNOWN_TICKERS)
def test_analyze_ticker_returns_valid_synthesis(ticker):
    synthesis = analyze_ticker(ticker)

    assert synthesis["ticker"] == ticker
    assert synthesis["verdict"] in {"bullish", "bearish", "neutral"}
    assert 0 <= synthesis["confidence"] <= 1
    assert set(synthesis["contributing_agents"]) <= {"technical", "sentiment", "financial"}
    assert set(synthesis["agent_results"].keys()) == {"technical", "sentiment", "financial"}
    assert len(synthesis["reasoning"]) == len(synthesis["contributing_agents"])


def test_analyze_ticker_handles_bad_ticker_gracefully():
    # technical + financial fail (real yfinance 404); sentiment still succeeds
    # since DuckDuckGo doesn't validate ticker existence. The graph must not
    # crash and must report what failed instead of silently guessing.
    synthesis = analyze_ticker("THISISNOTAREALTICKERXYZ.NS")

    assert synthesis["ticker"] == "THISISNOTAREALTICKERXYZ.NS"
    assert synthesis["verdict"] in {"bullish", "bearish", "neutral", "unknown"}
    assert len(synthesis["notes"]) >= 2  # technical and financial both failed
    assert set(synthesis["agent_results"].keys()) == {"technical", "sentiment", "financial"}
    assert synthesis["agent_results"]["technical"]["status"] == "error"
    assert synthesis["agent_results"]["financial"]["status"] == "error"


def test_nodes_run_concurrently_not_sequentially(monkeypatch):
    delay = 0.5

    def fake_technical(ticker):
        time.sleep(delay)
        return {"ticker": ticker, "verdict": "bullish", "confidence": 1.0, "reasoning": ["fake technical"]}

    def fake_sentiment(ticker):
        time.sleep(delay)
        return {"ticker": ticker, "status": "ok", "verdict": "bullish", "confidence": 1.0, "reasoning": ["fake sentiment"]}

    def fake_financial(ticker):
        time.sleep(delay)
        return {"ticker": ticker, "status": "ok", "verdict": "bullish", "confidence": 1.0, "reasoning": ["fake financial"]}

    monkeypatch.setattr(nodes_module, "analyze_technical", fake_technical)
    monkeypatch.setattr(nodes_module, "analyze_sentiment", fake_sentiment)
    monkeypatch.setattr(nodes_module, "analyze_financial", fake_financial)

    start = time.monotonic()
    synthesis = analyze_ticker("FAKE.NS")
    elapsed = time.monotonic() - start

    assert synthesis["verdict"] == "bullish"
    # sequential would take ~3*delay; parallel should take ~1*delay
    assert elapsed < delay * 2, f"expected concurrent execution, took {elapsed:.2f}s for 3x{delay}s agents"


def test_dump_log_shows_concurrent_agent_start_timestamps():
    before = _DUMP_LOG_PATH.stat().st_size if _DUMP_LOG_PATH.exists() else 0

    analyze_ticker("INFY.NS")

    with open(_DUMP_LOG_PATH, encoding="utf-8") as f:
        f.seek(before)
        new_lines = f.readlines()

    pattern = re.compile(r"^([\d\-]+ [\d:,]+) .*nodes\.(technical|sentiment|financial)_node start")
    timestamps = {}
    for line in new_lines:
        match = pattern.search(line)
        if match:
            ts_str, agent = match.groups()
            timestamps[agent] = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S,%f")

    assert set(timestamps.keys()) == {"technical", "sentiment", "financial"}
    spread = max(timestamps.values()) - min(timestamps.values())
    assert spread.total_seconds() < 1.0, f"agent start timestamps spread {spread} apart, expected concurrent dispatch"
