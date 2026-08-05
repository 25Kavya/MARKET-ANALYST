import time

import phase4.nodes as nodes_module
from phase5.graph import analyze_portfolio, compare_tickers, dispatch_tickers

_PORTFOLIO_TICKERS = ["INFY.NS", "RELIANCE.NS", "TMPV.NS"]
_COMPARE_TICKERS = ["M&M.NS", "RELIANCE.NS"]


def test_dispatch_tickers_returns_one_send_per_ticker():
    sends = dispatch_tickers({"tickers": _PORTFOLIO_TICKERS})

    assert len(sends) == 3
    assert all(s.node == "ticker_node" for s in sends)
    assert {s.arg["ticker"] for s in sends} == set(_PORTFOLIO_TICKERS)


def test_analyze_portfolio_real_tickers():
    report = analyze_portfolio(_PORTFOLIO_TICKERS)

    assert report["mode"] == "portfolio"
    assert set(report["tickers"]) == set(_PORTFOLIO_TICKERS)
    assert report["overall_verdict"] in {"bullish", "bearish", "neutral", "unknown"}
    assert report["best_performer"] in _PORTFOLIO_TICKERS
    assert report["worst_performer"] in _PORTFOLIO_TICKERS
    assert isinstance(report["risk_flags"], list)
    assert set(report["per_ticker"].keys()) == set(_PORTFOLIO_TICKERS)


def test_compare_tickers_real():
    report = compare_tickers(_COMPARE_TICKERS)

    assert report["mode"] == "compare"
    assert set(report["tickers"]) == set(_COMPARE_TICKERS)
    assert len(report["ranking"]) == 2
    assert report["winner"] in _COMPARE_TICKERS
    assert report["ranking"][0]["ticker"] == report["winner"]
    # ranking must be sorted descending by score
    scores = [row["score"] for row in report["ranking"]]
    assert scores == sorted(scores, reverse=True)
    assert report["rationale"]


def test_portfolio_handles_one_bad_ticker_without_crashing():
    tickers = ["INFY.NS", "THISISNOTAREALTICKERXYZ.NS"]
    report = analyze_portfolio(tickers)

    assert report["mode"] == "portfolio"
    assert set(report["tickers"]) == set(tickers)
    # the bad ticker had < 3 contributing agents (technical + financial failed)
    assert "THISISNOTAREALTICKERXYZ.NS" in report["risk_flags"]
    assert report["overall_verdict"] in {"bullish", "bearish", "neutral", "unknown"}


def test_tickers_run_concurrently_not_ticker_by_ticker(monkeypatch):
    delay = 0.4

    def fake_technical(ticker):
        time.sleep(delay)
        return {"ticker": ticker, "verdict": "bullish", "confidence": 1.0, "reasoning": ["fake technical"]}

    def fake_sentiment(ticker):
        time.sleep(delay)
        return {"ticker": ticker, "status": "ok", "verdict": "bullish", "confidence": 1.0, "reasoning": ["fake sentiment"]}

    def fake_financial(ticker):
        time.sleep(delay)
        return {"ticker": ticker, "status": "ok", "verdict": "bullish", "confidence": 1.0, "reasoning": ["fake financial"]}

    monkeypatch.setattr(nodes_module, "analyze_technical", fake_technical)
    monkeypatch.setattr(nodes_module, "analyze_sentiment", fake_sentiment)
    monkeypatch.setattr(nodes_module, "analyze_financial", fake_financial)

    tickers = ["FAKE1.NS", "FAKE2.NS", "FAKE3.NS"]
    start = time.monotonic()
    report = analyze_portfolio(tickers)
    elapsed = time.monotonic() - start

    assert report["overall_verdict"] == "bullish"
    # ticker-by-ticker (bug) would take ~3*delay = 1.2s; true 2-layer
    # concurrency (3 tickers x 3 agents all at once) should take ~1*delay.
    assert elapsed < delay * 2, (
        f"expected tickers to run concurrently (not one at a time), "
        f"took {elapsed:.2f}s for {len(tickers)} tickers x 3x{delay}s agents"
    )
