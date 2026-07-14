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


def extract_momentum_breakouts(df: pd.DataFrame, n: int = 3) -> pd.DataFrame:
    """
    Finds Mid/Small cap stocks breaking out with huge institutional delivery.
    Criteria: Delivery > 65%, Price > +2%.
    """
    if "DELIVERY_PCT" not in df.columns or df.empty:
        return pd.DataFrame()

    candidates = df[
        (df["MARKET_CAP_SEGMENT"].isin(["Mid", "Small"])) & 
        (df["DELIVERY_PCT"] >= 65.0) & 
        (df["PCT_CHANGE"] >= 2.0) &
        (df["CLOSE"] >= 50.0) # Filter penny stocks
    ].copy()

    # Sort by delivery % combined with price momentum
    return candidates.sort_values(by=["DELIVERY_PCT", "PCT_CHANGE"], ascending=[False, False]).head(n)


def extract_value_reversals(df: pd.DataFrame, n: int = 3) -> pd.DataFrame:
    """
    Finds Large cap stocks showing sudden institutional accumulation.
    Criteria: Large Cap, Delivery > 70%, Price green today (but likely beaten down macro).
    """
    if "DELIVERY_PCT" not in df.columns or df.empty:
        return pd.DataFrame()

    candidates = df[
        (df["MARKET_CAP_SEGMENT"] == "Large") & 
        (df["DELIVERY_PCT"] >= 70.0) & 
        (df["PCT_CHANGE"] > 0.0)
    ].copy()

    return candidates.sort_values(by="DELIVERY_PCT", ascending=False).head(n)
