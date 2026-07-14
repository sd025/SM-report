"""
red_team.py — The AI Validation Engine.
Combines Google News RSS and historical price data, then forces Gemini
to act as a skeptical Red Team against potential trade candidates.
"""
import logging
from typing import Dict, Any, List
from src.data.news_rss_fetcher import fetch_stock_news, format_news_for_prompt
from src.analysis.gemini_analyst import GeminiAnalyst

logger = logging.getLogger(__name__)

def red_team_validation(symbol: str, data_context: str, analyst: GeminiAnalyst) -> str:
    """
    Fetches latest news for a specific stock and feeds it + data to the AI Red Team.
    """
    logger.info("Initiating Red Team validation for %s", symbol)
    
    # 1. Scrape Live News for this exact stock
    news_articles = fetch_stock_news(symbol, max_articles=4)
    news_context = format_news_for_prompt(news_articles)
    
    # 2. Prompt the AI
    prompt = f"""
    You are the Lead Risk Officer (Red Team) at a top quantitative hedge fund. 
    A junior analyst is pitching {symbol} as a high-probability swing trade based on this data:
    
    [QUANTITATIVE DATA]:
    {data_context}
    
    [LATEST LIVE NEWS]:
    {news_context}
    
    Your job is to DESTROY this thesis if it's flawed. 
    1. Is this breakout just a reaction to a rumor/news that is already priced in?
    2. Are there fundamental red flags in the news?
    3. Is this a genuine institutional accumulation setup or retail FOMO?
    
    Provide your Brutally Honest, 3-sentence verdict on {symbol}.
    Finish with exactly one of these labels: [APPROVED] or [REJECTED].
    """
    
    # We bypass the standard GeminiAnalyst methods and use the model directly 
    # to enforce this specific Red Team persona.
    if not analyst.enabled:
        return "AI Red Team disabled. (No API Key)"
        
    try:
        response = analyst.model.generate_content(prompt)
        return response.text.strip()
    except Exception as exc:
        logger.error("Red Team validation failed for %s: %s", symbol, exc)
        return "Validation failed due to API error."
