import pytest

from phase1.data import market, search, tickers


# ---------------------------------------------------------------------------
# market.py — live yfinance calls
# ---------------------------------------------------------------------------

def test_get_history_returns_rows_for_known_ticker():
    df = market.get_history("INFY.NS", period="5d")
    assert not df.empty
    for col in ["Open", "High", "Low", "Close", "Volume"]:
        assert col in df.columns


def test_get_history_raises_for_invalid_ticker():
    with pytest.raises(market.MarketDataError):
        market.get_history("THISISNOTAREALTICKERXYZ.NS", period="5d")


def test_get_fundamentals_returns_expected_fields():
    info = market.get_fundamentals("INFY.NS")
    assert info["shortName"]
    assert "trailingPE" in info
    assert "marketCap" in info


# ---------------------------------------------------------------------------
# search.py — live DuckDuckGo calls
# ---------------------------------------------------------------------------

def test_search_news_returns_results():
    results = search.search_news("Infosys stock news", max_results=3)
    assert 0 < len(results) <= 3
    for r in results:
        assert r["title"]
        assert r["url"]


def test_search_news_respects_max_results():
    results = search.search_news("Reliance Industries news", max_results=1)
    assert len(results) <= 1


# ---------------------------------------------------------------------------
# tickers.py — pure lookup logic, no network
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "name,expected",
    [
        ("tata motors", "TMPV.NS"),
        ("infosys", "INFY.NS"),
        ("cupid", "CUPID.NS"),
        ("mahindra", "M&M.NS"),
        ("reliance", "RELIANCE.NS"),
    ],
)
def test_resolve_ticker_exact_aliases(name, expected):
    assert tickers.resolve_ticker(name) == expected


def test_resolve_ticker_passthrough_symbol():
    assert tickers.resolve_ticker("INFY.NS") == "INFY.NS"
    assert tickers.resolve_ticker("TCS") == "TCS.NS"


def test_resolve_ticker_passthrough_for_ticker_not_in_curated_list():
    # A well-formed ticker symbol we haven't curated an alias for should
    # still pass through — existence is validated later by the data layer,
    # not by this resolver.
    assert tickers.resolve_ticker("HCLTECH") == "HCLTECH.NS"
    assert tickers.resolve_ticker("HCLTECH.NS") == "HCLTECH.NS"


def test_resolve_ticker_fuzzy_match_typo():
    assert tickers.resolve_ticker("infosis") == "INFY.NS"


def test_resolve_ticker_raises_for_unknown_name():
    with pytest.raises(tickers.TickerResolutionError):
        tickers.resolve_ticker("zzz not a real company zzz")


def test_resolve_ticker_raises_for_empty_name():
    with pytest.raises(tickers.TickerResolutionError):
        tickers.resolve_ticker("   ")


# ---------------------------------------------------------------------------
# tickers.py — find_mentioned_tickers, pure lookup logic, no network
# ---------------------------------------------------------------------------

def test_find_mentioned_tickers_portfolio_query():
    text = "hows my portfolio doing (tata motors, infosys, cupid ......etc and other indian stocks)"
    assert tickers.find_mentioned_tickers(text) == ["TMPV.NS", "INFY.NS", "CUPID.NS"]


def test_find_mentioned_tickers_single_company_query():
    assert tickers.find_mentioned_tickers("how is infosys doing") == ["INFY.NS"]


def test_find_mentioned_tickers_compare_query():
    text = "compare the stocks between the mahindra and reliance"
    assert tickers.find_mentioned_tickers(text) == ["M&M.NS", "RELIANCE.NS"]


def test_find_mentioned_tickers_no_matches():
    assert tickers.find_mentioned_tickers("what is the weather today") == []


def test_find_mentioned_tickers_empty_text():
    assert tickers.find_mentioned_tickers("") == []


# ---------------------------------------------------------------------------
# tickers.py — bundled NSE equity list (nse_equity_list.csv), pure logic
# ---------------------------------------------------------------------------

def test_bundled_nse_list_loaded_with_thousands_of_aliases():
    # sanity check the CSV actually loaded, not just the curated ~20 companies
    assert len(tickers._ALIAS_TO_TICKER) > 1000


def test_resolve_ticker_by_official_name_not_in_curated_list():
    # ETERNAL LIMITED (Zomato's post-rebrand registered name) is reachable
    # via the bundled NSE list even without any manual curation.
    assert tickers.resolve_ticker("eternal limited") == "ETERNAL.NS"


def test_resolve_ticker_brand_name_not_in_official_records():
    # "zomato" appears nowhere in NSE's official name/symbol records (the
    # company is registered as "Eternal Limited" / ETERNAL) — only reachable
    # because it's hand-curated, same as "mahindra" or "reliance".
    assert tickers.resolve_ticker("zomato") == "ETERNAL.NS"
    assert tickers.find_mentioned_tickers("how is zomato doing") == ["ETERNAL.NS"]


def test_resolve_ticker_by_bare_symbol_not_in_curated_list():
    assert tickers.resolve_ticker("paytm") == "PAYTM.NS"


def test_curated_alias_wins_over_csv_derived_alias():
    # "mahindra" / "tcs" / "reliance" etc. must still resolve exactly as
    # curated, even though the CSV also derives aliases for the same tickers.
    assert tickers.resolve_ticker("mahindra") == "M&M.NS"
    assert tickers.resolve_ticker("tcs") == "TCS.NS"


def test_find_mentioned_tickers_still_finds_short_curated_aliases():
    # regression guard: the free-text length filter (aimed at risky
    # CSV-derived short symbols like "TI"/"BI") must not swallow legitimate
    # short curated aliases like "tcs".
    result = tickers.find_mentioned_tickers("infosys and reliance and tcs")
    assert set(result) == {"INFY.NS", "RELIANCE.NS", "TCS.NS"}


def test_find_mentioned_tickers_ignores_risky_short_csv_symbol():
    # "TI" (Tilaknagar Industries) must not false-positive-match inside an
    # ordinary word containing that substring.
    result = tickers.find_mentioned_tickers("what is my position in infosys today")
    assert result == ["INFY.NS"]
