"""
gemini_analyst.py — Interacts with Google's Gemini Flash 1.5 API.
Provides the "brutally honest" 17-year veteran analyst persona.
"""

import logging
import os
from typing import List, Dict, Optional
import google.generativeai as genai
from config import GEMINI_MODEL

logger = logging.getLogger(__name__)

SYSTEM_INSTRUCTION = """
You are a 17+ year veteran equity research analyst who has covered Indian markets through multiple bull and bear cycles.
You have attended hundreds of management meetings and investor conferences.
Your style is brutally honest, data-driven, and concise.

Rules:
- Never sugarcoat. If a stock looks bad, say so plainly (e.g. "falling knife", "value trap").
- Always reference the exact data provided (delivery %, volume vs avg, 52W position, % change).
- Flag institutional activity (high delivery) vs retail panic (low delivery/high volume) separately.
- Keep each stock comment to 2-3 sentences maximum.
- Do NOT say "this is not financial advice" or include generic disclaimers — the user knows this.
- Think like a portfolio manager: what is the risk/reward here? Is it accumulation, distribution, or noise?
"""


class GeminiAnalyst:
    """Wrapper for Gemini Flash to generate market commentary."""

    def __init__(self):
        api_key = os.environ.get("GEMINI_API_KEY", "")
        if not api_key:
            logger.warning("GEMINI_API_KEY not set. Narrative generation will be disabled.")
            self.enabled = False
            return
            
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(
            model_name=GEMINI_MODEL,
            system_instruction=SYSTEM_INSTRUCTION
        )
        self.enabled = True

    def get_market_summary(self, index_data: str, news_data: str) -> str:
        """Generate a short 3-4 sentence macro summary of the day/morning."""
        if not self.enabled:
            return "AI narrative disabled (no API key)."

        prompt = f"""
        Provide a very brief (3-4 sentences max) macro summary of the market based on this data:
        
        Indices:
        {index_data}
        
        Headlines:
        {news_data}
        
        What is the overall tone/trend? What should an investor be cautious about today/tomorrow?
        """
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as exc:
            logger.error("Gemini macro summary failed: %s", exc)
            return "Failed to generate market summary."

    def analyze_stock_group(self, group_name: str, stock_data: str) -> str:
        """Analyze a list of gainers/losers or anomalies."""
        if not self.enabled:
            return "AI narrative disabled."
            
        if not stock_data.strip():
            return "No notable stocks in this category."

        prompt = f"""
        Review this list of {group_name}. Provide your brutally honest, 2-3 sentence take on EACH stock.
        Format as a bulleted list:
        * **[SYMBOL]**: [Your 2-3 sentence take]
        
        Data:
        {stock_data}
        """
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as exc:
            logger.error("Gemini stock analysis failed: %s", exc)
            return "Failed to analyze stocks."

    def build_watchlist(self, anomaly_data: str) -> str:
        """Pick the top 3-4 most interesting setups from anomalies to watch tomorrow."""
        if not self.enabled:
            return "AI watchlist disabled."
            
        if not anomaly_data.strip():
            return "No significant anomalies detected for watchlist."

        prompt = f"""
        Out of these anomalous stocks (high delivery % or high price movement), pick the top 3 that are most interesting to watch tomorrow. 
        Are they breaking down heavily on institutional selling, or breaking out on accumulation?
        Give a brutally honest 2 sentence rationale for each.
        
        Format as a bulleted list:
        * **[SYMBOL]**: [Rationale]
        
        Data:
        {anomaly_data}
        """
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as exc:
            logger.error("Gemini watchlist failed: %s", exc)
            return "Failed to build watchlist."
