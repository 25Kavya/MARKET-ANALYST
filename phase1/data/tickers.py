import csv
import difflib
import re
from pathlib import Path

from phase1.logging_config import get_logger

logger = get_logger(__name__)

_NSE_EQUITY_CSV_PATH = Path(__file__).resolve().parent / "nse_equity_list.csv"
_NAME_SUFFIXES = ["private limited", "pvt limited", "pvt ltd", "limited", "ltd."]

# Hand-curated colloquial aliases a user would actually type — the official
# NSE-registered name often doesn't match how people refer to a company
# ("mahindra" vs "Mahindra & Mahindra Limited", "reliance" vs "Reliance
# Industries Limited"). Extend this table for any company whose common name
# isn't already reachable through nse_equity_list.csv below. Curated entries
# always take priority over anything derived from the CSV.
_TICKER_ALIASES = {
    # TATAMOTORS.NS was delisted after the 2025 demerger; TMPV.NS (Tata Motors
    # Passenger Vehicles) is the Yahoo Finance successor most users mean.
    "TMPV.NS": ["tata motors", "tatamotors", "tata motor"],
    "INFY.NS": ["infosys", "infy"],
    # ETERNAL.NS is Zomato's official listed name/symbol after its 2024
    # corporate rebrand — the brand name doesn't appear in NSE's official
    # records at all, so it can't be derived from nse_equity_list.csv.
    "ETERNAL.NS": ["zomato"],
    "CUPID.NS": ["cupid", "cupid ltd", "cupid limited"],
    "M&M.NS": ["mahindra", "mahindra and mahindra", "m&m", "mahindra & mahindra"],
    "RELIANCE.NS": ["reliance", "reliance industries", "ril"],
    "TCS.NS": ["tcs", "tata consultancy services", "tata consultancy"],
    "HDFCBANK.NS": ["hdfc bank", "hdfcbank"],
    "ICICIBANK.NS": ["icici bank", "icicibank"],
    "SBIN.NS": ["sbi", "state bank of india"],
    "WIPRO.NS": ["wipro"],
    "ITC.NS": ["itc"],
    "BAJFINANCE.NS": ["bajaj finance", "bajfinance"],
    "HINDUNILVR.NS": ["hindustan unilever", "hul", "hindunilvr"],
    "LT.NS": ["larsen and toubro", "l&t", "larsen & toubro"],
    "MARUTI.NS": ["maruti suzuki", "maruti"],
    "AXISBANK.NS": ["axis bank", "axisbank"],
    "SUNPHARMA.NS": ["sun pharma", "sun pharmaceutical"],
    "TATASTEEL.NS": ["tata steel", "tatasteel"],
    "ADANIENT.NS": ["adani enterprises", "adanient"],
    "ONGC.NS": ["ongc", "oil and natural gas corporation"],
}

_CURATED_ALIAS_TO_TICKER = {
    alias.lower(): ticker
    for ticker, aliases in _TICKER_ALIASES.items()
    for alias in aliases + [ticker.replace(".NS", "")]
}


def _strip_name_suffix(name):
    for suffix in _NAME_SUFFIXES:
        if name.endswith(suffix):
            return name[: -len(suffix)].strip()
    return name


def _load_csv_aliases(path):
    """Bundled snapshot of NSE's official equity list (~2,400 companies),
    fetched from https://archives.nseindia.com/content/equities/EQUITY_L.csv
    — refresh this file periodically the same way to pick up new listings,
    renames, and delistings. Covers any company by its official registered
    name or ticker symbol; it does NOT cover pure brand/colloquial names that
    differ from both (e.g. "Zomato" is officially "Eternal Limited",
    symbol ETERNAL) — those still need a hand-curated alias above."""
    aliases = {}
    if not path.exists():
        logger.warning("tickers._load_csv_aliases file not found path=%s", path)
        return aliases

    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            symbol = row.get("SYMBOL", "").strip()
            name = row.get("NAME OF COMPANY", "").strip()
            if not symbol or not name:
                continue

            ticker = f"{symbol}.NS"
            name_lower = name.lower()
            short_name = _strip_name_suffix(name_lower)

            aliases.setdefault(symbol.lower(), ticker)
            aliases.setdefault(name_lower, ticker)
            if short_name and short_name != name_lower:
                aliases.setdefault(short_name, ticker)

    return aliases


_CSV_ALIAS_TO_TICKER = _load_csv_aliases(_NSE_EQUITY_CSV_PATH)

# CSV-derived aliases first, then curated aliases layered on top so a
# curated colloquial name always wins over anything derived from the CSV.
_ALIAS_TO_TICKER = {**_CSV_ALIAS_TO_TICKER, **_CURATED_ALIAS_TO_TICKER}

# CSV-derived symbols below this length (e.g. "TI" = Tilaknagar Industries,
# bare "lt" = Larsen & Toubro) are fine for exact-match/fuzzy-match lookups
# but are excluded from free-text scanning in find_mentioned_tickers — a
# short alias would match as a false positive inside ordinary words (e.g.
# "TI" inside "position", "lt" inside "wealth"). Hand-curated aliases (e.g.
# "tcs", "sbi", "itc", "ril") are exempt from this filter — they were
# chosen deliberately and are already known-safe, some already 3 letters.
_MIN_FREE_TEXT_ALIAS_LEN = 4
_FREE_TEXT_ALIASES = [
    alias for alias in _ALIAS_TO_TICKER
    if alias in _CURATED_ALIAS_TO_TICKER or len(alias) >= _MIN_FREE_TEXT_ALIAS_LEN
]


class TickerResolutionError(Exception):
    pass


def resolve_ticker(name, fuzzy_cutoff=0.72):
    if not name or not name.strip():
        raise TickerResolutionError("empty company name provided")

    query = name.strip().lower()
    logger.info("tickers.resolve_ticker request name=%r", name)

    if query in _ALIAS_TO_TICKER:
        ticker = _ALIAS_TO_TICKER[query]
        logger.info("tickers.resolve_ticker exact match name=%r ticker=%s", name, ticker)
        return ticker

    upper = name.strip().upper()
    ticker_shaped = bool(re.fullmatch(r"[A-Z0-9&]+(\.NS)?", upper))

    # Already fully-qualified (e.g. "INFY.NS") — unambiguous, pass through
    # immediately rather than risking a fuzzy match against it.
    if ticker_shaped and upper.endswith(".NS"):
        logger.info("tickers.resolve_ticker passthrough (already qualified) name=%r ticker=%s", name, upper)
        return upper

    # Try correcting typos of a *known* company name before assuming a bare
    # word is already a raw ticker (e.g. "infosis" -> "infosys", not a
    # literal ticker "INFOSIS.NS").
    matches = difflib.get_close_matches(query, _ALIAS_TO_TICKER.keys(), n=1, cutoff=fuzzy_cutoff)
    if matches:
        ticker = _ALIAS_TO_TICKER[matches[0]]
        logger.info(
            "tickers.resolve_ticker fuzzy match name=%r matched_alias=%r ticker=%s",
            name, matches[0], ticker,
        )
        return ticker

    # Not a known company and not a close typo of one — if it's still
    # ticker-shaped (e.g. "HCLTECH"), assume it's a raw symbol we simply
    # haven't curated an alias for. Whether it actually exists on the
    # exchange is the data layer's job (market.py raises MarketDataError for
    # real), not this function's.
    if ticker_shaped:
        candidate = f"{upper}.NS"
        logger.info("tickers.resolve_ticker passthrough (ticker-shaped) name=%r ticker=%s", name, candidate)
        return candidate

    logger.warning("tickers.resolve_ticker no match name=%r", name)
    raise TickerResolutionError(f"could not resolve a ticker for {name!r}")


def find_mentioned_tickers(text):
    """Scan free text for known company aliases and return the resolved
    tickers mentioned, deduplicated, ordered by first appearance."""
    if not text:
        return []

    lowered = text.lower()
    consumed = [False] * len(lowered)
    matches = []  # (start_index, ticker)

    # Longest aliases first so "tata motors" is matched whole rather than a
    # shorter, unrelated alias matching inside it first.
    for alias in sorted(_FREE_TEXT_ALIASES, key=len, reverse=True):
        start = 0
        while True:
            idx = lowered.find(alias, start)
            if idx == -1:
                break
            span = range(idx, idx + len(alias))
            if not any(consumed[i] for i in span):
                for i in span:
                    consumed[i] = True
                matches.append((idx, _ALIAS_TO_TICKER[alias]))
            start = idx + len(alias)

    matches.sort(key=lambda m: m[0])
    seen = set()
    result = []
    for _, ticker in matches:
        if ticker not in seen:
            seen.add(ticker)
            result.append(ticker)
    return result
