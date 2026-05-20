"""Prompt-injection guard.

Heuristic scanner that flags text likely to be a prompt-injection attempt.
This is a first line of defense, not a complete solution. Combine with:
  - strict role separation (system vs user messages)
  - LLM-side guardrails (e.g. Llama Guard, OpenAI moderation)
  - per-tenant rate limits

Three risk levels:
  - low      pass through
  - medium   pass through but log a warning
  - high     block at the API boundary (HTTP 400)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class RiskScore:
    level: RiskLevel
    reasons: list[str] = field(default_factory=list)


# Patterns are intentionally conservative — they target the most common
# jailbreak and instruction-override phrases observed in 2024-2026 attacks.
_HIGH_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "instruction_override",
        re.compile(
            r"\b(?:ignore|disregard|forget|override)\s+(?:all\s+)?(?:previous|prior|above|"
            r"earlier|the)\s+(?:instructions?|prompts?|rules?|guidelines?|directives?)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "role_takeover",
        re.compile(
            r"\b(?:you\s+are\s+now|act\s+as|pretend\s+to\s+be|roleplay\s+as)\s+(?:an?\s+)?"
            r"(?:unrestricted|jailbroken|dan|do\s+anything|developer\s+mode)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "system_prompt_leak",
        re.compile(
            r"\b(?:reveal|show|print|output|repeat|expose|leak)\s+(?:the\s+|your\s+)?"
            r"(?:system\s+prompt|initial\s+instructions?|hidden\s+rules?|"
            r"developer\s+message|api\s+keys?|secrets?|credentials?)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "credential_exfiltration",
        re.compile(
            r"\b(?:send|email|post|exfiltrate|dump)\s+(?:all\s+)?(?:api\s+keys?|"
            r"passwords?|tokens?|credentials?|secrets?)\s+(?:to|at)\b",
            re.IGNORECASE,
        ),
    ),
]

_MEDIUM_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "delimiter_injection",
        re.compile(r"(?:```|---|###)\s*(?:system|assistant|user)\s*[:>]", re.IGNORECASE),
    ),
    (
        "encoded_escape",
        re.compile(r"\\x[0-9a-f]{2}|\\u[0-9a-f]{4}|&#x?\d+;", re.IGNORECASE),
    ),
    (
        "long_repetition",
        re.compile(r"(.)\1{50,}"),
    ),
]


def scan_prompt(text: str) -> RiskScore:
    """Inspect a string for prompt-injection signals.

    Returns a RiskScore. Callers should:
      - block on HIGH
      - log + allow on MEDIUM
      - allow silently on LOW
    """
    if not text:
        return RiskScore(level=RiskLevel.LOW)

    reasons: list[str] = []

    for tag, pattern in _HIGH_PATTERNS:
        if pattern.search(text):
            reasons.append(tag)

    if reasons:
        return RiskScore(level=RiskLevel.HIGH, reasons=reasons)

    for tag, pattern in _MEDIUM_PATTERNS:
        if pattern.search(text):
            reasons.append(tag)

    if reasons:
        return RiskScore(level=RiskLevel.MEDIUM, reasons=reasons)

    return RiskScore(level=RiskLevel.LOW)
