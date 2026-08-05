import pytest
from fastapi.testclient import TestClient

from phase3.api import app

_KNOWN_TICKERS = ["INFY.NS", "RELIANCE.NS", "TMPV.NS"]

client = TestClient(app)


def test_health_endpoint():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.parametrize("ticker", _KNOWN_TICKERS)
def test_get_sentiment_endpoint_known_tickers(ticker):
    resp = client.get(f"/stock/{ticker}/sentiment")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ticker"] == ticker
    assert body["verdict"] in {"bullish", "bearish", "neutral"}


@pytest.mark.parametrize("ticker", _KNOWN_TICKERS)
def test_get_financial_endpoint_known_tickers(ticker):
    resp = client.get(f"/stock/{ticker}/financial")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ticker"] == ticker
    assert body["verdict"] in {"bullish", "bearish", "neutral"}


def test_get_financial_endpoint_invalid_ticker_returns_502():
    resp = client.get("/stock/THISISNOTAREALTICKERXYZ.NS/financial")
    assert resp.status_code == 502
    assert "detail" in resp.json()
