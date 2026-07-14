"""
global_markets.py — Fetches overnight global market data via yfinance.
No API key needed. Used by the morning brief to show what happened globally
while Indian markets were closed.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

import yfinance as yf

logger = logging.getLogger(__name__)

# yfinance ticker → display name
GLOBAL_TICKERS: Dict[str, str] = {
    "^GSPC":    "S&P 500",
    "^IXIC":    "Nasdaq",
    "^DJI":     "Dow Jones",
    "^N225":    "Nikkei 225",
    "USDINR=X": "USD/INR",
    "BZ=F":     "Brent Crude",
    "GC=F":     "Gold",
}


def _fetch_ticker(symbol: str) -> Optional[Dict]:
    """Return latest OHLC + pct_change for a single yfinance ticker."""
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="2d", auto_adjust=True)
        if hist.empty or len(hist) < 1:
            return None

        latest = hist.iloc[-1]
        prev   = hist.iloc[-2] if len(hist) >= 2 else None

        close     = round(float(latest["Close"]), 4)
        prev_close = round(float(prev["Close"]), 4) if prev is not None else close
        pct_change = round((close - prev_close) / prev_close * 100, 2) if prev_close else 0.0

        return {
            "close":      close,
            "prev_close": prev_close,
            "pct_change": pct_change,
            "date":       str(latest.name.date()),
        }
    except Exception as exc:
        logger.warning("yfinance error for %s: %s", symbol, exc)
        return None


def get_global_snapshot() -> Dict[str, Optional[Dict]]:
    """
    Fetch all global market tickers and return a dict keyed by display name.
    Example output:
        {
          "S&P 500": {"close": 5480.0, "pct_change": -0.41, ...},
          "Brent Crude": {"close": 78.2, "pct_change": 0.12, ...},
          ...
        }
    """
    result: Dict[str, Optional[Dict]] = {}
    for symbol, name in GLOBAL_TICKERS.items():
        data = _fetch_ticker(symbol)
        result[name] = data
        if data:
            logger.debug("%-15s close=%-10s pct=%+.2f%%", name, data["close"], data["pct_change"])
        else:
            logger.warning("%-15s — no data", name)
    return result
