import streamlit as st

from phase7.api_client import ApiClient, ApiError
from phase7.portfolio_store import add_holding, load_portfolio, remove_holding

st.set_page_config(page_title="Market Analyst", page_icon="📈", layout="wide")


def get_client():
    if "api_client" not in st.session_state:
        st.session_state.api_client = ApiClient()
    return st.session_state.api_client


def _as_table_rows(d):
    # st.table() converts dicts to a DataFrame via PyArrow, which errors on
    # a column mixing types (e.g. floats and the string "increasing") —
    # stringify every value so the resulting column is uniformly text.
    return [{"metric": k, "value": "-" if v is None else str(v)} for k, v in d.items()]


def render_agent_breakdown(agent_results):
    technical = agent_results.get("technical", {})
    sentiment = agent_results.get("sentiment", {})
    financial = agent_results.get("financial", {})

    tab_t, tab_s, tab_f = st.tabs(["Technical", "Sentiment", "Financial"])

    with tab_t:
        if technical.get("status") == "error":
            st.warning(f"Technical analysis unavailable: {technical.get('error')}")
        else:
            st.write(f"Verdict: **{technical.get('verdict')}** (confidence {technical.get('confidence')})")
            st.table(_as_table_rows(technical.get("indicators", {})))
            for reason in technical.get("reasoning", []):
                st.caption(f"- {reason}")

    with tab_s:
        if sentiment.get("status") == "error":
            st.warning(f"Sentiment analysis unavailable: {sentiment.get('error')}")
        else:
            st.write(f"Verdict: **{sentiment.get('verdict')}** (confidence {sentiment.get('confidence')})")
            for headline in sentiment.get("headlines", [])[:5]:
                st.markdown(f"- [{headline['title']}]({headline['url']})")

    with tab_f:
        if financial.get("status") == "error":
            st.warning(f"Financial analysis unavailable: {financial.get('error')}")
        else:
            st.write(f"Verdict: **{financial.get('verdict')}** (confidence {financial.get('confidence')})")
            st.table(_as_table_rows(financial.get("ratios", {})))
            for reason in financial.get("reasoning", []):
                st.caption(f"- {reason}")


def render_ticker_synthesis(synthesis):
    col1, col2 = st.columns(2)
    col1.metric("Verdict", synthesis["verdict"].upper())
    col2.metric("Confidence", f"{synthesis['confidence']:.0%}")

    if synthesis.get("notes"):
        for note in synthesis["notes"]:
            st.info(note)

    st.write("**Reasoning**")
    for line in synthesis.get("reasoning", []):
        st.caption(f"- {line}")

    render_agent_breakdown(synthesis.get("agent_results", {}))


def render_portfolio_report(report):
    col1, col2, col3 = st.columns(3)
    col1.metric("Overall verdict", report["overall_verdict"].upper())
    col2.metric("Best performer", report["best_performer"])
    col3.metric("Worst performer", report["worst_performer"])

    if report["risk_flags"]:
        st.warning(f"Risk flags: {', '.join(report['risk_flags'])}")

    for ticker, synthesis in report["per_ticker"].items():
        with st.expander(f"{ticker} — {synthesis['verdict']}"):
            render_ticker_synthesis(synthesis)


def render_compare_report(report):
    st.success(f"Winner: **{report['winner']}**")
    st.write(report["rationale"])
    st.table([
        {"ticker": row["ticker"], "verdict": row["verdict"], "score": row["score"]}
        for row in report["ranking"]
    ])

    for ticker, synthesis in report["per_ticker"].items():
        with st.expander(f"{ticker} — {synthesis['verdict']}"):
            render_ticker_synthesis(synthesis)


def render_query_result(payload):
    intent = payload["intent"]
    result = payload["result"]

    st.caption(f"Understood as: **{intent['mode']}** — tickers: {', '.join(intent['tickers'])}")

    if intent["mode"] == "single":
        render_ticker_synthesis(result)
    elif intent["mode"] == "portfolio":
        render_portfolio_report(result)
    else:
        render_compare_report(result)


st.title("📈 Market Analyst")

st.header("Ask a question")
query_text = st.text_input(
    "e.g. \"how is infosys doing\", \"compare mahindra and reliance\"",
    key="query_input",
)
if st.button("Ask", key="ask_button") and query_text:
    client = get_client()
    try:
        st.session_state.query_result = client.query(query_text)
        st.session_state.query_error = None
    except ApiError as exc:
        st.session_state.query_result = None
        st.session_state.query_error = str(exc)

if st.session_state.get("query_error"):
    st.error(st.session_state.query_error)
if st.session_state.get("query_result"):
    render_query_result(st.session_state.query_result)

st.divider()

st.header("My Portfolio")
holdings = load_portfolio()

with st.form("add_holding_form", clear_on_submit=True):
    new_name = st.text_input("Company name or ticker", key="new_holding_name")
    new_qty = st.number_input("Quantity (optional)", min_value=0.0, value=0.0, step=1.0, key="new_holding_qty")
    new_price = st.number_input("Buy price (optional)", min_value=0.0, value=0.0, step=1.0, key="new_holding_price")
    submitted = st.form_submit_button("Add to portfolio", key="add_holding_submit")
    if submitted and new_name:
        holdings = add_holding(new_name, qty=new_qty or None, buy_price=new_price or None)
        st.rerun()

if holdings:
    for h in holdings:
        col1, col2 = st.columns([4, 1])
        col1.write(f"**{h['ticker']}** ({h['name']}) — qty: {h.get('qty') or '-'}, buy price: {h.get('buy_price') or '-'}")
        if col2.button("Remove", key=f"remove_{h['ticker']}"):
            remove_holding(h["ticker"])
            st.rerun()

    if st.button("Analyze Portfolio", key="analyze_portfolio_button"):
        client = get_client()
        try:
            st.session_state.portfolio_result = client.portfolio_analyze([h["ticker"] for h in holdings])
            st.session_state.portfolio_error = None
        except ApiError as exc:
            st.session_state.portfolio_result = None
            st.session_state.portfolio_error = str(exc)
else:
    st.caption("No holdings yet — add one above.")

if st.session_state.get("portfolio_error"):
    st.error(st.session_state.portfolio_error)
if st.session_state.get("portfolio_result"):
    render_portfolio_report(st.session_state.portfolio_result)

st.divider()

st.header("Compare Two Stocks")
col_a, col_b = st.columns(2)
ticker_a = col_a.text_input("Stock A", key="compare_a")
ticker_b = col_b.text_input("Stock B", key="compare_b")
if st.button("Compare", key="compare_button") and ticker_a and ticker_b:
    client = get_client()
    try:
        st.session_state.compare_result = client.compare([ticker_a, ticker_b])
        st.session_state.compare_error = None
    except ApiError as exc:
        st.session_state.compare_result = None
        st.session_state.compare_error = str(exc)

if st.session_state.get("compare_error"):
    st.error(st.session_state.compare_error)
if st.session_state.get("compare_result"):
    render_compare_report(st.session_state.compare_result)
