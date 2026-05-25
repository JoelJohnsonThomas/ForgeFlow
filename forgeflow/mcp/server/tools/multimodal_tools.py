"""MCP tools for multi-modal input — PDF extraction + image description."""

from __future__ import annotations

import base64
import logging

from fastmcp import FastMCP

logger = logging.getLogger(__name__)
router = FastMCP("multimodal-tools")


@router.tool()
async def extract_pdf(
    source_bytes_base64: str,
    max_pages: int | None = None,
    truncate_chars: int | None = 50_000,
) -> dict:
    """Extract text + metadata from a PDF passed as a base64-encoded blob.

    MCP tools can't pass raw bytes natively; clients base64-encode the
    PDF before calling. The default truncate_chars cap keeps the result
    inside typical LLM context windows.
    """
    try:
        from forgeflow.multimodal.pdf import extract_pdf_text
    except ImportError as exc:
        return {"error": str(exc), "mock": True}

    try:
        data = base64.b64decode(source_bytes_base64)
    except Exception as exc:
        return {"error": f"invalid base64: {exc}"}

    try:
        doc = extract_pdf_text(data, max_pages=max_pages)
    except (ImportError, ValueError) as exc:
        return {"error": str(exc)}

    if truncate_chars:
        doc = doc.truncate_to(truncate_chars)

    return {
        "page_count": doc.page_count,
        "char_count": doc.char_count,
        "text": doc.text,
        "metadata": doc.metadata,
    }


@router.tool()
async def describe_image(
    source_bytes_base64: str,
    mime_type: str = "image/png",
    prompt: str = "Describe this image in detail. List the objects you see.",
) -> dict:
    """Send an image to a vision-capable LLM and return its description.

    The image is base64-encoded by the client; this tool re-encodes it
    as a data URL and routes the request through the configured LLM
    provider (OpenAI / Anthropic / Ollama vision models).
    """
    try:
        from forgeflow.multimodal.images import describe_image as _describe
    except ImportError as exc:
        return {"error": str(exc), "mock": True}

    try:
        data = base64.b64decode(source_bytes_base64)
    except Exception as exc:
        return {"error": f"invalid base64: {exc}"}

    # The image helper accepts bytes directly and picks the MIME from the
    # caller-provided hint.
    try:
        from forgeflow.multimodal.images import image_to_data_url

        # Validate up front so we surface bad MIME / size errors clearly
        image_to_data_url(data, mime_type=mime_type)
    except ValueError as exc:
        return {"error": str(exc)}

    result = await _describe(source=data, prompt=prompt)
    return {
        "description": result.description,
        "detected_objects": result.detected_objects,
        "confidence": result.confidence,
    }
