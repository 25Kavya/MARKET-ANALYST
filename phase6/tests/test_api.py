import pytest
from fastapi.testclient import TestClient

from phase6.api import app

client = TestClient(app)


def test_health_endpoint():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_get_stock_endpoint_resolves_company_name():
    resp = client.get("/stock/infosys")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ticker"] == "INFY.NS"
    assert body["verdict"] in {"bullish", "bearish", "neutral"}


def test_get_stock_endpoint_accepts_raw_ticker():
    resp = client.get("/stock/RELIANCE.NS")
    assert resp.status_code == 200
    assert resp.json()["ticker"] == "RELIANCE.NS"


def test_get_stock_endpoint_invalid_name_returns_400():
    resp = client.get("/stock/zzz not a real company zzz")
    assert resp.status_code == 400


def test_post_portfolio_analyze_with_company_names():
    resp = client.post("/portfolio/analyze", json={"tickers": ["infosys", "reliance"]})
    assert resp.status_code == 200
    body = resp.json()
    assert body["mode"] == "portfolio"
    assert set(body["tickers"]) == {"INFY.NS", "RELIANCE.NS"}


def test_post_portfolio_analyze_empty_list_returns_400():
    resp = client.post("/portfolio/analyze", json={"tickers": []})
    assert resp.status_code == 400


def test_post_compare_with_company_names():
    resp = client.post("/compare", json={"tickers": ["mahindra", "reliance"]})
    assert resp.status_code == 200
    body = resp.json()
    assert body["mode"] == "compare"
    assert body["winner"] in {"M&M.NS", "RELIANCE.NS"}


def test_post_compare_single_ticker_returns_400():
    resp = client.post("/compare", json={"tickers": ["infosys"]})
    assert resp.status_code == 400


@pytest.mark.parametrize(
    "query,expected_mode",
    [
        ("how is infosys doing", "single"),
        ("compare the stocks between the mahindra and reliance", "compare"),
    ],
)
def test_post_query_end_to_end(query, expected_mode):
    resp = client.post("/query", json={"query": query})
    assert resp.status_code == 200
    body = resp.json()
    assert body["intent"]["mode"] == expected_mode
    assert "result" in body


def test_post_query_portfolio_end_to_end():
    resp = client.post(
        "/query",
        json={"query": "hows my portfolio doing (infosys, cupid)"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["intent"]["mode"] == "portfolio"
    assert body["result"]["mode"] == "portfolio"
    assert set(body["result"]["tickers"]) == {"INFY.NS", "CUPID.NS"}


def test_post_query_unknown_returns_400():
    resp = client.post("/query", json={"query": "what is the weather today"})
    assert resp.status_code == 400
