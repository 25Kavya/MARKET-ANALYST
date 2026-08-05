import os

import requests

from phase1.logging_config import get_logger

logger = get_logger(__name__)


class ApiError(Exception):
    pass


class ApiClient:
    """Thin HTTP wrapper around the Phase 6 FastAPI backend.

    `client` defaults to a real `requests.Session` hitting `base_url`
    (a live server). Tests inject a `fastapi.testclient.TestClient` with
    `base_url=""` so the same code path exercises the real API without a
    separate running process.

    The `MARKET_ANALYST_API_URL` env var is read fresh at construction time
    (not cached at import time) so tests can point a fresh `ApiClient` at a
    throwaway test server started after this module was already imported.
    """

    def __init__(self, client=None, base_url=None):
        self.client = client or requests.Session()
        self.base_url = base_url if base_url is not None else os.getenv("MARKET_ANALYST_API_URL", "http://localhost:8000")

    def _url(self, path):
        return f"{self.base_url}{path}"

    def _handle(self, resp):
        if resp.status_code >= 400:
            try:
                detail = resp.json().get("detail", resp.text)
            except ValueError:
                detail = resp.text
            logger.warning("api_client request failed status=%s detail=%s", resp.status_code, detail)
            raise ApiError(detail)
        return resp.json()

    def health(self):
        return self._handle(self.client.get(self._url("/health")))

    def query(self, text):
        return self._handle(self.client.post(self._url("/query"), json={"query": text}))

    def get_stock(self, ticker):
        return self._handle(self.client.get(self._url(f"/stock/{ticker}")))

    def portfolio_analyze(self, tickers):
        return self._handle(self.client.post(self._url("/portfolio/analyze"), json={"tickers": tickers}))

    def compare(self, tickers):
        return self._handle(self.client.post(self._url("/compare"), json={"tickers": tickers}))
