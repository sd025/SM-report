# Market Daily Report (SM-Report)

A fully automated, free daily pipeline that delivers two brutally honest equity-analyst-style market reports to your Gmail every weekday.

Built with:
- **Upstox API v3** (Free account, index quotes)
- **NSE Bhavcopy** (Full market EOD snapshot + Delivery %)
- **Gemini 1.5 Flash** (Analyst narrative)
- **NewsData.io** (Top headlines)
- **GitHub Actions** (Scheduler)

## Setup Guide

1. Fork or clone this repo.
2. Go to **Settings > Secrets and variables > Actions**.
3. Add the following secrets:
   - `UPSTOX_ACCESS_TOKEN`
   - `GEMINI_API_KEY`
   - `NEWSDATA_API_KEY`
   - `GMAIL_ADDRESS`
   - `GMAIL_APP_PASSWORD`
   - `HEALTHCHECKS_UUID` (optional)

4. Go to **Actions** tab in GitHub and manually trigger both the **Morning Brief** and **EOD Deep Dive** workflows to test them.

*(Note: Market cap constituent CSVs are auto-refreshed bi-weekly via GitHub Actions).*
