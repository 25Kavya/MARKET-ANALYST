import pytest

from phase1.data.search import SearchError
from phase3.agents import sentiment as sentiment_module
from phase3.agents.sentiment import analyze_sentiment

_KNOWN_TICKERS = ["INFY.NS", "RELIANCE.NS", "TMPV.NS"]


@pytest.mark.parametrize("ticker", _KNOWN_TICKERS)
def test_analyze_sentiment_returns_sane_output(ticker):
    result = analyze_sentiment(ticker)

    assert result["ticker"] == ticker
    assert result["status"] == "ok"
    assert result["verdict"] in {"bullish", "bearish", "neutral"}
    assert 0 <= result["confidence"] <= 1
    assert -1 <= result["sentiment_score"] <= 1
    assert len(result["headlines"]) > 0
    assert len(result["reasoning"]) == 1

    for headline in result["headlines"]:
        assert headline["title"]
        assert headline["url"]


def test_analyze_sentiment_catches_search_failure_and_does_not_raise(monkeypatch):
    def _boom(query, max_results=8):
        raise SearchError("simulated search backend outage")

    monkeypatch.setattr(sentiment_module, "search_news", _boom)

    result = analyze_sentiment("INFY.NS")

    assert result["status"] == "error"
    assert "simulated search backend outage" in result["error"]
