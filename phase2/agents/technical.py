import time

from phase1.data.market import get_history
from phase1.logging_config import get_logger

logger = get_logger(__name__)

_DEFAULT_PERIOD = "6mo"
_DEFAULT_INTERVAL = "1d"


def _rsi(close, period=14):
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def _macd(close, fast=12, slow=26, signal=9):
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    return macd_line, signal_line


def _bollinger_bands(close, period=20, num_std=2):
    sma = close.rolling(period).mean()
    std = close.rolling(period).std()
    return sma + num_std * std, sma - num_std * std


def _volume_trend(volume):
    if len(volume) < 25:
        return "unknown"
    recent = volume.tail(5).mean()
    prior = volume.iloc[-25:-5].mean()
    if prior == 0:
        return "unknown"
    if recent > prior * 1.1:
        return "increasing"
    if recent < prior * 0.9:
        return "decreasing"
    return "flat"


def _round(value, digits=2):
    if value is None:
        return None
    try:
        if value != value:  # NaN check without importing math/numpy here
            return None
    except TypeError:
        return None
    return round(float(value), digits)


def analyze_technical(ticker, period=_DEFAULT_PERIOD, interval=_DEFAULT_INTERVAL):
    start = time.monotonic()
    logger.info("technical.analyze_technical request ticker=%s period=%s", ticker, period)

    df = get_history(ticker, period=period, interval=interval)

    close = df["Close"]
    sma20 = close.rolling(20).mean()
    sma50 = close.rolling(50).mean()
    rsi14 = _rsi(close, 14)
    macd_line, macd_signal = _macd(close)
    bb_upper, bb_lower = _bollinger_bands(close)
    volume_trend = _volume_trend(df["Volume"])
    support = _round(df["Low"].tail(20).min())
    resistance = _round(df["High"].tail(20).max())

    latest_close = float(close.iloc[-1])
    sma20_last = sma20.iloc[-1]
    sma50_last = sma50.iloc[-1]
    rsi_last = rsi14.iloc[-1]
    macd_last = macd_line.iloc[-1]
    macd_signal_last = macd_signal.iloc[-1]

    votes = []

    if sma50_last == sma50_last:  # not NaN -> enough history for 50-day SMA
        if latest_close > sma20_last > sma50_last:
            votes.append(("trend", "bullish", "price above SMA20 above SMA50"))
        elif latest_close < sma20_last < sma50_last:
            votes.append(("trend", "bearish", "price below SMA20 below SMA50"))
        else:
            votes.append(("trend", "neutral", "no clear SMA20/SMA50 alignment"))
    else:
        votes.append(("trend", "neutral", "insufficient history for 50-day SMA"))

    if macd_last > macd_signal_last:
        votes.append(("macd", "bullish", "MACD above signal line"))
    elif macd_last < macd_signal_last:
        votes.append(("macd", "bearish", "MACD below signal line"))
    else:
        votes.append(("macd", "neutral", "MACD equal to signal line"))

    if rsi_last >= 70:
        votes.append(("rsi", "bearish", f"RSI overbought at {rsi_last:.1f}"))
    elif rsi_last <= 30:
        votes.append(("rsi", "bullish", f"RSI oversold at {rsi_last:.1f}"))
    else:
        votes.append(("rsi", "neutral", f"RSI neutral at {rsi_last:.1f}"))

    counts = {"bullish": 0, "bearish": 0, "neutral": 0}
    for _, label, _ in votes:
        counts[label] += 1

    verdict = max(counts, key=counts.get)
    confidence = round(counts[verdict] / len(votes), 2)
    reasoning = [reason for _, _, reason in votes]

    result = {
        "ticker": ticker,
        "as_of": str(df.index[-1].date()),
        "price": _round(latest_close),
        "indicators": {
            "sma20": _round(sma20_last),
            "sma50": _round(sma50_last),
            "rsi14": _round(rsi_last),
            "macd": _round(macd_last),
            "macd_signal": _round(macd_signal_last),
            "bollinger_upper": _round(bb_upper.iloc[-1]),
            "bollinger_lower": _round(bb_lower.iloc[-1]),
            "volume_trend": volume_trend,
            "support": support,
            "resistance": resistance,
        },
        "verdict": verdict,
        "confidence": confidence,
        "reasoning": reasoning,
    }

    elapsed = time.monotonic() - start
    logger.info(
        "technical.analyze_technical ok ticker=%s verdict=%s confidence=%.2f elapsed=%.2fs",
        ticker, verdict, confidence, elapsed,
    )
    return result
