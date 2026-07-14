"""
morning_brief.py — Assembles and sends the 8:30 AM IST Morning Brief.
Uses:
- Upstox API for previous close of Indian indices
- yfinance for overnight global markets (US close, SGX Nifty morning quote)
- NewsData.io for headlines
- Gemini for short macro narrative
"""

import logging
import sys
from datetime import datetime
import requests

from config import SECTOR_ORDER, HEALTHCHECKS_BASE
from src.data.upstox_client import UpstoxClient
from src.data.global_markets import get_global_snapshot
from src.data.news_fetcher import get_market_news
from src.analysis.gemini_analyst import GeminiAnalyst
from src.reports.email_sender import send_html_email

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def build_morning_brief() -> str:
    logger.info("Building Morning Brief...")
    
    # 1. Fetch Global Markets
    global_data = get_global_snapshot()
    
    # 2. Fetch Indian Indices (Yesterday's close)
    upstox = UpstoxClient()
    indian_indices = upstox.get_index_quotes()
    
    # 3. Fetch News
    news = get_market_news(5)
    
    # 4. Generate AI Summary
    analyst = GeminiAnalyst()
    
    # Format data for prompt
    idx_str = "\n".join([f"{k}: {v['pct_change']}%" for k, v in indian_indices.items() if v])
    glob_str = "\n".join([f"{k}: {v['pct_change']}%" for k, v in global_data.items() if v])
    news_str = "\n".join([f"- {n['title']}" for n in news])
    
    summary_prompt = f"Indian (Prev Close):\n{idx_str}\n\nGlobal Overnight:\n{glob_str}\n\nHeadlines:\n{news_str}"
    macro_take = analyst.get_market_summary("Indices Data:\n" + summary_prompt, "News:\n" + news_str)
    
    # 5. Construct HTML
    today_str = datetime.now().strftime("%a, %d %b")
    sgx = global_data.get("SGX Nifty")
    sgx_signal = f"SGX Nifty {sgx['pct_change']:+.2f}%" if sgx else "Pre-open"
    
    html = f"""
    <h2>🌅 Morning Brief &mdash; {today_str}</h2>
    <p class="muted">Overnight global cues and yesterday's Indian market recap.</p>
    
    <div class="analyst-take">
        <strong>Analyst Macro Take:</strong><br/>
        {macro_take}
    </div>
    
    <h3>🌍 Overnight Global Snapshot</h3>
    <table>
        <tr><th>Market/Asset</th><th>Close</th><th>Chg %</th></tr>
    """
    
    for name, data in global_data.items():
        if data:
            cls_css = "positive" if data['pct_change'] > 0 else "negative" if data['pct_change'] < 0 else ""
            html += f"<tr><td>{name}</td><td>{data['close']}</td><td class='{cls_css}'>{data['pct_change']:+.2f}%</td></tr>"
            
    html += """
    </table>
    
    <h3>⚡ Yesterday's Recap (Indian Markets)</h3>
    <table>
        <tr><th>Index</th><th>Prev Close</th><th>Chg %</th></tr>
    """
    
    for name in ["Nifty 50", "Sensex", "Bank Nifty", "Nifty Midcap 150", "India VIX"]:
        data = indian_indices.get(name)
        if data:
            cls_css = "positive" if data['pct_change'] > 0 else "negative" if data['pct_change'] < 0 else ""
            html += f"<tr><td>{name}</td><td>{data['prev_close']}</td><td class='{cls_css}'>{data['pct_change']:+.2f}%</td></tr>"
            
    html += """
    </table>
    
    <h3>📰 Top Market-Moving Headlines</h3>
    <ul>
    """
    
    for n in news:
        html += f"<li><a href='{n['url']}'>{n['title']}</a> <span class='muted'>({n['source']})</span></li>"
        
    html += "</ul>"
    
    return html


def main():
    try:
        html_content = build_morning_brief()
        today_str = datetime.now().strftime("%a, %d %b")
        subject = f"🌅 Market Brief — {today_str}"
        
        success = send_html_email(subject, html_content)
        
        if success:
            logger.info("Morning Brief sent successfully.")
            # Ping Healthchecks
            import os
            hc_uuid = os.environ.get("HEALTHCHECKS_UUID")
            if hc_uuid:
                requests.get(f"{HEALTHCHECKS_BASE}/{hc_uuid}", timeout=10)
        else:
            sys.exit(1)
            
    except Exception as exc:
        logger.error("Morning Brief failed: %s", exc)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
