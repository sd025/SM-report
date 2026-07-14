"""
news_fetcher.py — Fetches top Indian financial headlines from NewsData.io.
Free tier: 200 requests/day. We use 1–2 per day, so always within limits.
"""

import logging
import os
from typing import List, Dict, Optional

import requests

logger = logging.getLogger(__name__)

NEWSDATA_BASE = "https://newsdata.io/api/1/news"


def get_market_news(n: int = 5) -> List[Dict[str, str]]:
    """
    Fetch top n Indian financial/business headlines.
    Returns list of {"title": ..., "source": ..., "url": ..., "published": ...}

    Falls back to empty list silently if API fails — the report will still send.
    """
    api_key = os.environ.get("NEWSDATA_API_KEY", "")
    if not api_key:
        logger.warning("NEWSDATA_API_KEY not set — skipping news section.")
        return []

    params = {
        "apikey":   api_key,
        "country":  "in",
        "category": "business",
        "language": "en",
        "size":     min(n, 10),  # NewsData max per call
    }

    try:
        resp = requests.get(NEWSDATA_BASE, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        if data.get("status") != "success":
            logger.warning("NewsData API returned non-success: %s", data.get("message"))
            return []

        articles = data.get("results", [])[:n]
        headlines = []
        for a in articles:
            headlines.append({
                "title":     a.get("title", "No title"),
                "source":    a.get("source_id", "Unknown"),
                "url":       a.get("link", ""),
                "published": a.get("pubDate", ""),
            })
        logger.info("Fetched %d headlines from NewsData.io", len(headlines))
        return headlines

    except requests.RequestException as exc:
        logger.error("NewsData.io request failed: %s", exc)
        return []
    except Exception as exc:
        logger.error("Unexpected error in news_fetcher: %s", exc)
        return []
