import time

import yfinance as yf

from phase1.logging_config import get_logger
from phase8.cache import ttl_cache

logger = get_logger(__name__)

_MAX_RETRIES = 2
_BACKOFF_SECONDS = 1
_CACHE_TTL_SECONDS = 300  # 5 minutes — price/fundamentals don't need to be fetched more often than this


class MarketDataError(Exception):
    pass


def _fetch_with_retry(description, ticker, fetch_fn):
    """Retry only genuine exceptions (network errors, malformed responses)
    from the fetch call itself. A permanently invalid ticker doesn't raise —
    yfinance returns an empty/placeholder result instead — so that case is
    handled separately by the caller and never wastes time being retried."""
    last_error = None
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            return fetch_fn()
        except Exception as exc:
            last_error = exc
            logger.warning(
                "market.%s attempt %d/%d failed ticker=%s error=%s",
                description, attempt, _MAX_RETRIES, ticker, exc,
            )
            if attempt < _MAX_RETRIES:
                time.sleep(_BACKOFF_SECONDS * attempt)

    logger.error("market.%s exhausted retries ticker=%s error=%s", description, ticker, last_error)
    raise MarketDataError(f"failed to fetch {description} for {ticker}: {last_error}") from last_error


@ttl_cache(ttl_seconds=_CACHE_TTL_SECONDS)
def get_history(ticker, period="1mo", interval="1d"):
    start = time.monotonic()
    logger.info("market.get_history request ticker=%s period=%s interval=%s", ticker, period, interval)

    df = _fetch_with_retry("get_history", ticker, lambda: yf.Ticker(ticker).history(period=period, interval=interval))

    if df is None or df.empty:
        logger.warning("market.get_history empty result ticker=%s", ticker)
        raise MarketDataError(f"no history data returned for {ticker}")

    elapsed = time.monotonic() - start
    logger.info("market.get_history ok ticker=%s rows=%d elapsed=%.2fs", ticker, len(df), elapsed)
    return df


@ttl_cache(ttl_seconds=_CACHE_TTL_SECONDS)
def get_fundamentals(ticker):
    start = time.monotonic()
    logger.info("market.get_fundamentals request ticker=%s", ticker)

    info = _fetch_with_retry("get_fundamentals", ticker, lambda: yf.Ticker(ticker).info)

    if not info or info.get("regularMarketPrice") is None and info.get("currentPrice") is None and info.get("shortName") is None:
        logger.warning("market.get_fundamentals empty/invalid result ticker=%s", ticker)
        raise MarketDataError(f"no fundamentals data returned for {ticker}")

    fields = [
        "shortName",
        "sector",
        "industry",
        "marketCap",
        "trailingPE",
        "forwardPE",
        "trailingEps",
        "priceToBook",
        "debtToEquity",
        "returnOnEquity",
        "revenueGrowth",
        "grossMargins",
        "profitMargins",
        "currentPrice",
        "regularMarketPrice",
        "fiftyTwoWeekHigh",
        "fiftyTwoWeekLow",
    ]
    result = {field: info.get(field) for field in fields}

    elapsed = time.monotonic() - start
    logger.info("market.get_fundamentals ok ticker=%s elapsed=%.2fs", ticker, elapsed)
    return result
