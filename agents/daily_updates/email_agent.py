import logging
import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, Any, Optional
from shared.base_agent import BaseAgent, AgentResult, AgentStatus
from shared.llm import generate_content_with_failover

logger = logging.getLogger("EmailAgent")

class EmailAgent(BaseAgent):
    """
    Generates and dispatches daily executive briefing emails summarizing system status,
    job search results, market movements, and pending approval queues.
    """
    def __init__(self):
        super().__init__(name="EmailAgent")
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", 587))
        self.smtp_user = os.getenv("SMTP_USER")
        self.smtp_pass = os.getenv("SMTP_PASS")
        self.recipient = os.getenv("ALERT_EMAIL_RECIPIENT", self.smtp_user)

    def build_briefing_html(self, briefing_text: str) -> str:
        """Wraps markdown/plain summary in a clean responsive HTML email template."""
        formatted_content = briefing_text.replace(chr(10), "<br/>")
        return f"""<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; line-height: 1.6; color: #2D3748; background-color: #F7FAFC; padding: 20px; }}
        .container {{ max-width: 600px; margin: 0 auto; background: #FFFFFF; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }}
        .header {{ background-color: #1A365D; color: #FFFFFF; padding: 24px; text-align: center; }}
        .content {{ padding: 24px; }}
        .footer {{ background-color: #EDF2F7; padding: 16px; text-align: center; font-size: 12px; color: #718096; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2 style="margin:0;">⚡ Chronos Daily Executive Briefing</h2>
        </div>
        <div class="content">
            {formatted_content}
        </div>
        <div class="footer">
            Generated autonomously by Chronos Multi-Agent Operating System
        </div>
    </div>
</body>
</html>
"""

    async def generate_daily_digest(self, context_data: Optional[Dict[str, Any]] = None) -> str:
        context_str = str(context_data or {})
        prompt = f"""
You are the Executive Chief of Staff AI for an ambitious Software Engineer & Trader.
Generate a concise, motivating, and actionable Daily Morning Executive Briefing.

Operational Context:
{context_str}

Include:
1. 🎯 Top 3 Priorities for Today
2. 💼 Job Radar & Career Automation Update
3. 📈 Macro Market & Trading Session Outlook
4. 🤖 Agent Daemon Health & Memory Status

Keep it punchy, well-structured, and inspiring.
"""
        response = generate_content_with_failover(prompt_text=prompt)
        return response.text.strip()

    async def execute(self, payload: Optional[Dict[str, Any]] = None) -> AgentResult:
        digest = await self.generate_daily_digest(payload)
        html_body = self.build_briefing_html(digest)
        
        # If SMTP is configured and not DRY_RUN, send email
        smtp_configured = bool(self.smtp_user and self.smtp_pass and self.recipient)
        if smtp_configured and not os.getenv("DRY_RUN", "false").lower() in ("true", "1"):
            try:
                msg = MIMEMultipart("alternative")
                msg["Subject"] = "⚡ Chronos Daily Morning Briefing"
                msg["From"] = self.smtp_user
                msg["To"] = self.recipient
                msg.attach(MIMEText(html_body, "html"))

                with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                    server.starttls()
                    server.login(self.smtp_user, self.smtp_pass)
                    server.send_message(msg)
                self.logger.info(f"Briefing email successfully sent to {self.recipient}")
            except Exception as e:
                self.logger.error(f"Failed to send SMTP email: {e}")

        return AgentResult(
            status=AgentStatus.SUCCESS,
            data={
                "digest_text": digest,
                "html_body": html_body,
                "dispatched": smtp_configured
            }
        )
