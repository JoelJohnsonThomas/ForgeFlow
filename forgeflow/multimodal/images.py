"""Image handling — data-URL encoding for vision LLMs + description helper.

The actual vision call goes through whichever LLM provider is selected by
forgeflow.models.get_model. Both ChatOpenAI (gpt-4o-class models) and
ChatAnthropic (claude-3.5+) accept the same image-content format that
LangChain normalises:

    HumanMessage(content=[
        {"type": "text",  "text": "What's in this image?"},
        {"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}}
    ])

This module hides the encoding behind a single helper so workflows don't
have to know which provider is active.
"""

from __future__ import annotations

import base64
import logging
import mimetypes
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage

logger = logging.getLogger(__name__)

SUPPORTED_MIME_PREFIXES = ("image/png", "image/jpeg", "image/webp", "image/gif")
MAX_IMAGE_BYTES = 20 * 1024 * 1024  # 20 MB — OpenAI's stated limit


@dataclass
class ImageDescription:
    """Vision-LLM description of an image."""
    description: str
    detected_objects: list[str]
    confidence: float                  # heuristic 0..1


def image_to_data_url(
    source: str | bytes | Path,
    mime_type: str | None = None,
) -> str:
    """Encode an image to a base64 data: URL the LLM providers accept.

    The data URL format is universal across OpenAI, Anthropic, and Ollama's
    vision models — no provider-specific shape needed.

    Args:
        source: file path, raw bytes, or Path
        mime_type: override the inferred MIME. Required when source is bytes
                   without a known extension.

    Raises:
        ValueError when source is too large or MIME is unsupported
    """
    if isinstance(source, (str, Path)):
        path = Path(source)
        data = path.read_bytes()
        if mime_type is None:
            mime_type, _ = mimetypes.guess_type(str(path))
    elif isinstance(source, bytes):
        data = source
    else:
        raise ValueError(f"unsupported image source type: {type(source).__name__}")

    if len(data) > MAX_IMAGE_BYTES:
        raise ValueError(
            f"image too large ({len(data)} bytes); max is {MAX_IMAGE_BYTES}"
        )

    if not mime_type:
        # Default to PNG; LLM providers tolerate the mismatch better than
        # an empty MIME, but log it so callers can fix the input.
        logger.warning("Could not infer image MIME; defaulting to image/png")
        mime_type = "image/png"

    if not any(mime_type.startswith(p) for p in SUPPORTED_MIME_PREFIXES):
        raise ValueError(
            f"unsupported image MIME '{mime_type}'; "
            f"must be one of: {SUPPORTED_MIME_PREFIXES}"
        )

    encoded = base64.b64encode(data).decode()
    return f"data:{mime_type};base64,{encoded}"


async def describe_image(
    source: str | bytes | Path,
    prompt: str = "Describe this image in detail. List the objects you see.",
    model: Any = None,
) -> ImageDescription:
    """Send an image to a vision-capable LLM and return its description.

    The model argument is optional — if omitted, the provider factory is
    consulted so workflows can call this from anywhere without threading
    a model handle through state.
    """
    if model is None:
        # Lazy import — avoids circular imports during package init
        from forgeflow.models import get_model
        model = get_model(strong=True)

    data_url = image_to_data_url(source)

    message = HumanMessage(
        content=[
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": data_url}},
        ]
    )

    try:
        response = await model.ainvoke([message])
    except Exception as exc:
        logger.exception("Vision LLM call failed: %s", exc)
        return ImageDescription(
            description=f"[error: {exc}]",
            detected_objects=[],
            confidence=0.0,
        )

    text = str(response.content) if hasattr(response, "content") else str(response)

    # Heuristic object extraction: split the response on common list separators
    # and keep short tokens. The model usually returns "I see X, Y, and Z" —
    # this catches the common phrasing without forcing structured output.
    objects = _extract_objects(text)

    return ImageDescription(
        description=text,
        detected_objects=objects,
        confidence=0.8 if objects else 0.5,
    )


def _extract_objects(text: str) -> list[str]:
    """Light heuristic — pull comma/list-separated nouns from a description.

    Not a real NER; just gives downstream code a structured-ish hint
    without forcing the model into a JSON schema (which would slow down
    streaming + add an output-token tax)."""
    if not text:
        return []
    # Look for "I see X, Y, and Z" or "Contains: X, Y, Z"
    import re

    for pattern in (
        r"(?:I\s+(?:can\s+)?see|contains?|includes?|including|features?|shows?)[:\s]+([^.]+)",
        r"objects?[:\s]+([^.]+)",
    ):
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            chunk = m.group(1)
            parts = re.split(r",|\band\b|\bor\b", chunk)
            results = [p.strip(" .;:") for p in parts if 1 <= len(p.strip()) <= 40]
            return [r for r in results if r]
    return []
