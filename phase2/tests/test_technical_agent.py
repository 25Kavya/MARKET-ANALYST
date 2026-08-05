import pytest
from fastapi.testclient import TestClient

from phase1.data.market import MarketDataError
from phase2.agents.technical import analyze_technical
from phase2.api import app

_KNOWN_TICKERS = ["INFY.NS", "RELIANCE.NS", "TMPV.NS"]

client = TestClient(app)


# ---------------------------------------------------------------------------
# Agent, called directly
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("ticker", _KNOWN_TICKERS)
def test_analyze_technical_returns_sane_output(ticker):
    result = analyze_technical(ticker)

    assert result["ticker"] == ticker
    assert result["price"] > 0
    assert result["verdict"] in {"bullish", "bearish", "neutral"}
    assert 0 <= result["confidence"] <= 1
    assert len(result["reasoning"]) == 3

    indicators = result["indicators"]
    for key in ["sma20", "sma50", "rsi14", "macd", "macd_signal",
                "bollinger_upper", "bollinger_lower", "support", "resistance"]:
        assert key in indicators
        assert indicators[key] is not None

    assert 0 <= indicators["rsi14"] <= 100
    assert indicators["support"] <= result["price"] <= indicators["resistance"] * 1.05
    assert indicators["volume_trend"] in {"increasing", "decreasing", "flat", "unknown"}


def test_analyze_technical_raises_for_invalid_ticker():
    with pytest.raises(MarketDataError):
        analyze_technical("THISISNOTAREALTICKERXYZ.NS")


# ---------------------------------------------------------------------------
# FastAPI route (walking skeleton: UI -> API -> agent -> data source)
# ---------------------------------------------------------------------------

def test_health_endpoint():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.parametrize("ticker", _KNOWN_TICKERS)
def test_get_technical_endpoint_known_tickers(ticker):
    resp = client.get(f"/stock/{ticker}/technical")
    assert resp.status_code == 200

    body = resp.json()
    assert body["ticker"] == ticker
    assert body["verdict"] in {"bullish", "bearish", "neutral"}
    assert "indicators" in body


def test_get_technical_endpoint_invalid_ticker_returns_404():
    resp = client.get("/stock/THISISNOTAREALTICKERXYZ.NS/technical")
    assert resp.status_code == 404
    assert "detail" in resp.json()
