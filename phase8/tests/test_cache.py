import time

import pytest

from phase8.cache import TTLCache, ttl_cache


def test_ttl_cache_returns_cached_value_within_ttl():
    calls = []

    @ttl_cache(ttl_seconds=5)
    def add(a, b):
        calls.append((a, b))
        return a + b

    assert add(1, 2) == 3
    assert add(1, 2) == 3
    assert len(calls) == 1  # second call was a cache hit, function not re-run


def test_ttl_cache_distinguishes_different_arguments():
    calls = []

    @ttl_cache(ttl_seconds=5)
    def add(a, b):
        calls.append((a, b))
        return a + b

    add(1, 2)
    add(2, 3)
    assert len(calls) == 2


def test_ttl_cache_expires_after_ttl():
    calls = []

    @ttl_cache(ttl_seconds=0.2)
    def add(a, b):
        calls.append((a, b))
        return a + b

    add(1, 2)
    time.sleep(0.3)
    add(1, 2)
    assert len(calls) == 2  # ttl expired, second call re-ran the function


def test_ttl_cache_does_not_cache_exceptions():
    calls = []

    @ttl_cache(ttl_seconds=5)
    def flaky(x):
        calls.append(x)
        if len(calls) == 1:
            raise ValueError("boom")
        return x

    with pytest.raises(ValueError):
        flaky(1)

    assert flaky(1) == 1  # second call actually re-ran, not a cached failure
    assert len(calls) == 2


def test_ttl_cache_supports_custom_key_fn():
    calls = []

    @ttl_cache(ttl_seconds=5, key_fn=lambda ticker, period="1mo": ticker)
    def fetch(ticker, period="1mo"):
        calls.append((ticker, period))
        return period

    fetch("INFY.NS", period="1mo")
    fetch("INFY.NS", period="6mo")  # different period, same custom key -> still a hit
    assert len(calls) == 1


def test_ttl_cache_object_get_set_clear():
    cache = TTLCache(ttl_seconds=5)
    assert cache.get("k") == (None, False)

    cache.set("k", "v")
    assert cache.get("k") == ("v", True)

    cache.clear()
    assert cache.get("k") == (None, False)
