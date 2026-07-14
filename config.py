"""
config.py — Non-secret configuration. Safe to commit.
All API keys / passwords must come from environment variables.
"""

import os

# ── Gemini Model ──────────────────────────────────────────────────────────────
GEMINI_MODEL = "gemini-2.0-flash"

# ── Market Cap Segmentation (SEBI Definitions by rank) ───────────────────────
LARGE_CAP_MAX_RANK = 100    # Top 100 by 6-month avg market cap = Large Cap
MID_CAP_MAX_RANK   = 250    # Rank 101–250 = Mid Cap
# Rank 251+            = Small Cap

# ── Anomaly Detection Thresholds ──────────────────────────────────────────────
DELIVERY_HIGH_PCT      = 60.0   # Delivery % > this → notable
DELIVERY_EXTREME_PCT   = 75.0   # Delivery % > this → strong institutional signal
VOLUME_SPIKE_MULT      = 2.0    # Volume / 30d avg > this → spike
VOLUME_EXTREME_MULT    = 4.0    # Volume / 30d avg > this → extreme spike
PCT_CHANGE_SIGNIFICANT = 3.0    # % move > this is significant

# ── Report Settings ───────────────────────────────────────────────────────────
TOP_N       = 5   # Top N gainers/losers per segment shown in report
WATCHLIST_N = 4   # Stocks highlighted in "Watch Tomorrow" section
NEWS_N      = 5   # Number of news headlines to fetch

# ── Upstox — Index Instrument Keys ───────────────────────────────────────────
NSE_INDICES = {
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

# Ordered list for display in sector rotation section
SECTOR_ORDER = [
    "Bank Nifty", "Nifty IT", "Nifty Pharma", "Nifty Auto",
    "Nifty Metal", "Nifty Realty", "Nifty FMCG", "Nifty Energy",
]

# ── yfinance — Global Market Tickers ─────────────────────────────────────────
GLOBAL_TICKERS = {
    "S&P 500":    "^GSPC",
    "Nasdaq":     "^IXIC",
    "Dow Jones":  "^DJI",
    "Nikkei 225": "^N225",
    "USD/INR":    "USDINR=X",
    "Brent Crude": "BZ=F",
    "Gold":       "GC=F",
}

# ── Data Directory ────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR  = os.path.join(BASE_DIR, "data", "index_constituents")

CONSTITUENT_FILES = {
    "large_cap":  os.path.join(DATA_DIR, "nifty100.csv"),
    "mid_cap":    os.path.join(DATA_DIR, "nifty_midcap150.csv"),
    "small_cap":  os.path.join(DATA_DIR, "nifty_smallcap250.csv"),
}

# ── NSE Archive Base URL ──────────────────────────────────────────────────────
NSE_ARCHIVE_BASE = "https://nsearchives.nseindia.com"

# ── Healthchecks.io ───────────────────────────────────────────────────────────
HEALTHCHECKS_BASE = "https://hc-ping.com"
