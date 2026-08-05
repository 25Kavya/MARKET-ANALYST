import json
from pathlib import Path

from phase1.data.tickers import TickerResolutionError, resolve_ticker
from phase1.logging_config import get_logger

logger = get_logger(__name__)

DEFAULT_PATH = Path(__file__).resolve().parent / "data" / "portfolio.json"


def load_portfolio(path=DEFAULT_PATH):
    path = Path(path)
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_portfolio(holdings, path=DEFAULT_PATH):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(holdings, f, indent=2)


def add_holding(name, qty=None, buy_price=None, path=DEFAULT_PATH):
    ticker = resolve_ticker(name)
    holdings = load_portfolio(path)

    holdings = [h for h in holdings if h["ticker"] != ticker]
    holdings.append({
        "ticker": ticker,
        "name": name.strip(),
        "qty": qty,
        "buy_price": buy_price,
    })

    save_portfolio(holdings, path)
    logger.info("portfolio_store.add_holding ticker=%s qty=%s buy_price=%s", ticker, qty, buy_price)
    return holdings


def remove_holding(name_or_ticker, path=DEFAULT_PATH):
    try:
        ticker = resolve_ticker(name_or_ticker)
    except TickerResolutionError:
        ticker = name_or_ticker.strip().upper()

    holdings = load_portfolio(path)
    remaining = [h for h in holdings if h["ticker"] != ticker]

    save_portfolio(remaining, path)
    logger.info("portfolio_store.remove_holding ticker=%s removed=%s", ticker, len(holdings) != len(remaining))
    return remaining
