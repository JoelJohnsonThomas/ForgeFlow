"""MCP tools: email drafting and sending (mock SMTP — swap for SendGrid/SES in prod)."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from fastmcp import FastMCP

logger = logging.getLogger(__name__)

router = FastMCP("email-tools")

# Sent emails log (replace with real email provider in production)
_sent_emails: list[dict] = []


@router.tool()
async def draft_email(
    to: str,
    subject: str,
    context: str,
    tone: str = "professional",
) -> dict:
    """Generate an email draft using the provided context.

    Args:
        to: Recipient email address
        subject: Email subject line
        context: Key points and information to include
        tone: Writing tone — professional | friendly | formal

    Returns:
        Email draft with subject and body
    """
    # In production this would call an LLM or email template engine
    body = f"""Dear {to.split('@')[0].replace('.', ' ').title()},

I hope this message finds you well.

{context}

I'd love to schedule a brief 30-minute conversation to learn more about your
goals and share how ForgeFlow's enterprise AI platform could accelerate your outcomes.

Are you available for a call this week or next?

Best regards,
ForgeFlow Sales Team
sales@forgeflow.ai | calendly.com/forgeflow"""

    draft = {
        "to": to,
        "subject": subject,
        "body": body,
        "tone": tone,
        "draft_id": str(uuid.uuid4()),
        "created_at": datetime.now(UTC).isoformat(),
    }
    logger.info("Email drafted for %s | subject: %s", to, subject)
    return draft


@router.tool()
async def send_email(
    to: str,
    subject: str,
    body: str,
    allowed_domains: list[str],
    cc: list[str] | None = None,
) -> dict:
    """Send an email — requires an explicit recipient-domain allowlist.

    The orchestrator (Executor agent) must supply `allowed_domains` from the
    workspace settings. We refuse the send if `to` (or any cc) doesn't match
    the list. This closes the LLM-controlled exfil channel called out in
    SECURITY_AUDIT.md C-5.

    Args:
        to: Primary recipient email
        subject: Email subject line
        body: Full email body text
        allowed_domains: fnmatch patterns the recipient must satisfy
        cc: Optional CC recipients
    """
    from forgeflow.security.email_allowlist import EmailNotAllowed, require_allowed

    recipients = [to] + list(cc or [])
    try:
        for r in recipients:
            require_allowed(r, allowed_domains)
    except EmailNotAllowed as exc:
        logger.warning("Refusing send_email: %s", exc)
        return {"success": False, "error": str(exc)}

    message_id = str(uuid.uuid4())
    record = {
        "message_id": message_id,
        "to": to,
        "cc": cc or [],
        "subject": subject,
        "body": body[:200] + "...",
        "sent_at": datetime.now(UTC).isoformat(),
        "status": "sent",
    }
    _sent_emails.append(record)
    logger.info("Email sent | to=%s | subject=%s | id=%s", to, subject, message_id)
    return {"success": True, "message_id": message_id, "sent_at": record["sent_at"]}
