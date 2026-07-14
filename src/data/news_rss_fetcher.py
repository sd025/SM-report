"""
news_rss_fetcher.py — Fetches stock-specific news from Google News RSS.
Used by the AI Red Team to validate breakouts and check for rumors/crises.
"""
import feedparser
import logging
import urllib.parse
from typing import List, Dict

logger = logging.getLogger(__name__)

def fetch_stock_news(query: str, max_articles: int = 5) -> List[Dict[str, str]]:
    """
    Fetches the latest news for a specific stock ticker, company name, or macro topic.
    Returns a list of dicts: {"title": ..., "published": ..., "link": ...}
    """
    try:
        encoded_query = urllib.parse.quote(query)
        # Using English / India specific feed parameters
        rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-IN&gl=IN&ceid=IN:en"
        
        feed = feedparser.parse(rss_url)
        articles = []
        
        for entry in feed.entries[:max_articles]:
            articles.append({
                "title": entry.title,
                "published": getattr(entry, 'published', 'Unknown date'),
                "link": entry.link
            })
            
        logger.info("Fetched %d news articles for query: '%s'", len(articles), query)
        return articles
        
    except Exception as exc:
        logger.error("Failed to fetch RSS news for '%s': %s", query, exc)
        return []

def format_news_for_prompt(articles: List[Dict[str, str]]) -> str:
    """Formats the list of articles into a clean string for the Gemini prompt."""
    if not articles:
        return "No recent news found."
        
    formatted = []
    for a in articles:
        formatted.append(f"- {a['title']} ({a['published']})")
    return "\n".join(formatted)
