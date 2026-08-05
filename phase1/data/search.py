import time

from ddgs import DDGS
from ddgs.exceptions import DDGSException

from phase1.logging_config import get_logger
from phase8.cache import ttl_cache

logger = get_logger(__name__)

_MAX_RETRIES = 3
_BACKOFF_SECONDS = 2
_CACHE_TTL_SECONDS = 600  # 10 minutes — news doesn't change fast enough to justify re-searching sooner


class SearchError(Exception):
    pass


@ttl_cache(ttl_seconds=_CACHE_TTL_SECONDS)
def search_news(query, max_results=5):
    start = time.monotonic()
    logger.info("search.search_news request query=%r max_results=%d", query, max_results)

    last_error = None
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_results))
            elapsed = time.monotonic() - start
            logger.info(
                "search.search_news ok query=%r attempt=%d results=%d elapsed=%.2fs",
                query, attempt, len(results), elapsed,
            )
            return [
                {
                    "title": r.get("title"),
                    "url": r.get("href"),
                    "snippet": r.get("body"),
                }
                for r in results
            ]
        except DDGSException as exc:
            last_error = exc
            logger.warning(
                "search.search_news attempt %d/%d failed query=%r error=%s",
                attempt, _MAX_RETRIES, query, exc,
            )
            if attempt < _MAX_RETRIES:
                time.sleep(_BACKOFF_SECONDS * attempt)

    logger.error("search.search_news exhausted retries query=%r error=%s", query, last_error)
    raise SearchError(f"search failed for query {query!r}: {last_error}")
