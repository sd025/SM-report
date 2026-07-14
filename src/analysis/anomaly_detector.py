"""
anomaly_detector.py — Flags unusual market activity.
- Delivery % spikes
- Volume anomalies (requires 30-day avg, but for now we'll do basic relative if available, 
  or just flag absolute extreme delivery).
- 52-week high/low proximity.
"""

import logging
from typing import Dict, List

import pandas as pd
from config import DELIVERY_HIGH_PCT, DELIVERY_EXTREME_PCT, PCT_CHANGE_SIGNIFICANT

logger = logging.getLogger(__name__)


def extract_top_movers(
    df: pd.DataFrame, 
    segment: str, 
    direction: str = "gainers", 
    n: int = 5
) -> pd.DataFrame:
    """
    Extract top N gainers or losers for a specific market cap segment.
    Filters out penny stocks (< Rs 20) to reduce noise.
    """
    if df.empty:
        return pd.DataFrame()

    filtered = df[(df["MARKET_CAP_SEGMENT"] == segment) & (df["CLOSE"] >= 20.0)].copy()
    
    if filtered.empty:
        return pd.DataFrame()

    if direction == "gainers":
        return filtered.sort_values(by="PCT_CHANGE", ascending=False).head(n)
    else:  # losers
        return filtered.sort_values(by="PCT_CHANGE", ascending=True).head(n)


def detect_delivery_anomalies(df: pd.DataFrame) -> pd.DataFrame:
    """
    Find stocks with unusually high delivery percentages AND significant price movement.
    This is often a sign of institutional accumulation (if price up) or distribution (if down).
    """
    if "DELIVERY_PCT" not in df.columns or df.empty:
        return pd.DataFrame()

    # Filter out very small cap/micro cap noise
    liquid = df[df["MARKET_CAP_SEGMENT"].isin(["Large", "Mid", "Small"])].copy()

    # Criteria: High delivery AND moved > PCT_CHANGE_SIGNIFICANT (up or down)
    anomalies = liquid[
        (liquid["DELIVERY_PCT"] >= DELIVERY_HIGH_PCT) & 
        (liquid["PCT_CHANGE"].abs() >= PCT_CHANGE_SIGNIFICANT)
    ].copy()

    return anomalies.sort_values(by="DELIVERY_PCT", ascending=False)
