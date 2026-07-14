"""
email_sender.py — Sends styled HTML emails via Gmail SMTP using an App Password.
"""

import logging
import os
import smtplib
from email.message import EmailMessage
from typing import Optional

logger = logging.getLogger(__name__)

# Fallback basic HTML structure if templates aren't fully baked
BASIC_HTML_WRAPPER = """
<!DOCTYPE html>
<html>
<head>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: 0 auto; padding: 20px; }}
  h2 {{ border-bottom: 2px solid #eaecef; padding-bottom: 0.3em; margin-top: 1.5em; }}
  table {{ border-collapse: collapse; width: 100%; margin-bottom: 1em; }}
  th, td {{ border: 1px solid #dfe2e5; padding: 6px 13px; text-align: left; }}
  th {{ background-color: #f6f8fa; }}
  .positive {{ color: #22863a; font-weight: bold; }}
  .negative {{ color: #cb2431; font-weight: bold; }}
  .muted {{ color: #6a737d; font-size: 0.9em; }}
  .analyst-take {{ background-color: #f1f8ff; border-left: 4px solid #0366d6; padding: 10px 15px; margin: 10px 0; }}
</style>
</head>
<body>
  {content}
</body>
</html>
"""


def send_html_email(subject: str, html_content: str) -> bool:
    """
    Sends an HTML email using Gmail SMTP.
    Requires GMAIL_ADDRESS and GMAIL_APP_PASSWORD env vars.
    """
    sender_email = os.environ.get("GMAIL_ADDRESS")
    app_password = os.environ.get("GMAIL_APP_PASSWORD")

    if not sender_email or not app_password:
        logger.error("Email credentials missing. Set GMAIL_ADDRESS and GMAIL_APP_PASSWORD.")
        return False

    # Wrap raw HTML if it doesn't look like a full document
    if "<html" not in html_content.lower():
        html_content = BASIC_HTML_WRAPPER.format(content=html_content)

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender_email
    msg["To"] = sender_email  # Send to self
    
    # Optional: If you want to CC others, you can add msg["Cc"] = "..."
    
    msg.set_content("Please enable HTML to view this email.") # Plaintext fallback
    msg.add_alternative(html_content, subtype='html')

    try:
        logger.info("Connecting to smtp.gmail.com...")
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, app_password)
            server.send_message(msg)
        logger.info("Email sent successfully: %s", subject)
        return True
    except smtplib.SMTPAuthenticationError:
        logger.error("SMTP Auth failed. Check GMAIL_APP_PASSWORD.")
        return False
    except Exception as exc:
        logger.error("Failed to send email: %s", exc)
        return False
