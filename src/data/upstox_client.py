"""
upstox_client.py — Upstox API v2 wrapper for market data (read-only).
Covers: NSE/BSE index quotes, stock OHLC, previous close.
No order placement — static IP requirement does NOT apply.
"""

import logging
import os
import time
from typing import Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

UPSTOX_BASE = "https://api.upstox.com/v2"

# Instrument keys (| delimited in query; NSE returns with : in response key)
NSE_INDICES: Dict[str, str] = {
    "Nifty 50":           "NSE_INDEX|Nifty 50",
    "Sensex":             "BSE_INDEX|SENSEX",
    "Bank Nifty":         "NSE_INDEX|Nifty Bank",
    "Nifty IT":           "NSE_INDEX|Nifty IT",
    "Nifty Pharma":       "NSE_INDEX|Nifty Pharma",
    "Nifty Auto":         "NSE_INDEX|Nifty Auto",
    "Nifty Metal":        "NSE_INDEX|Nifty Metal",
    "Nifty Realty":       "NSE_INDEX|Nifty Realty",
    "Nifty FMCG":         "NSE_INDEX|Nifty FMCG",
    "Nifty Energy":       "NSE_INDEX|Nifty Energy",
    "Nifty Midcap 150":   "NSE_INDEX|NIFTY MIDCAP 150",
    "Nifty Smallcap 250": "NSE_INDEX|NIFTY SMLCAP 250",
    "India VIX":          "NSE_INDEX|India VIX",
}


class UpstoxClient:
    """Thin, read-only Upstox API v2 client."""

    def __init__(self, access_token: Optional[str] = None):
        token = access_token or os.environ.get("UPSTOX_ACCESS_TOKEN", "")
        if not token:
            raise EnvironmentError("UPSTOX_ACCESS_TOKEN env var not set.")
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        }

    # ── Public Methods ─────────────────────────────────────────────────────

    def get_index_quotes(self) -> Dict[str, Dict]:
        """
        Fetch current OHLC + prev_close for all tracked indices.
        Returns dict keyed by friendly name (e.g. "Nifty 50").

        If the market hasn't opened yet (morning call), the API returns
        the previous trading session's data — which is exactly what we want.
        """
        keys = ",".join(NSE_INDICES.values())
        raw = self._ohlc_call(keys)
        result: Dict[str, Dict] = {}
        for name, instrument_key in NSE_INDICES.items():
            # Upstox returns key with ':' instead of '|'
            response_key = instrument_key.replace("|", ":")
            if response_key not in raw:
                logger.debug("Missing index in response: %s", name)
                continue
            d = raw[response_key]
            ohlc = d.get("ohlc", {})
            close = ohlc.get("close") or ohlc.get("last_price") or 0
            prev  = d.get("prev_close_price") or 0
            pct   = round((close - prev) / prev * 100, 2) if prev else 0.0
            result[name] = {
                "open":       ohlc.get("open"),
                "high":       ohlc.get("high"),
                "low":        ohlc.get("low"),
                "close":      close,
                "prev_close": prev,
                "change":     round(close - prev, 2),
                "pct_change": pct,
            }
        return result

    def get_historical_candles(
        self,
        instrument_key: str,
        interval: str = "day",
        from_date: str = "",
        to_date: str = "",
    ) -> List[List]:
        """
        Fetch OHLCV candles. interval options: day, week, month, 1minute, 30minute.
        Dates in YYYY-MM-DD format.
        Returns list of [timestamp, open, high, low, close, volume, oi].
        """
        url = (
            f"{UPSTOX_BASE}/historical-candle/"
            f"{requests.utils.quote(instrument_key, safe='')}/"
            f"{interval}/{to_date}/{from_date}"
        )
        try:
            resp = requests.get(url, headers=self._headers, timeout=15)
            resp.raise_for_status()
            return resp.json().get("data", {}).get("candles", [])
        except requests.RequestException as exc:
            logger.error("Historical candle error for %s: %s", instrument_key, exc)
            return []

    # ── Private Helpers ────────────────────────────────────────────────────

    def _ohlc_call(self, instrument_keys: str) -> Dict:
        """Raw OHLC market quote call."""
        url = f"{UPSTOX_BASE}/market-quote/ohlc"
        try:
            resp = requests.get(
                url,
                headers=self._headers,
                params={"instrument_key": instrument_keys},
                timeout=15,
            )
            resp.raise_for_status()
            return resp.json().get("data", {})
        except requests.RequestException as exc:
            logger.error("Upstox OHLC call failed: %s", exc)
            return {}
