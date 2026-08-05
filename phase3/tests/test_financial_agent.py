from phase3.agents.financial import analyze_financial

_KNOWN_TICKERS = ["INFY.NS", "RELIANCE.NS", "TMPV.NS"]


def test_analyze_financial_returns_sane_output_infy():
    result = analyze_financial("INFY.NS")

    assert result["ticker"] == "INFY.NS"
    assert result["status"] == "ok"
    assert result["verdict"] in {"bullish", "bearish", "neutral"}
    assert 0 <= result["confidence"] <= 1
    assert len(result["reasoning"]) == 3
    assert result["ratios"]["shortName"]


def test_analyze_financial_returns_sane_output_reliance():
    result = analyze_financial("RELIANCE.NS")

    assert result["ticker"] == "RELIANCE.NS"
    assert result["status"] == "ok"
    assert result["verdict"] in {"bullish", "bearish", "neutral"}


def test_analyze_financial_returns_sane_output_tmpv():
    result = analyze_financial("TMPV.NS")

    assert result["ticker"] == "TMPV.NS"
    assert result["status"] == "ok"
    assert result["verdict"] in {"bullish", "bearish", "neutral"}


def test_analyze_financial_catches_bad_ticker_and_does_not_raise():
    result = analyze_financial("THISISNOTAREALTICKERXYZ.NS")

    assert result["ticker"] == "THISISNOTAREALTICKERXYZ.NS"
    assert result["status"] == "error"
    assert "error" in result
