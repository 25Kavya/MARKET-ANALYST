from phase5.graph import analyze_portfolio


def test_bad_ticker_mid_portfolio_still_returns_full_report_with_hardening_in_place():
    """Phase 8's required regression check: force one data source to fail
    (a delisted/nonexistent ticker) inside a multi-stock portfolio and
    confirm the rest of the report still comes back, with a clear note
    about the failed piece — now re-verified with caching + retry/backoff
    sitting underneath the data layer."""
    tickers = ["INFY.NS", "THISISNOTAREALTICKERXYZ.NS", "RELIANCE.NS"]

    report = analyze_portfolio(tickers)

    assert report["mode"] == "portfolio"
    assert set(report["tickers"]) == set(tickers)
    assert "THISISNOTAREALTICKERXYZ.NS" in report["risk_flags"]

    good_ticker_syntheses = [
        report["per_ticker"]["INFY.NS"],
        report["per_ticker"]["RELIANCE.NS"],
    ]
    for synthesis in good_ticker_syntheses:
        assert synthesis["verdict"] in {"bullish", "bearish", "neutral"}
        assert len(synthesis["contributing_agents"]) == 3

    bad_ticker_synthesis = report["per_ticker"]["THISISNOTAREALTICKERXYZ.NS"]
    assert len(bad_ticker_synthesis["notes"]) >= 2  # technical + financial failed
    assert bad_ticker_synthesis["agent_results"]["technical"]["status"] == "error"
    assert bad_ticker_synthesis["agent_results"]["financial"]["status"] == "error"
