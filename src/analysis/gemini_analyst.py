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
You are a 17+ year veteran equity research analyst and Hedge Fund Manager who has covered Indian markets through multiple bull and bear cycles.
Your audience is a busy professional who relies on you to manage their portfolio strategy.
Your style is brutally honest, data-driven, and highly educational.

Rules:
- Never sugarcoat. If FIIs are dumping, say the market is weak.
- Connect the dots between global macro (news) and Indian liquidity (FII/DII data).
- When recommending a trade, always provide the exact setup (e.g. VCP Breakout) and an explicit Invalidation/Stop-Loss level.
- Think like a portfolio manager: prioritize risk management over hype.
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

    def get_market_summary(self, index_data: str, news_data: str, fii_dii: str = "") -> str:
        """Generate a macro summary combining price action, liquidity, and global news."""
        if not self.enabled:
            return "AI narrative disabled (no API key)."

        prompt = f"""
        Provide a brutally honest macro summary of the market today based on this data:
        
        Indices:
        {index_data}
        
        FII/DII Liquidity (Net Cash Rs Cr):
        {fii_dii}
        
        Global Headlines / Crises:
        {news_data}
        
        What is the overall trend? Are institutions buying or selling? How do the global headlines affect Indian markets today? (Keep it to 4-5 sentences max).
        """
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as exc:
            logger.error("Gemini macro summary failed: %s", exc)
            return "Failed to generate market summary."

    def get_analyst_desk_lesson(self, topic: str = "Volatility Contraction Pattern") -> str:
        """Generates a quick 3-sentence educational lesson on a financial concept."""
        if not self.enabled:
            return ""
            
        prompt = f"Explain the trading concept of '{topic}' in 3 simple sentences for someone who is not in finance, but wants to understand how hedge funds use it to make money."
        try:
            return self.model.generate_content(prompt).text.strip()
        except:
            return ""

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
