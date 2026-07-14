"""
download_constituents.py — Fetches the official Nifty index constituent CSVs
from the NSE website to keep our Large/Mid/Small cap categorizations accurate.
"""

import os
import requests
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# NSE uses these fixed URLs for the current composition of broad market indices
URLS = {
    "large_cap": "https://archives.nseindia.com/content/indices/ind_nifty100list.csv",
    "mid_cap":   "https://archives.nseindia.com/content/indices/ind_niftymidcap150list.csv",
    "small_cap": "https://archives.nseindia.com/content/indices/ind_niftysmallcap250list.csv"
}

from config import CONSTITUENT_FILES, DATA_DIR

_REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    
    for cap_type, url in URLS.items():
        filepath = CONSTITUENT_FILES[cap_type]
        logger.info("Downloading %s from %s", cap_type, url)
        
        try:
            resp = requests.get(url, headers=_REQUEST_HEADERS, timeout=15)
            resp.raise_for_status()
            
            with open(filepath, "wb") as f:
                f.write(resp.content)
                
            logger.info("Saved -> %s", filepath)
            
        except requests.RequestException as exc:
            logger.error("Failed to download %s: %s", url, exc)

if __name__ == "__main__":
    main()
