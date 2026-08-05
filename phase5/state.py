import operator
from typing import Annotated, Literal, TypedDict


class MultiTickerState(TypedDict):
    tickers: list
    mode: Literal["portfolio", "compare"]
    # Each ticker is dispatched to its own branch (which internally fans out
    # to the 3 agents for that ticker) — operator.add concatenates the
    # per-ticker syntheses from all branches once they all finish.
    ticker_syntheses: Annotated[list, operator.add]
    report: dict
