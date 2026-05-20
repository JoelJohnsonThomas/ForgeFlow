"""Notification helpers — Slack, etc. Used by both MCP tools and API handlers."""

from forgeflow.notifications.slack import (
    notify_approval_request,
    slack_post,
)

__all__ = ["notify_approval_request", "slack_post"]
