import pytest

from phase1.data.tickers import TickerResolutionError
from phase7 import portfolio_store


@pytest.fixture
def portfolio_path(tmp_path):
    return tmp_path / "portfolio.json"


def test_load_portfolio_returns_empty_list_when_file_missing(portfolio_path):
    assert portfolio_store.load_portfolio(portfolio_path) == []


def test_add_holding_resolves_name_and_persists(portfolio_path):
    holdings = portfolio_store.add_holding("infosys", qty=10, buy_price=1500, path=portfolio_path)

    assert holdings == [{"ticker": "INFY.NS", "name": "infosys", "qty": 10, "buy_price": 1500}]
    assert portfolio_store.load_portfolio(portfolio_path) == holdings


def test_add_holding_twice_updates_instead_of_duplicating(portfolio_path):
    portfolio_store.add_holding("infosys", qty=10, path=portfolio_path)
    holdings = portfolio_store.add_holding("infosys", qty=20, path=portfolio_path)

    assert len(holdings) == 1
    assert holdings[0]["qty"] == 20


def test_add_multiple_holdings(portfolio_path):
    portfolio_store.add_holding("infosys", path=portfolio_path)
    holdings = portfolio_store.add_holding("reliance", path=portfolio_path)

    assert {h["ticker"] for h in holdings} == {"INFY.NS", "RELIANCE.NS"}


def test_remove_holding_by_ticker(portfolio_path):
    portfolio_store.add_holding("infosys", path=portfolio_path)
    portfolio_store.add_holding("reliance", path=portfolio_path)

    remaining = portfolio_store.remove_holding("INFY.NS", path=portfolio_path)

    assert [h["ticker"] for h in remaining] == ["RELIANCE.NS"]


def test_remove_holding_by_name(portfolio_path):
    portfolio_store.add_holding("infosys", path=portfolio_path)

    remaining = portfolio_store.remove_holding("infosys", path=portfolio_path)

    assert remaining == []


def test_add_holding_raises_for_unresolvable_name(portfolio_path):
    with pytest.raises(TickerResolutionError):
        portfolio_store.add_holding("zzz not a real company zzz", path=portfolio_path)
