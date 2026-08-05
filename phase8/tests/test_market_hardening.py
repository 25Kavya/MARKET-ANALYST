import pandas as pd
import pytest

import phase1.data.market as market_module
from phase1.data.market import MarketDataError, get_fundamentals, get_history


def _fresh_history_df():
    return pd.DataFrame(
        {"Open": [1], "High": [1], "Low": [1], "Close": [1], "Volume": [100]},
        index=pd.to_datetime(["2026-01-01"]),
    )


@pytest.fixture(autouse=True)
def clear_caches():
    get_history.cache.clear()
    get_fundamentals.cache.clear()
    yield
    get_history.cache.clear()
    get_fundamentals.cache.clear()


def test_get_history_retries_transient_error_then_succeeds(monkeypatch):
    attempts = []

    class FlakyTicker:
        def __init__(self, ticker):
            pass

        def history(self, period, interval):
            attempts.append(1)
            if len(attempts) == 1:
                raise ConnectionError("simulated transient network error")
            return _fresh_history_df()

    monkeypatch.setattr(market_module.yf, "Ticker", FlakyTicker)

    df = get_history("FAKE.NS", period="5d")

    assert not df.empty
    assert len(attempts) == 2  # failed once, succeeded on retry


def test_get_history_raises_after_exhausting_retries(monkeypatch):
    attempts = []

    class AlwaysFailsTicker:
        def __init__(self, ticker):
            pass

        def history(self, period, interval):
            attempts.append(1)
            raise ConnectionError("simulated persistent network error")

    monkeypatch.setattr(market_module.yf, "Ticker", AlwaysFailsTicker)

    with pytest.raises(MarketDataError):
        get_history("FAKE.NS", period="5d")

    assert len(attempts) == market_module._MAX_RETRIES


def test_get_history_does_not_retry_permanently_invalid_ticker(monkeypatch):
    attempts = []

    class EmptyResultTicker:
        def __init__(self, ticker):
            pass

        def history(self, period, interval):
            attempts.append(1)
            return pd.DataFrame()  # yfinance's real behavior for an invalid ticker

    monkeypatch.setattr(market_module.yf, "Ticker", EmptyResultTicker)

    with pytest.raises(MarketDataError):
        get_history("THISISNOTAREALTICKERXYZ.NS", period="5d")

    assert len(attempts) == 1  # no wasted retries for a non-exception "no data" result


def test_get_history_caches_repeated_calls(monkeypatch):
    attempts = []

    class CountingTicker:
        def __init__(self, ticker):
            pass

        def history(self, period, interval):
            attempts.append(1)
            return _fresh_history_df()

    monkeypatch.setattr(market_module.yf, "Ticker", CountingTicker)

    get_history("FAKE.NS", period="5d")
    get_history("FAKE.NS", period="5d")

    assert len(attempts) == 1  # second call was served from cache


def test_get_history_cache_key_distinguishes_period(monkeypatch):
    attempts = []

    class CountingTicker:
        def __init__(self, ticker):
            pass

        def history(self, period, interval):
            attempts.append(period)
            return _fresh_history_df()

    monkeypatch.setattr(market_module.yf, "Ticker", CountingTicker)

    get_history("FAKE.NS", period="5d")
    get_history("FAKE.NS", period="6mo")

    assert len(attempts) == 2  # different period -> different cache key, not a hit
