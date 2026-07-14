"""
portfolio_tracker.py — Analyzes the user's specific holdings.
Tracks P&L, today's performance, and runs the 7-day trend analysis.
"""
import json
import os
import logging
from typing import Dict, List, Any
import pandas as pd
from src.data.historical_fetcher import fetch_7d_history, get_7d_trend_summary

logger = logging.getLogger(__name__)

def load_portfolio(filepath: str = "portfolio.json") -> Dict[str, Dict[str, float]]:
    if not os.path.exists(filepath):
        logger.warning("Portfolio file %s not found.", filepath)
        return {}
        
    try:
        with open(filepath, "r") as f:
            return json.load(f)
    except Exception as exc:
        logger.error("Failed to parse portfolio: %s", exc)
        return {}

def analyze_portfolio(eod_df: pd.DataFrame, portfolio: Dict[str, Dict[str, float]]) -> List[Dict[str, Any]]:
    """
    Merges today's bhavcopy data with the user's portfolio and fetches 7-day trend.
    Returns a list of dicts with full analysis per stock.
    """
    if not portfolio or eod_df.empty:
        return []
        
    symbols = list(portfolio.keys())
    # We fetch historical data for their portfolio
    hist_data = fetch_7d_history(symbols)
    
    results = []
    
    for symbol, details in portfolio.items():
        shares = details.get("shares", 0)
        avg_price = details.get("avg_price", 0.0)
        
        # Get today's snapshot from EOD df
        today_row = eod_df[eod_df["SYMBOL"] == symbol]
        if today_row.empty:
            logger.warning("Portfolio stock %s not found in today's EOD data.", symbol)
            continue
            
        today_data = today_row.iloc[0]
        close = today_data["CLOSE"]
        pct_change = today_data["PCT_CHANGE"]
        delivery_pct = today_data.get("DELIVERY_PCT", float("nan"))
        
        # Calculations
        current_value = shares * close
        invested_value = shares * avg_price
        unrealized_pl = current_value - invested_value
        unrealized_pct = (unrealized_pl / invested_value * 100) if invested_value > 0 else 0
        
        # Trend
        df_hist = hist_data.get(symbol)
        trend = get_7d_trend_summary(df_hist)
        
        results.append({
            "SYMBOL": symbol,
            "shares": shares,
            "avg_price": avg_price,
            "close": close,
            "pct_change": pct_change,
            "unrealized_pct": unrealized_pct,
            "unrealized_pl": unrealized_pl,
            "delivery_pct": delivery_pct,
            "trend": trend
        })
        
    return results
