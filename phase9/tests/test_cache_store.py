import threading

import pytest

from phase9 import cache_store


@pytest.fixture(autouse=True)
def _temp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(cache_store, "DB_PATH", tmp_path / "test_cache.db")


def test_cache_miss_returns_none():
    assert cache_store.get_cached("some_tool", "missing-key") is None


def test_cache_set_then_get_hit():
    cache_store.set_cached("some_tool", "k1", "v1", "how is infosys doing", {"mode": "single"})

    assert cache_store.get_cached("some_tool", "k1") == {"mode": "single"}


def test_cache_distinguishes_tool_name():
    cache_store.set_cached("tool_a", "same-key", "v1", "query", {"mode": "single"})

    assert cache_store.get_cached("tool_b", "same-key") is None


def test_cache_set_overwrites_existing_key():
    cache_store.set_cached("some_tool", "k1", "v1", "query", {"mode": "single"})
    cache_store.set_cached("some_tool", "k1", "v1", "query", {"mode": "portfolio"})

    assert cache_store.get_cached("some_tool", "k1") == {"mode": "portfolio"}


def test_cache_never_stores_failures():
    # set_cached is only ever called by callers on success — confirm nothing
    # gets written just by a failed lookup (a miss doesn't create a row).
    cache_store.get_cached("some_tool", "never-set")
    assert cache_store.get_cached("some_tool", "never-set") is None


def test_cache_concurrent_writes_and_reads_do_not_crash():
    errors = []

    def worker(i):
        try:
            key = f"key-{i % 5}"
            cache_store.set_cached("concurrent_tool", key, "v1", f"query {i}", {"mode": "single", "i": i})
            cache_store.get_cached("concurrent_tool", key)
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors
    for i in range(5):
        assert cache_store.get_cached("concurrent_tool", f"key-{i}") is not None
