"""
fii_dii_fetcher.py — Scrapes daily FII/DII cash market net activity.
This is the macro liquidity indicator.
"""
import requests
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Use a well-known community endpoint or direct NSE API to fetch FII/DII data.
# NSE API requires cookie handling, so we'll use nseindia API with proper headers.
NSE_BASE_URL = "https://www.nseindia.com"
NSE_FII_DII_URL = f"{NSE_BASE_URL}/api/fiidiiTradeReact"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://www.nseindia.com/reports/fii-dii",
}

def get_fii_dii_data() -> Optional[Dict[str, float]]:
    """
    Returns a dict with FII and DII net buy/sell amounts in Crores.
    Example: {"FII": -1500.50, "DII": 2500.25}
    """
    session = requests.Session()
    session.headers.update(HEADERS)
    
    try:
        # NSE requires a cookie to be set first from the homepage
        logger.info("Setting NSE session cookies...")
        session.get(NSE_BASE_URL, timeout=10)
        
        logger.info("Fetching FII/DII data...")
        resp = session.get(NSE_FII_DII_URL, timeout=10)
        
        if resp.status_code == 200:
            data = resp.json()
            # Parse the list of dictionaries
            result = {}
            for item in data:
                category = item.get("category", "")
                net_value = float(item.get("netValue", 0).replace(",", ""))
                
                if "FII" in category or "FPI" in category:
                    result["FII"] = net_value
                elif "DII" in category:
                    result["DII"] = net_value
                    
            if not result:
                logger.warning("FII/DII data was empty or unparseable.")
                return None
                
            logger.info("Successfully fetched FII/DII data: %s", result)
            return result
        else:
            logger.error("NSE API returned status %s", resp.status_code)
            return None
            
    except Exception as exc:
        logger.error("Failed to fetch FII/DII data: %s", exc)
        return None
