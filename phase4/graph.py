from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from phase4.nodes import financial_node, sentiment_node, synthesizer, technical_node
from phase4.state import GraphState

_AGENT_NODES = ["technical_node", "sentiment_node", "financial_node"]


def dispatch(state):
    ticker = state["ticker"]
    return [Send(node, {"ticker": ticker}) for node in _AGENT_NODES]


def build_graph():
    graph = StateGraph(GraphState)

    graph.add_node("technical_node", technical_node)
    graph.add_node("sentiment_node", sentiment_node)
    graph.add_node("financial_node", financial_node)
    graph.add_node("synthesizer", synthesizer)

    graph.add_conditional_edges(START, dispatch, _AGENT_NODES)
    for node in _AGENT_NODES:
        graph.add_edge(node, "synthesizer")
    graph.add_edge("synthesizer", END)

    return graph.compile()


def analyze_ticker(ticker):
    app = build_graph()
    final_state = app.invoke({"ticker": ticker, "agent_results": []})
    return final_state["synthesis"]
