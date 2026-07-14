"""
eod_report.py — V3.1 Premium Polish
Assembles the premium daily tear-sheet featuring FII/DII tracking, 
portfolio P&L, AI Red-Team validation, and educational insights.
"""
import logging
import sys
import os
from datetime import datetime
import pandas as pd
import requests

from config import HEALTHCHECKS_BASE, TOP_N
from src.data.upstox_client import UpstoxClient
from src.data.nse_bhavcopy import get_eod_data, merge_with_delivery
from src.data.fii_dii_fetcher import get_fii_dii_data
from src.data.news_rss_fetcher import fetch_stock_news, format_news_for_prompt
from src.analysis.market_segmenter import MarketSegmenter
from src.analysis.anomaly_detector import extract_momentum_breakouts, extract_value_reversals
from src.analysis.gemini_analyst import GeminiAnalyst
from src.analysis.portfolio_tracker import load_portfolio, analyze_portfolio
from src.analysis.red_team import red_team_validation
from src.reports.email_sender import send_html_email

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Premium CSS Template - Clean Light Mode
EMAIL_CSS = """
<style>
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background-color: #f6f8fa; color: #24292f; line-height: 1.6; padding: 20px; }
    .container { max-width: 720px; margin: 0 auto; background: #ffffff; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); padding: 30px; border: 1px solid #e1e4e8; }
    h2 { border-bottom: 2px solid #0969da; padding-bottom: 10px; font-weight: 600; font-size: 24px; margin-top: 0; }
    h3 { font-size: 18px; font-weight: 600; color: #24292f; margin-top: 25px; border-bottom: 1px solid #eaecef; padding-bottom: 8px; }
    .card { background: #f8f9fa; border: 1px solid #e1e4e8; border-radius: 8px; padding: 15px; margin-bottom: 15px; }
    .analyst-take { border-left: 4px solid #0366d6; background-color: #f1f8ff; padding: 12px 15px; margin: 15px 0; border-radius: 0 6px 6px 0; font-size: 14px; }
    .analyst-desk { border-left: 4px solid #bf8700; background-color: #fffbdd; padding: 15px; margin: 15px 0; border-radius: 0 6px 6px 0; font-size: 14px; }
    table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 13px; }
    th { background-color: #f6f8fa; text-align: left; padding: 10px; color: #57606a; border-bottom: 1px solid #d0d7de; font-weight: 600; }
    td { padding: 10px; border-bottom: 1px solid #e1e4e8; }
    .positive { color: #1a7f37; font-weight: 600; }
    .negative { color: #d1242f; font-weight: 600; }
    .muted { color: #57606a; font-size: 13px; }
    .badge { display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 12px; font-weight: 600; margin-left: 8px; }
    .badge-pos { background: #dafbe1; color: #1a7f37; }
    .badge-neg { background: #ffebe9; color: #d1242f; }
</style>
"""

def _format_fii_dii(fii_dii: dict) -> str:
    if not fii_dii:
        return "<p class='muted'>FII/DII Data Unavailable</p>"
    
    fii = fii_dii.get('FII', 0)
    dii = fii_dii.get('DII', 0)
    
    fii_css = "positive" if fii > 0 else "negative"
    dii_css = "positive" if dii > 0 else "negative"
    
    return f"""
    <div style="display: flex; gap: 20px; margin-bottom: 15px;">
        <div class="card" style="flex: 1; margin: 0; text-align: center;">
            <div class="muted">FII Net Cash</div>
            <div class='{fii_css}' style="font-size: 20px;">₹{fii:,.2f} Cr</div>
        </div>
        <div class="card" style="flex: 1; margin: 0; text-align: center;">
            <div class="muted">DII Net Cash</div>
            <div class='{dii_css}' style="font-size: 20px;">₹{dii:,.2f} Cr</div>
        </div>
    </div>
    """

def _format_portfolio(results: list) -> str:
    if not results:
        return "<p class='muted'>No portfolio loaded.</p>"
        
    html = "<div class='card' style='padding: 0; overflow-x: auto;'><table>"
    html += "<tr><th>Symbol</th><th>Qty</th><th>Avg Price</th><th>Close</th><th>Today %</th><th>Total P&L %</th><th>7-Day Trend</th></tr>"
    
    total_unrealized = 0
    total_invested = 0
    
    for r in results:
        today_css = "positive" if r['pct_change'] > 0 else "negative" if r['pct_change'] < 0 else ""
        unrealized_css = "badge-pos" if r['unrealized_pct'] > 0 else "badge-neg" if r['unrealized_pct'] < 0 else ""
        
        total_invested += (r['shares'] * r['avg_price'])
        total_unrealized += r['unrealized_pl']
        
        html += f"""
        <tr>
            <td><strong>{r['SYMBOL']}</strong></td>
            <td>{r['shares']}</td>
            <td>₹{r['avg_price']:.2f}</td>
            <td>₹{r['close']:.2f}</td>
            <td class='{today_css}'>{r['pct_change']:+.2f}%</td>
            <td><span class='badge {unrealized_css}'>{r['unrealized_pct']:+.2f}%</span></td>
            <td class='muted' style='font-size: 0.85em;'>{r['trend']}</td>
        </tr>
        """
        
    total_pct = (total_unrealized / total_invested * 100) if total_invested > 0 else 0
    total_css = "positive" if total_pct > 0 else "negative"
    html += f"<tr style='background: #f6f8fa;'><td colspan='5'><strong>Total Portfolio Performance</strong></td><td colspan='2' class='{total_css}'><strong>{total_pct:+.2f}% (₹{total_unrealized:,.2f})</strong></td></tr>"
    html += "</table></div>"
    return html

def _format_trade_candidates(df: pd.DataFrame, title: str, analyst: GeminiAnalyst) -> str:
    if df.empty:
        return f"<h3>{title}</h3><p class='muted'>No setups passed the strict filtering today.</p>"
        
    html = f"<h3>{title}</h3>"
    
    for _, row in df.iterrows():
        sym = row['SYMBOL']
        pct = row['PCT_CHANGE']
        deliv = row['DELIVERY_PCT']
        
        # 1. Provide Context
        context = f"Price moved {pct:+.2f}%. Massive institutional delivery at {deliv:.1f}%."
        
        # 2. Get AI Red Team Verdict
        verdict = red_team_validation(sym, context, analyst)
        
        cls_css = "badge-pos" if pct > 0 else "badge-neg"
        html += f"""
        <div class="card">
            <h4 style="margin-top: 0; margin-bottom: 10px;">{sym} <span class='badge {cls_css}'>{pct:+.2f}%</span> <span class="muted" style="font-weight: normal; margin-left: 10px;">Delivery: {deliv:.1f}%</span></h4>
            <div class='analyst-take' style="margin:0;">
                <strong>AI Red Team Verdict:</strong><br/>
                {verdict}
            </div>
        </div>
        """
        
    return html

def build_eod_report() -> str:
    logger.info("Building V3.1 EOD Deep Dive...")
    
    analyst = GeminiAnalyst()
    
    # 1. Fetch Market & Macro Data
    upstox = UpstoxClient()
    indian_indices = upstox.get_index_quotes()
    fii_dii_data = get_fii_dii_data()
    global_news = fetch_stock_news("Global Economy OR Indian Stock Market", 3)
    
    # 2. Fetch NSE Bhavcopy & Segment
    bhav_df, deliv_df = get_eod_data()
    if bhav_df is None:
        raise ValueError("Failed to download NSE Bhavcopy.")
        
    df = merge_with_delivery(bhav_df, deliv_df)
    segmenter = MarketSegmenter()
    df = segmenter.segment(df)
    
    # 3. Analyze Personal Portfolio
    portfolio = load_portfolio()
    portfolio_results = analyze_portfolio(df, portfolio)
    
    # 4. Run Strategy Screeners
    momentum = extract_momentum_breakouts(df, n=2)
    value = extract_value_reversals(df, n=2)
    
    # 5. Generate Top-Level AI Narratives
    idx_str = "\n".join([f"{k}: {v['pct_change']}%" for k, v in indian_indices.items() if v])
    fii_str = f"FII: {fii_dii_data.get('FII', 0)} Cr, DII: {fii_dii_data.get('DII', 0)} Cr" if fii_dii_data else "No data"
    news_str = format_news_for_prompt(global_news)
    
    macro_summary = analyst.get_market_summary(idx_str, news_str, fii_str)
    lesson = analyst.get_analyst_desk_lesson("Institutional Footprints (FII/DII Net Cash Flow)")
    
    # 6. Construct HTML
    today_str = datetime.now().strftime("%a, %d %b")
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        {EMAIL_CSS}
    </head>
    <body>
        <div class="container">
            <h2>📊 The Edge: Portfolio & Market Deep Dive &mdash; {today_str}</h2>
            
            <h3>🌍 Macro Liquidity & Global Context</h3>
            {_format_fii_dii(fii_dii_data)}
            <div class='analyst-take'>
                <strong>Lead Analyst Summary:</strong><br/>
                {macro_summary}
            </div>
            
            <h3>💼 Your Personal Portfolio</h3>
            {_format_portfolio(portfolio_results)}
            
            <h3>🎯 AI-Validated Actionable Trades</h3>
            <p class='muted'>These candidates passed the quantitative screener and were subjected to live news Red-Team validation.</p>
            
            {_format_trade_candidates(momentum, "🚀 High-Momentum Breakouts (Mid/Small Cap)", analyst)}
            {_format_trade_candidates(value, "💎 Value Reversals (Large Cap)", analyst)}
            
            <h3>🎓 The Analyst's Desk</h3>
            <div class="analyst-desk">
                <strong style="color: #9a6c00;">Today's Lesson: Institutional Footprints</strong><br/>
                {lesson}
            </div>
            
            <div style="text-align: center; margin-top: 30px; font-size: 12px; color: #8c959f;">
                Generated by SM-Report AI Engine
            </div>
        </div>
    </body>
    </html>
    """
    
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
        
        subject = f"📊 Your Portfolio & Market Edge — {today_str} {nifty_str}"
        
        success = send_html_email(subject, html_content)
        
        if success:
            logger.info("V3.1 EOD Report sent successfully.")
            hc_uuid = os.environ.get("HEALTHCHECKS_UUID")
            if hc_uuid:
                requests.get(f"{HEALTHCHECKS_BASE}/{hc_uuid}", timeout=10)
        else:
            sys.exit(1)
            
    except Exception as exc:
        logger.error("V3.1 EOD Report failed: %s", exc)
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
