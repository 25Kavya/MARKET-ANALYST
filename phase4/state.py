import operator
from typing import Annotated, TypedDict


class AgentResult(TypedDict, total=False):
    agent: str          # "technical" | "sentiment" | "financial"
    status: str         # "ok" | "error"
    verdict: str        # "bullish" | "bearish" | "neutral" (present when status == "ok")
    confidence: float
    reasoning: list
    error: str           # present when status == "error"


class Synthesis(TypedDict, total=False):
    ticker: str
    verdict: str
    confidence: float
    contributing_agents: list
    notes: list
    reasoning: list
    agent_results: dict


class GraphState(TypedDict):
    ticker: str
    # Each of the 3 agent nodes runs in its own parallel branch (via Send) and
    # appends one AgentResult here; operator.add concatenates the lists from
    # all branches once they all finish, so no branch ever overwrites another.
    agent_results: Annotated[list, operator.add]
    synthesis: Synthesis
