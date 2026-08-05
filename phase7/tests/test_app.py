from streamlit.testing.v1 import AppTest


def _fresh_app(live_server_url, monkeypatch):
    monkeypatch.setenv("MARKET_ANALYST_API_URL", live_server_url)
    at = AppTest.from_file("phase7/app.py")
    at.run(timeout=30)
    assert not at.exception
    return at


def test_app_loads_without_error(live_server_url, monkeypatch):
    at = _fresh_app(live_server_url, monkeypatch)
    assert not at.exception


def test_query_single_stock_golden_path(live_server_url, monkeypatch):
    at = _fresh_app(live_server_url, monkeypatch)

    at.text_input(key="query_input").set_value("how is infosys doing")
    at.button(key="ask_button").click().run(timeout=30)

    assert not at.exception
    assert "query_result" in at.session_state
    result = at.session_state["query_result"]
    assert result["intent"]["mode"] == "single"
    assert result["result"]["ticker"] == "INFY.NS"


def test_query_compare_golden_path(live_server_url, monkeypatch):
    at = _fresh_app(live_server_url, monkeypatch)

    at.text_input(key="query_input").set_value("compare the stocks between the mahindra and reliance")
    at.button(key="ask_button").click().run(timeout=30)

    assert not at.exception
    result = at.session_state["query_result"]
    assert result["intent"]["mode"] == "compare"
    assert result["result"]["winner"] in {"M&M.NS", "RELIANCE.NS"}


def test_query_unknown_shows_error_not_crash(live_server_url, monkeypatch):
    at = _fresh_app(live_server_url, monkeypatch)

    at.text_input(key="query_input").set_value("what is the weather today")
    at.button(key="ask_button").click().run(timeout=30)

    assert not at.exception
    assert at.session_state["query_error"] is not None
    assert at.session_state["query_result"] is None


def test_add_holding_then_analyze_portfolio(live_server_url, monkeypatch):
    at = _fresh_app(live_server_url, monkeypatch)

    at.text_input(key="new_holding_name").set_value("infosys")
    at.button(key="add_holding_submit").click().run(timeout=30)
    assert not at.exception

    at.button(key="analyze_portfolio_button").click().run(timeout=30)

    assert not at.exception
    assert "portfolio_result" in at.session_state
    report = at.session_state["portfolio_result"]
    assert report["mode"] == "portfolio"
    assert "INFY.NS" in report["tickers"]


def test_compare_form_golden_path(live_server_url, monkeypatch):
    at = _fresh_app(live_server_url, monkeypatch)

    at.text_input(key="compare_a").set_value("mahindra")
    at.text_input(key="compare_b").set_value("reliance")
    at.button(key="compare_button").click().run(timeout=30)

    assert not at.exception
    report = at.session_state["compare_result"]
    assert report["mode"] == "compare"
