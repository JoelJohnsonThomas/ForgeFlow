"""Opt-in anonymous telemetry emitter.

Design principles:

  1. **Off by default.** Settings.telemetry_enabled defaults to False.
     We never collect anything unless an operator explicitly opts in.
  2. **No PII.** Allowed event fields are constrained to an allowlist
     (event_name, workflow_type, version, etc.). User content, lead
     payloads, prompts, and LLM outputs are NEVER emitted.
  3. **No SaaS lock-in.** Events are POSTed to a configurable webhook
     (PostHog, Mixpanel, your own bucket). No vendor SDK dependency.
  4. **Fire-and-forget.** Network failures must never affect a workflow
     run. Errors are logged at debug-level and dropped.
  5. **Anonymous install ID.** A random UUID generated at first emit
     identifies an installation (not a user). Stored in
     settings.telemetry_install_id — operators can rotate or remove it.

Use this for: adoption metrics, error class counts, workflow-type
popularity, version distribution. Don't use it for: user behavior,
content analysis, anything that could deanonymize.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# Whitelist of fields allowed in an event. Anything else is dropped before
# emission. Keep this list short and review additions carefully.
_ALLOWED_FIELDS: frozenset[str] = frozenset({
    "event_name",         # required: 'workflow.started', 'connector.installed', etc.
    "workflow_type",      # sales_ops | support_ops | finance_recon
    "outcome",            # success | failure | partial
    "duration_ms",        # numeric — workflow latency bucketed at the caller
    "stage_reached",      # qualify | research | analyze | propose | approve | done
    "agent_name",         # supervisor | researcher | analyzer | executor
    "error_class",        # the exception class name — NOT the message (could contain PII)
    "llm_provider",       # openai | ollama | anthropic
    "tracing_provider",   # langsmith | phoenix | langfuse | none
    "events_provider",    # none | redis | kafka
    "version",            # ForgeFlow version string
    "python_version",     # major.minor
    "platform",           # linux | darwin | win32
})


@dataclass
class TelemetryEmitter:
    enabled: bool = False
    webhook_url: str = ""
    install_id: str = ""
    version: str = "0.1.0"
    timeout_seconds: float = 3.0
    # Internal — populated lazily
    _httpx: Any = field(default=None, repr=False)

    @classmethod
    def from_settings(cls) -> TelemetryEmitter:
        from forgeflow.config import get_settings
        settings = get_settings()
        install_id = settings.telemetry_install_id or str(uuid.uuid4())
        return cls(
            enabled=bool(settings.telemetry_enabled and settings.telemetry_webhook_url),
            webhook_url=settings.telemetry_webhook_url,
            install_id=install_id,
            version=settings.telemetry_version,
        )

    async def emit(self, **fields: Any) -> None:
        """Send an event. Always async-safe; never raises.

        Disallowed keys are silently dropped — keeps the emission site
        forgiving while still enforcing the PII boundary.
        """
        if not self.enabled or not self.webhook_url:
            return
        if "event_name" not in fields:
            logger.debug("telemetry: dropped event without event_name")
            return

        scrubbed: dict[str, Any] = {
            k: v for k, v in fields.items()
            if k in _ALLOWED_FIELDS and v is not None
        }
        # Always-on context fields
        scrubbed.setdefault("version", self.version)
        scrubbed["install_id"] = self.install_id

        try:
            import httpx
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                await client.post(
                    self.webhook_url,
                    json=scrubbed,
                    headers={"Content-Type": "application/json"},
                )
        except Exception as exc:
            # Telemetry must never break a workflow — degrade silently
            logger.debug("telemetry emit failed: %s", exc)

    def emit_sync(self, **fields: Any) -> None:
        """Convenience wrapper for non-async call sites. Runs the coroutine
        on a new event loop if there isn't a running one — used by CLI tools."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # We're inside an async context; schedule and forget
                loop.create_task(self.emit(**fields))
                return
        except RuntimeError:
            pass
        # No loop or stopped loop — run a fresh one synchronously
        try:
            asyncio.run(self.emit(**fields))
        except Exception as exc:
            logger.debug("telemetry emit_sync failed: %s", exc)


_singleton: TelemetryEmitter | None = None


def get_emitter() -> TelemetryEmitter:
    global _singleton
    if _singleton is None:
        _singleton = TelemetryEmitter.from_settings()
    return _singleton


async def emit(**fields: Any) -> None:
    """Module-level shortcut so call sites don't have to manage the singleton."""
    await get_emitter().emit(**fields)
