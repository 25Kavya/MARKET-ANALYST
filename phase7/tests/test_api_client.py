import pytest
from fastapi.testclient import TestClient

from phase6.api import app
from phase7.api_client import ApiClient, ApiError


@pytest.fixture
def client():
    return ApiClient(client=TestClient(app), base_url="")


def test_health(client):
    assert client.health() == {"status": "ok"}


def test_query_single(client):
    result = client.query("how is infosys doing")
    assert result["intent"]["mode"] == "single"
    assert result["result"]["ticker"] == "INFY.NS"


def test_get_stock_resolves_company_name(client):
    result = client.get_stock("infosys")
    assert result["ticker"] == "INFY.NS"


def test_portfolio_analyze(client):
    result = client.portfolio_analyze(["infosys", "reliance"])
    assert result["mode"] == "portfolio"
    assert set(result["tickers"]) == {"INFY.NS", "RELIANCE.NS"}


def test_compare(client):
    result = client.compare(["mahindra", "reliance"])
    assert result["mode"] == "compare"
    assert result["winner"] in {"M&M.NS", "RELIANCE.NS"}


def test_error_response_raises_api_error(client):
    with pytest.raises(ApiError):
        client.query("what is the weather today")
