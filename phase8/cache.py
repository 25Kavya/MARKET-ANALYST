import threading
import time
from functools import wraps

from phase1.logging_config import get_logger

logger = get_logger(__name__)


class TTLCache:
    def __init__(self, ttl_seconds):
        self.ttl_seconds = ttl_seconds
        self._store = {}
        self._lock = threading.Lock()

    def get(self, key):
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None, False
            value, expires_at = entry
            if time.monotonic() >= expires_at:
                del self._store[key]
                return None, False
            return value, True

    def set(self, key, value):
        with self._lock:
            self._store[key] = (value, time.monotonic() + self.ttl_seconds)

    def clear(self):
        with self._lock:
            self._store.clear()

    def __len__(self):
        with self._lock:
            return len(self._store)


def ttl_cache(ttl_seconds, key_fn=None):
    """Cache a function's return value for ttl_seconds, keyed by its
    arguments (or a custom key_fn(*args, **kwargs) -> hashable key).

    Exceptions are never cached — a failed call (bad ticker, transient
    network error) always re-runs the wrapped function next time, rather
    than "remembering" a failure as if it were a stable result.
    """
    def decorator(func):
        cache = TTLCache(ttl_seconds)

        @wraps(func)
        def wrapper(*args, **kwargs):
            key = key_fn(*args, **kwargs) if key_fn else (args, tuple(sorted(kwargs.items())))
            value, hit = cache.get(key)
            if hit:
                logger.info("cache hit func=%s key=%r", func.__qualname__, key)
                return value

            logger.info("cache miss func=%s key=%r", func.__qualname__, key)
            value = func(*args, **kwargs)
            cache.set(key, value)
            return value

        wrapper.cache = cache
        return wrapper

    return decorator
