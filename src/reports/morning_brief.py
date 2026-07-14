"""
morning_brief.py — Assembles and sends the 8:30 AM IST Morning Brief.
Premium UI: Clean Light Mode.
"""
import logging
import sys
import os
from datetime import datetime
import requests

from config import HEALTHCHECKS_BASE
from src.data.upstox_client import UpstoxClient
from src.data.global_markets import get_global_snapshot
from src.data.news_fetcher import get_market_news
from src.analysis.gemini_analyst import GeminiAnalyst
from src.reports.email_sender import send_html_email

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

EMAIL_CSS = """
<style>
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background-color: #f6f8fa; color: #24292f; line-height: 1.6; padding: 20px; }
    .container { max-width: 680px; margin: 0 auto; background: #ffffff; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); padding: 30px; border: 1px solid #e1e4e8; }
    h2 { border-bottom: 2px solid #ea4a5a; padding-bottom: 10px; font-weight: 600; font-size: 24px; margin-top: 0; }
    h3 { font-size: 18px; font-weight: 600; color: #24292f; margin-top: 25px; border-bottom: 1px solid #eaecef; padding-bottom: 8px; }
    .card { background: #f8f9fa; border: 1px solid #e1e4e8; border-radius: 8px; padding: 15px; margin-bottom: 15px; }
    .analyst-take { border-left: 4px solid #0366d6; background-color: #f1f8ff; padding: 12px 15px; margin: 15px 0; border-radius: 0 6px 6px 0; font-size: 14px; }
    table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 14px; }
    th { background-color: #f6f8fa; text-align: left; padding: 10px; color: #57606a; border-bottom: 1px solid #d0d7de; font-weight: 600; }
    td { padding: 10px; border-bottom: 1px solid #e1e4e8; }
    .positive { color: #1a7f37; font-weight: 600; }
    .negative { color: #d1242f; font-weight: 600; }
    .muted { color: #57606a; font-size: 13px; }
    a { color: #0969da; text-decoration: none; }
</style>
"""


def format_indian_markets(indices: dict) -> str:
    if not indices:
        return "<p class='muted'>Indian index data unavailable.</p>"
    html = "<table><tr><th>Index</th><th>Close</th><th>Chg %</th></tr>"
    for name in ["Nifty 50", "Sensex", "Bank Nifty", "Nifty Midcap 150", "India VIX"]:
        data = indices.get(name)
        if data:
            pct = data['pct_change']
            cls = "positive" if pct > 0 else "negative" if pct < 0 else ""
            html += (
                "<tr>"
                "<td><strong>" + name + "</strong></td>"
                "<td>&#8377;" + "{:,.2f}".format(data['close']) + "</td>"
                "<td class='" + cls + "'>" + "{:+.2f}".format(pct) + "%</td>"
                "</tr>"
            )
    html += "</table>"
    return html


def format_global_markets(markets: dict) -> str:
    if not markets:
        return "<p class='muted'>Global market data unavailable.</p>"
    html = "<table><tr><th>Market/Asset</th><th>Close</th><th>Chg %</th></tr>"
    for name, data in markets.items():
        if data:
            pct = data['pct_change']
            cls = "positive" if pct > 0 else "negative" if pct < 0 else ""
            html += (
                "<tr>"
                "<td>" + name + "</td>"
                "<td>" + "{:,.2f}".format(data['close']) + "</td>"
                "<td class='" + cls + "'>" + "{:+.2f}".format(pct) + "%</td>"
                "</tr>"
            )
    html += "</table>"
    return html


def format_news(news: list) -> str:
    if not news:
        return "<p class='muted'>No headlines available.</p>"
    html = "<ul style='padding-left: 20px; font-size: 14px;'>"
    for item in news:
        title = item.get("title", "")
        url = item.get("url", "#")
        src = item.get("source", "")
        html += (
            "<li style='margin-bottom: 8px;'>"
            "<a href='" + url + "'>" + title + "</a>"
            " <span class='muted'>(" + src + ")</span>"
            "</li>"
        )
    html += "</ul>"
    return html


def build_morning_brief() -> str:
    logger.info("Building Morning Brief...")

    # 1. Fetch Data
    upstox = UpstoxClient()
    indian_indices = upstox.get_index_quotes()
    global_markets = get_global_snapshot()
    news = get_market_news()

    # 2. AI Summary
    idx_str = "\n".join(
        "{}: {:.2f}%".format(k, v['pct_change'])
        for k, v in indian_indices.items() if v
    )
    news_str = "\n".join(n.get("title", "") for n in news)

    analyst = GeminiAnalyst()
    macro_take = analyst.get_market_summary(idx_str, news_str, "")

    # 3. Construct HTML
    today_str = datetime.now().strftime("%a, %d %b")

    html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    {css}
</head>
<body>
    <div class="container">
        <h2>&#127749; Morning Edge &mdash; {date}</h2>
        <p class='muted' style='margin-top: -10px;'>Overnight global cues and yesterday's Indian market recap.</p>

        <div class='analyst-take'>
            <strong>Analyst Macro Take:</strong><br/>
            {macro_take}
        </div>

        <h3>&#127757; Overnight Global Snapshot</h3>
        <div class="card">
            {global_markets}
        </div>

        <h3>&#9889; Yesterday's Recap (Indian Markets)</h3>
        <div class="card">
            {indian_markets}
        </div>

        <h3>&#128240; Top Market-Moving Headlines</h3>
        <div class="card">
            {news}
        </div>

        <div style="text-align: center; margin-top: 30px; font-size: 12px; color: #8c959f;">
            Generated by SM-Report AI Engine
        </div>
    </div>
</body>
</html>""".format(
        css=EMAIL_CSS,
        date=today_str,
        macro_take=macro_take,
        global_markets=format_global_markets(global_markets),
        indian_markets=format_indian_markets(indian_indices),
        news=format_news(news),
    )
    return html


def main():
    try:
        html_content = build_morning_brief()
        today_str = datetime.now().strftime("%a, %d %b")
        subject = "&#127749; Morning Edge: Global Cues & Action Plan \u2014 " + today_str

        success = send_html_email(subject, html_content)
        if success:
            logger.info("Morning brief sent successfully.")
            hc_uuid = os.environ.get("HEALTHCHECKS_UUID")
            if hc_uuid:
                requests.get("{}/{}".format(HEALTHCHECKS_BASE, hc_uuid), timeout=10)
        else:
            sys.exit(1)

    except Exception as exc:
        logger.error("Morning brief failed: %s", exc)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
