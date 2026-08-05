from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from phase5.nodes import aggregator, ticker_node
from phase5.state import MultiTickerState


def dispatch_tickers(state):
    return [Send("ticker_node", {"ticker": ticker}) for ticker in state["tickers"]]


def build_graph():
    graph = StateGraph(MultiTickerState)

    graph.add_node("ticker_node", ticker_node)
    graph.add_node("aggregator", aggregator)

    graph.add_conditional_edges(START, dispatch_tickers, ["ticker_node"])
    graph.add_edge("ticker_node", "aggregator")
    graph.add_edge("aggregator", END)

    return graph.compile()


def analyze_portfolio(tickers):
    app = build_graph()
    final_state = app.invoke({"tickers": tickers, "mode": "portfolio", "ticker_syntheses": []})
    return final_state["report"]


def compare_tickers(tickers):
    app = build_graph()
    final_state = app.invoke({"tickers": tickers, "mode": "compare", "ticker_syntheses": []})
    return final_state["report"]
