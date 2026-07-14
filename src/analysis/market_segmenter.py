"""
market_segmenter.py — Classifies stocks into Large/Mid/Small cap.
Loads the bi-weekly refreshed SEBI constituent lists.
"""

import logging
import os
from typing import Set

import pandas as pd

from config import CONSTITUENT_FILES

logger = logging.getLogger(__name__)


def _load_constituents(filepath: str) -> Set[str]:
    """Load a single CSV of constituents, returning a set of symbols."""
    if not os.path.exists(filepath):
        logger.warning("Constituent file not found: %s", filepath)
        return set()

    try:
        df = pd.read_csv(filepath)
        # NSE typically uses "Symbol" or "SYMBOL", normalize just in case
        col_name = next((c for c in df.columns if c.strip().upper() == "SYMBOL"), None)
        if not col_name:
            logger.warning("No SYMBOL column found in %s", filepath)
            return set()

        symbols = set(df[col_name].astype(str).str.strip().str.upper())
        logger.debug("Loaded %d symbols from %s", len(symbols), os.path.basename(filepath))
        return symbols
    except Exception as exc:
        logger.error("Failed to load %s: %s", filepath, exc)
        return set()


class MarketSegmenter:
    """Classifies NSE stocks into Large/Mid/Small cap based on AMFI/NSE lists."""

    def __init__(self):
        self.large_cap = _load_constituents(CONSTITUENT_FILES["large_cap"])
        self.mid_cap   = _load_constituents(CONSTITUENT_FILES["mid_cap"])
        self.small_cap = _load_constituents(CONSTITUENT_FILES["small_cap"])

    def segment(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Adds a 'MARKET_CAP_SEGMENT' column to the DataFrame.
        Categories: Large, Mid, Small, Micro/Other.
        """
        if "SYMBOL" not in df.columns:
            raise ValueError("DataFrame must contain a SYMBOL column.")

        # Ensure string type for reliable matching
        df["SYMBOL"] = df["SYMBOL"].astype(str)

        def _get_segment(symbol: str) -> str:
            if symbol in self.large_cap:
                return "Large"
            elif symbol in self.mid_cap:
                return "Mid"
            elif symbol in self.small_cap:
                return "Small"
            else:
                return "Micro/Other"

        df["MARKET_CAP_SEGMENT"] = df["SYMBOL"].apply(_get_segment)
        return df
