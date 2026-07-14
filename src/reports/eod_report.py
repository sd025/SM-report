"""
eod_report.py — Assembles and sends the 6:00 PM IST EOD Deep Dive.
Uses:
- Upstox API for index closes
- NSE Bhavcopy for full market breadth, delivery %, and anomalies
- Market Segmenter to break down Large/Mid/Small cap
- Gemini Analyst for the "brutally honest" take on gainers/losers/watchlist
"""

import logging
import sys
from datetime import datetime
import pandas as pd
import requests

from config import HEALTHCHECKS_BASE, TOP_N, WATCHLIST_N
from src.data.upstox_client import UpstoxClient
from src.data.nse_bhavcopy import get_eod_data, merge_with_delivery
from src.analysis.market_segmenter import MarketSegmenter
from src.analysis.anomaly_detector import extract_top_movers, detect_delivery_anomalies
from src.analysis.gemini_analyst import GeminiAnalyst
from src.reports.email_sender import send_html_email

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def _df_to_html(df: pd.DataFrame, title: str) -> str:
    """Format dataframe into HTML table."""
    if df.empty:
        return f"<h3>{title}</h3><p class='muted'>No significant data.</p>"
        
    html = f"<h3>{title}</h3><table><tr>"
    
    # Pick columns to show
    cols = ["SYMBOL", "CLOSE", "PCT_CHANGE"]
    if "DELIVERY_PCT" in df.columns:
        cols.append("DELIVERY_PCT")
        
    for c in cols:
        html += f"<th>{c}</th>"
    html += "</tr>"
    
    for _, row in df.iterrows():
        pct = row['PCT_CHANGE']
        cls_css = "positive" if pct > 0 else "negative" if pct < 0 else ""
        html += f"<tr><td><strong>{row['SYMBOL']}</strong></td><td>{row['CLOSE']:.2f}</td><td class='{cls_css}'>{pct:+.2f}%</td>"
        
        if "DELIVERY_PCT" in cols:
            del_pct = row['DELIVERY_PCT']
            if pd.isna(del_pct):
                html += "<td>-</td>"
            else:
                del_css = "positive" if del_pct > 60 else ""
                html += f"<td class='{del_css}'>{del_pct:.1f}%</td>"
                
        html += "</tr>"
        
    html += "</table>"
    return html


def build_eod_report() -> str:
    logger.info("Building EOD Deep Dive...")
    
    # 1. Fetch Indian Indices (Today's close)
    upstox = UpstoxClient()
    indian_indices = upstox.get_index_quotes()
    
    # 2. Fetch NSE Bhavcopy & Delivery
    bhav_df, deliv_df = get_eod_data()
    if bhav_df is None:
        raise ValueError("Failed to download NSE Bhavcopy.")
        
    df = merge_with_delivery(bhav_df, deliv_df)
    
    # 3. Segment Market
    segmenter = MarketSegmenter()
    df = segmenter.segment(df)
    
    # 4. Extract Movers & Anomalies
    large_losers = extract_top_movers(df, "Large", "losers", TOP_N)
    mid_losers   = extract_top_movers(df, "Mid", "losers", TOP_N)
    small_losers = extract_top_movers(df, "Small", "losers", TOP_N)
    
    large_gainers = extract_top_movers(df, "Large", "gainers", TOP_N)
    
    anomalies = detect_delivery_anomalies(df)
    
    # 5. Generate AI Narratives
    analyst = GeminiAnalyst()
    
    def _format_for_ai(movers_df: pd.DataFrame) -> str:
        if movers_df.empty: return ""
        lines = []
        for _, r in movers_df.iterrows():
            d = f"{r['DELIVERY_PCT']:.1f}%" if pd.notna(r.get('DELIVERY_PCT')) else "N/A"
            lines.append(f"{r['SYMBOL']}: {r['PCT_CHANGE']:+.2f}% (Delivery: {d})")
        return "\n".join(lines)
        
    ll_ai = analyst.analyze_stock_group("Large Cap Losers", _format_for_ai(large_losers))
    lg_ai = analyst.analyze_stock_group("Large Cap Gainers", _format_for_ai(large_gainers))
    watchlist_ai = analyst.build_watchlist(_format_for_ai(anomalies.head(10)))
    
    # 6. Construct HTML
    today_str = datetime.now().strftime("%a, %d %b")
    
    html = f"""
    <h2>📊 EOD Deep Dive &mdash; {today_str}</h2>
    
    <h3>📈 Index Snapshot</h3>
    <table>
        <tr><th>Index</th><th>Close</th><th>Chg %</th></tr>
    """
    
    for name, data in indian_indices.items():
        if data:
            cls_css = "positive" if data['pct_change'] > 0 else "negative" if data['pct_change'] < 0 else ""
            html += f"<tr><td>{name}</td><td>{data['close']}</td><td class='{cls_css}'>{data['pct_change']:+.2f}%</td></tr>"
            
    html += "</table>"
    
    # Market Breadth Calculation
    advances = len(df[df["PCT_CHANGE"] > 0])
    declines = len(df[df["PCT_CHANGE"] < 0])
    html += f"<p><strong>Market Breadth:</strong> {advances} Advances / {declines} Declines</p>"
    
    # Sections
    html += _df_to_html(large_losers, "🔴 Top Large Cap Losers")
    html += f"<div class='analyst-take'>{ll_ai}</div>"
    
    html += _df_to_html(large_gainers, "🟢 Top Large Cap Gainers")
    html += f"<div class='analyst-take'>{lg_ai}</div>"
    
    html += _df_to_html(mid_losers, "🔴 Top Mid Cap Losers")
    html += _df_to_html(small_losers, "🔴 Top Small Cap Losers")
    
    html += "<h3>👁️ Analyst Watchlist &mdash; Tomorrow</h3>"
    html += f"<div class='analyst-take'>{watchlist_ai}</div>"
    
    return html


def main():
    try:
        html_content = build_eod_report()
        today_str = datetime.now().strftime("%a, %d %b")
        
        # Calculate Nifty move for subject line
        upstox = UpstoxClient()
        indices = upstox.get_index_quotes()
        nifty = indices.get("Nifty 50")
        nifty_str = f"| Nifty {nifty['pct_change']:+.2f}%" if nifty else ""
        
        subject = f"📊 EOD Report — {today_str} {nifty_str}"
        
        success = send_html_email(subject, html_content)
        
        if success:
            logger.info("EOD Report sent successfully.")
            import os
            hc_uuid = os.environ.get("HEALTHCHECKS_UUID")
            if hc_uuid:
                requests.get(f"{HEALTHCHECKS_BASE}/{hc_uuid}", timeout=10)
        else:
            sys.exit(1)
            
    except Exception as exc:
        logger.error("EOD Report failed: %s", exc)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
