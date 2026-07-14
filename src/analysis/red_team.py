"""
red_team.py — The AI Validation Engine.
Uses GeminiAnalyst.red_team_verdict() to validate trade candidates.
"""
import logging
from src.data.news_rss_fetcher import fetch_stock_news, format_news_for_prompt
from src.analysis.gemini_analyst import GeminiAnalyst

logger = logging.getLogger(__name__)

def red_team_validation(symbol: str, data_context: str, analyst: GeminiAnalyst) -> str:
    """
    Fetches latest news for a specific stock and feeds it + data to the AI Red Team.
    """
    logger.info("Initiating Red Team validation for %s", symbol)
    news_articles = fetch_stock_news(symbol, max_articles=4)
    news_context = format_news_for_prompt(news_articles)
    return analyst.red_team_verdict(symbol, data_context, news_context)
