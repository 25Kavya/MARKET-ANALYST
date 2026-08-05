import json
import sqlite3
import threading
import time
from pathlib import Path

from phase1.logging_config import get_logger

logger = get_logger(__name__)

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "market_analyst.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS llm_cache (
    cache_key TEXT PRIMARY KEY,
    tool_name TEXT NOT NULL,
    prompt_version TEXT NOT NULL,
    query_text TEXT,
    response_json TEXT NOT NULL,
    created_at TEXT NOT NULL
)
"""

_MAX_RETRIES = 5
_RETRY_BACKOFF_SECONDS = 0.05

_schema_lock = threading.Lock()
_schema_ready_for = set()


def _ensure_schema(conn):
    """CREATE TABLE IF NOT EXISTS still takes an exclusive lock, so serialize
    it per DB path rather than letting every short-lived connection race on
    it — under concurrent access that race is what produces spurious
    'database is locked' errors on the very first calls."""
    key = str(DB_PATH)
    if key in _schema_ready_for:
        return
    with _schema_lock:
        if key not in _schema_ready_for:
            conn.execute(_SCHEMA)
            _schema_ready_for.add(key)


def _connect():
    # isolation_level=None (autocommit) so each statement commits immediately
    # instead of leaving an implicit transaction open, minimizing how long a
    # write lock is held under concurrent access.
    conn = sqlite3.connect(DB_PATH, timeout=5, isolation_level=None)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    _ensure_schema(conn)
    return conn


def _with_retry(fn):
    """Belt-and-suspenders retry on top of PRAGMA busy_timeout — SQLite can
    still surface 'database is locked' under heavy concurrent access even
    with a busy timeout set, so retry a few times with a short backoff."""
    last_error = None
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            return fn()
        except sqlite3.OperationalError as exc:
            last_error = exc
            if attempt < _MAX_RETRIES:
                time.sleep(_RETRY_BACKOFF_SECONDS * attempt)
    raise last_error


def get_cached(tool_name, cache_key):
    """Return the cached response dict, or None on a miss.

    Opens a short-lived connection per call rather than holding one open
    across requests, since FastAPI's sync routes run on a threadpool and
    sqlite3 connections aren't safe to share across threads.
    """
    def _do():
        conn = _connect()
        try:
            return conn.execute(
                "SELECT response_json FROM llm_cache WHERE tool_name = ? AND cache_key = ?",
                (tool_name, cache_key),
            ).fetchone()
        finally:
            conn.close()

    row = _with_retry(_do)

    if row is None:
        logger.info("cache_store miss tool=%s key=%r", tool_name, cache_key)
        return None

    logger.info("cache_store hit tool=%s key=%r", tool_name, cache_key)
    return json.loads(row[0])


def set_cached(tool_name, cache_key, prompt_version, query_text, response):
    """Store a successful response. Never call this for a failed/errored call —
    a failure should never be "remembered" as if it were a stable result."""
    def _do():
        conn = _connect()
        try:
            conn.execute(
                """
                INSERT OR REPLACE INTO llm_cache
                    (cache_key, tool_name, prompt_version, query_text, response_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    cache_key,
                    tool_name,
                    prompt_version,
                    query_text,
                    json.dumps(response),
                    time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                ),
            )
        finally:
            conn.close()

    _with_retry(_do)
    logger.info("cache_store set tool=%s key=%r", tool_name, cache_key)
