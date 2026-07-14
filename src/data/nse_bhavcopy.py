"""
nse_bhavcopy.py — Downloads and parses NSE's official End-of-Day data.

Two files are downloaded per day:
  1. CM Bhavcopy (ZIP/CSV) — OHLCV + prev close for every NSE equity stock
  2. Delivery Positions (DAT) — delivery % per stock (key institutional signal)

Both are from NSE's public archive server — no authentication required.
Published daily ~5:30–6:00 PM IST after market close.
"""

import io
import logging
import time
import zipfile
from datetime import date, timedelta
from typing import Optional, Tuple

import pandas as pd
import requests

logger = logging.getLogger(__name__)

NSE_ARCHIVE = "https://nsearchives.nseindia.com"

_REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "*/*",
    "Referer": "https://www.nseindia.com/",
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def last_trading_day(offset: int = 0) -> date:
    """Return today (minus offset), rolling back over weekends."""
    d = date.today() - timedelta(days=offset)
    while d.weekday() >= 5:      # 5=Sat, 6=Sun
        d -= timedelta(days=1)
    return d


# ── Bhavcopy ──────────────────────────────────────────────────────────────────

def _bhavcopy_url(d: date) -> str:
    """NSE CM UDiFF Bhavcopy (Final) — ZIP format. Published post July 2024."""
    return (
        f"{NSE_ARCHIVE}/content/cm/"
        f"BhavCopy_NSE_CM_0_0_0_{d.strftime('%Y%m%d')}_F_0000.csv.zip"
    )


def _download_bhavcopy(d: date) -> Optional[bytes]:
    url = _bhavcopy_url(d)
    try:
        resp = requests.get(url, headers=_REQUEST_HEADERS, timeout=25)
        if resp.status_code == 200:
            logger.info("Bhavcopy downloaded: %d bytes", len(resp.content))
            return resp.content
        logger.warning("Bhavcopy HTTP %s — date: %s", resp.status_code, d)
    except requests.RequestException as exc:
        logger.error("Bhavcopy download exception: %s", exc)
    return None


def _parse_bhavcopy(zip_bytes: bytes) -> Optional[pd.DataFrame]:
    """Unzip and parse the bhavcopy CSV into a clean DataFrame."""
    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            csv_name = next((n for n in zf.namelist() if n.endswith(".csv")), None)
            if not csv_name:
                logger.error("No CSV found inside bhavcopy ZIP.")
                return None
            with zf.open(csv_name) as f:
                df = pd.read_csv(f, low_memory=False)
    except Exception as exc:
        logger.error("Failed to parse bhavcopy ZIP: %s", exc)
        return None

    # Normalize column names — NSE changes capitalization/underscore style occasionally
    df.columns = [c.strip().upper().replace(" ", "_") for c in df.columns]

    # Column name aliases (NSE UDiFF uses different names than the old format)
    aliases = {
        "TRAD_CONS_SYM":  "SYMBOL",
        "SYMBOL":         "SYMBOL",
        "ISIN_CODE":      "ISIN",
        "ISIN":           "ISIN",
        "OPEN_PRICE":     "OPEN",
        "HIGH_PRICE":     "HIGH",
        "LOW_PRICE":      "LOW",
        "CLOSE_PRICE":    "CLOSE",
        "PREV_CL_PR":     "PREV_CLOSE",
        "PREV_CLOSE":     "PREV_CLOSE",
        "TTL_TRD_QNTY":  "VOLUME",
        "TOT_TRD_QTY":   "VOLUME",
        "SERIES":         "SERIES",
        "MKT_CAP":        "MKT_CAP",
    }
    for old, new in aliases.items():
        if old in df.columns and new not in df.columns:
            df.rename(columns={old: new}, inplace=True)

    # Keep only equity series (EQ = regular, BE = trade-to-trade, BZ = SME)
    if "SERIES" in df.columns:
        df = df[df["SERIES"].isin(["EQ", "BE", "BZ"])].copy()

    # Coerce numeric columns
    for col in ["OPEN", "HIGH", "LOW", "CLOSE", "PREV_CLOSE", "VOLUME"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Drop rows without close or prev_close
    df = df.dropna(subset=["CLOSE"]).copy()

    # Compute % change
    if "PREV_CLOSE" in df.columns:
        prev = df["PREV_CLOSE"].replace(0, pd.NA)
        df["PCT_CHANGE"] = ((df["CLOSE"] - prev) / prev * 100).round(2)

    logger.info("Bhavcopy parsed: %d equity rows", len(df))
    return df.reset_index(drop=True)


# ── Delivery Positions ────────────────────────────────────────────────────────

def _delivery_url(d: date) -> str:
    """NSE Security-wise Delivery Positions — published alongside bhavcopy."""
    return (
        f"{NSE_ARCHIVE}/archives/equities/mto/"
        f"MTO_{d.strftime('%d%m%Y')}.DAT"
    )


def _download_delivery(d: date) -> Optional[pd.DataFrame]:
    url = _delivery_url(d)
    try:
        resp = requests.get(url, headers=_REQUEST_HEADERS, timeout=20)
        if resp.status_code != 200:
            logger.warning("Delivery data HTTP %s", resp.status_code)
            return None

        records = []
        for line in resp.text.strip().splitlines():
            parts = [p.strip() for p in line.split(",")]
            # Record type 20 = security-level delivery data
            if len(parts) >= 6 and parts[0] == "20":
                try:
                    records.append({
                        "SYMBOL":         parts[2].strip(),
                        "TRADED_QTY":     float(parts[3]),
                        "DELIVERABLE_QTY": float(parts[4]),
                        "DELIVERY_PCT":   float(parts[5]),
                    })
                except (ValueError, IndexError):
                    continue

        if not records:
            logger.warning("Delivery DAT file had no parseable records.")
            return None

        df = pd.DataFrame(records)
        logger.info("Delivery data parsed: %d rows", len(df))
        return df

    except requests.RequestException as exc:
        logger.error("Delivery data download error: %s", exc)
        return None


# ── Public API ────────────────────────────────────────────────────────────────

def get_eod_data(
    trading_date: Optional[date] = None,
) -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame]]:
    """
    Main entry point. Returns (bhavcopy_df, delivery_df).
    - bhavcopy_df : all equity stocks with OHLCV + PCT_CHANGE
    - delivery_df : delivery % per symbol

    Both can be None if download fails (caller should handle gracefully).
    """
    if trading_date is None:
        trading_date = last_trading_day(0)

    logger.info("Fetching EOD data for %s", trading_date)

    bhavcopy_df = None
    zip_bytes = _download_bhavcopy(trading_date)
    if zip_bytes:
        bhavcopy_df = _parse_bhavcopy(zip_bytes)

    time.sleep(1)  # polite delay to NSE servers

    delivery_df = _download_delivery(trading_date)
    return bhavcopy_df, delivery_df


def merge_with_delivery(
    bhavcopy: pd.DataFrame,
    delivery: Optional[pd.DataFrame],
) -> pd.DataFrame:
    """
    Left-join bhavcopy with delivery data on SYMBOL.
    Adds DELIVERY_PCT column (NaN if delivery data unavailable for that stock).
    """
    if delivery is None or delivery.empty:
        bhavcopy = bhavcopy.copy()
        bhavcopy["DELIVERY_PCT"]    = float("nan")
        bhavcopy["DELIVERABLE_QTY"] = float("nan")
        return bhavcopy

    return bhavcopy.merge(
        delivery[["SYMBOL", "DELIVERY_PCT", "DELIVERABLE_QTY"]],
        on="SYMBOL",
        how="left",
    )
