"""PII redactor — regex-based scrubbing for common personally-identifying data.

This is a defense-in-depth layer. It is intentionally conservative: false
positives (over-redacting) are preferred to false negatives (leaking PII).
For high-stakes compliance use, pair with a vendor solution like AWS Macie
or Google DLP.

Detected categories:
  - email      (RFC-5321-ish)
  - phone      (E.164 + common US formats)
  - ssn        (XXX-XX-XXXX)
  - credit_card (16-digit, Luhn-validated)
  - ipv4 / ipv6
  - api_key    (heuristic: sk_-, ghp_-, AKIA-, etc.)
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_EMAIL_RE = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
)
_PHONE_RE = re.compile(
    r"(?<!\d)(?:\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}(?!\d)"
)
_SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_CREDIT_CARD_RE = re.compile(r"\b(?:\d[ -]*?){13,19}\b")
_IPV4_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_IPV6_RE = re.compile(r"\b(?:[A-Fa-f0-9]{1,4}:){2,7}[A-Fa-f0-9]{1,4}\b")
_API_KEY_RE = re.compile(
    r"\b(?:sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{20,}|AKIA[A-Z0-9]{16}|"
    r"xox[abp]-[A-Za-z0-9-]{10,}|AIza[A-Za-z0-9_-]{20,})\b"
)


@dataclass(frozen=True)
class RedactionMatch:
    category: str
    start: int
    end: int
    original: str


def _luhn_valid(digits_only: str) -> bool:
    total = 0
    rev = digits_only[::-1]
    for i, ch in enumerate(rev):
        if not ch.isdigit():
            return False
        d = int(ch)
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0 and len(digits_only) >= 13


def redact(text: str) -> tuple[str, list[RedactionMatch]]:
    """Return a redacted copy of text plus the list of matches that were redacted.

    Replacement tokens use ``[REDACTED:<category>]`` so downstream consumers can
    still see *that* PII was present, but not the value.
    """
    if not text:
        return text, []

    matches: list[RedactionMatch] = []
    cursor_text = text

    patterns = [
        ("email", _EMAIL_RE),
        # api_key first — its alphanumeric runs often contain digit substrings
        # that the phone regex would otherwise eat.
        ("api_key", _API_KEY_RE),
        ("phone", _PHONE_RE),
        ("ssn", _SSN_RE),
        ("ipv6", _IPV6_RE),
        ("ipv4", _IPV4_RE),
    ]

    # Apply non-credit-card categories first (cheap, no validation step)
    for category, pattern in patterns:
        new_text, found = _apply_pattern(cursor_text, pattern, category)
        cursor_text = new_text
        matches.extend(found)

    # Credit cards last — needs Luhn validation to dodge false positives
    cc_matches: list[RedactionMatch] = []
    out_chunks = []
    last_end = 0
    for m in _CREDIT_CARD_RE.finditer(cursor_text):
        digits = re.sub(r"[ -]", "", m.group(0))
        if _luhn_valid(digits):
            out_chunks.append(cursor_text[last_end : m.start()])
            out_chunks.append("[REDACTED:credit_card]")
            cc_matches.append(
                RedactionMatch(
                    category="credit_card",
                    start=m.start(),
                    end=m.end(),
                    original=m.group(0),
                )
            )
            last_end = m.end()
    out_chunks.append(cursor_text[last_end:])
    if cc_matches:
        cursor_text = "".join(out_chunks)
        matches.extend(cc_matches)

    return cursor_text, matches


def _apply_pattern(
    text: str, pattern: re.Pattern[str], category: str
) -> tuple[str, list[RedactionMatch]]:
    found: list[RedactionMatch] = []
    replacement = f"[REDACTED:{category}]"

    def _sub(match: re.Match[str]) -> str:
        found.append(
            RedactionMatch(
                category=category,
                start=match.start(),
                end=match.end(),
                original=match.group(0),
            )
        )
        return replacement

    return pattern.sub(_sub, text), found
