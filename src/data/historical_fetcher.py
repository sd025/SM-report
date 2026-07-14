"""
historical_fetcher.py — Fetches a 7-day rolling window of historical data for stocks.
Uses yfinance (free, fast, no auth) to get a 7-day context for the user's portfolio
and any anomaly candidates.
"""
import yfinance as yf
import pandas as pd
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

def fetch_7d_history(symbols: List[str]) -> Dict[str, Optional[pd.DataFrame]]:
    """
    Fetches 7 days of OHLCV data for a list of NSE symbols.
    Appends '.NS' to the symbols for Yahoo Finance.
    Returns a dictionary mapping the original symbol to its historical DataFrame.
    """
    if not symbols:
        return {}
        
    # Append .NS for NSE stocks
    yf_tickers = [f"{sym}.NS" for sym in symbols]
    
    logger.info("Fetching 7-day history for %d symbols via yfinance...", len(symbols))
    
    # Download in bulk for speed
    try:
        # interval="1d", period="7d" fetches the last 7 trading days
        data = yf.download(yf_tickers, period="7d", interval="1d", group_by="ticker", auto_adjust=True, progress=False)
    except Exception as exc:
        logger.error("Failed to fetch bulk history from yfinance: %s", exc)
        return {sym: None for sym in symbols}
        
    result = {}
    
    # yf.download returns different structures if 1 ticker vs multiple
    if len(symbols) == 1:
        sym = symbols[0]
        if data.empty:
            result[sym] = None
        else:
            df = data.copy()
            df.index = df.index.strftime('%Y-%m-%d')
            result[sym] = df
    else:
        for sym, yf_sym in zip(symbols, yf_tickers):
            if yf_sym in data.columns.levels[0]:
                df = data[yf_sym].copy()
                df = df.dropna(how="all")
                if not df.empty:
                    df.index = df.index.strftime('%Y-%m-%d')
                    result[sym] = df
                else:
                    result[sym] = None
            else:
                result[sym] = None
                
    logger.info("Successfully fetched history for %d/%d symbols.", 
                sum(1 for v in result.values() if v is not None), len(symbols))
    return result

def get_7d_trend_summary(df: pd.DataFrame) -> str:
    """
    Generates a quick text summary of the 7-day trend (e.g., up 5%, volume expanding).
    Useful for feeding into the AI.
    """
    if df is None or len(df) < 2:
        return "Not enough data"
        
    start_close = df['Close'].iloc[0]
    end_close = df['Close'].iloc[-1]
    pct_change = ((end_close - start_close) / start_close) * 100
    
    avg_vol = df['Volume'].mean()
    last_vol = df['Volume'].iloc[-1]
    vol_ratio = (last_vol / avg_vol) if avg_vol > 0 else 1.0
    
    trend_dir = "Up" if pct_change > 0 else "Down"
    return f"{trend_dir} {pct_change:.1f}% over 7 days. Today's volume is {vol_ratio:.1f}x the 7-day avg."
