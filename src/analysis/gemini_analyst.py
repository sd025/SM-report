"""
gemini_analyst.py — Interacts with Google's Gemini API (google-genai SDK).
Provides the "brutally honest" 17-year veteran analyst persona.
"""

import logging
import os
from google import genai
from google.genai import types

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

# The correct model name for the google-genai SDK (not deprecated)
GEMINI_MODEL = "gemini-2.5-flash"


class GeminiAnalyst:
    """Wrapper for the google-genai SDK with the 17-year veteran persona."""

    def __init__(self):
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            logger.warning("GEMINI_API_KEY not found. AI narratives will be disabled.")
            self.enabled = False
            return

        self.client = genai.Client(api_key=api_key)
        self.model_name = GEMINI_MODEL
        self.config = types.GenerateContentConfig(
            temperature=0.4,
            system_instruction=SYSTEM_INSTRUCTION
        )
        self.enabled = True

    def _generate(self, prompt: str, fallback: str = "") -> str:
        """Central generate method with error handling."""
        if not self.enabled:
            return fallback or "AI narrative disabled (no API key)."
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=self.config
            )
            return response.text.strip()
        except Exception as exc:
            logger.error("Gemini API error: %s", exc)
            return fallback or f"AI generation failed: {exc}"

    def get_market_summary(self, index_data: str, news_data: str, fii_dii: str = "") -> str:
        """Generate a macro summary combining price action, liquidity, and global news."""
        prompt = (
            "Provide a brutally honest macro summary of the market today based on this data:\n\n"
            f"Indices:\n{index_data}\n\n"
            f"FII/DII Liquidity (Net Cash Rs Cr):\n{fii_dii}\n\n"
            f"Global Headlines / Crises:\n{news_data}\n\n"
            "What is the overall trend? Are institutions buying or selling? "
            "How do the global headlines affect Indian markets today? (Keep it to 4-5 sentences max)."
        )
        return self._generate(prompt, fallback="Market summary unavailable.")

    def get_analyst_desk_lesson(self, topic: str = "Volatility Contraction Pattern") -> str:
        """Generates a quick 3-sentence educational lesson on a financial concept."""
        prompt = (
            f"Explain the trading concept of '{topic}' in 3 simple sentences "
            "for someone who is not in finance, but wants to understand how hedge funds use it to make money."
        )
        return self._generate(prompt, fallback="")

    def analyze_stock_group(self, group_name: str, stock_data: str) -> str:
        """Analyze a list of gainers/losers or anomalies."""
        if not stock_data.strip():
            return "No notable stocks in this category."
        prompt = (
            f"Analyze this group of stocks ({group_name}):\n{stock_data}\n\n"
            "Provide a 2-3 sentence analysis per stock. Be brutally honest."
        )
        return self._generate(prompt, fallback="Analysis unavailable.")

    def red_team_verdict(self, symbol: str, data_context: str, news_context: str) -> str:
        """Generates a Red Team verdict for a trade candidate."""
        prompt = (
            f"You are the Lead Risk Officer (Red Team) at a top quantitative hedge fund.\n"
            f"A junior analyst is pitching {symbol} as a high-probability swing trade:\n\n"
            f"[QUANTITATIVE DATA]:\n{data_context}\n\n"
            f"[LATEST LIVE NEWS]:\n{news_context}\n\n"
            "Your job is to DESTROY this thesis if it's flawed.\n"
            "1. Is this breakout just a reaction to a rumor/news already priced in?\n"
            "2. Are there fundamental red flags in the news?\n"
            "3. Is this genuine institutional accumulation or retail FOMO?\n\n"
            f"Provide your Brutally Honest, 3-sentence verdict on {symbol}.\n"
            "Finish with exactly one of these labels: [APPROVED] or [REJECTED]."
        )
        return self._generate(prompt, fallback="Red Team validation unavailable.")

    def build_watchlist(self, anomaly_data: str) -> str:
        """Pick the top 3-4 most interesting setups from anomalies to watch tomorrow."""
        if not anomaly_data.strip():
            return "No significant anomalies detected for watchlist."
        prompt = (
            "Out of these anomalous stocks (high delivery % or high price movement), "
            "pick the top 3 that are most interesting to watch tomorrow.\n"
            "Are they breaking down heavily on institutional selling, or breaking out on accumulation?\n"
            "Give a brutally honest 2 sentence rationale for each.\n\n"
            "Format as a bulleted list:\n"
            "* **[SYMBOL]**: [Rationale]\n\n"
            f"Data:\n{anomaly_data}"
        )
        return self._generate(prompt, fallback="Watchlist unavailable.")
