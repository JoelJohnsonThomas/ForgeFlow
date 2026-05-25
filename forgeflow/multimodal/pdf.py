"""PDF text + metadata extraction.

Uses pypdf (pure-Python, MIT, ships in the optional [multimodal] extra).
We deliberately don't pull in heavier dependencies (PyMuPDF requires
native libs and is AGPL-licensed) because the goal here is text + simple
metadata, not OCR or layout reconstruction.

For scanned PDFs (no embedded text), this module returns whatever pypdf
extracts — typically empty pages. Wiring OCR (tesseract, PaddleOCR) is
tracked in ROADMAP as a follow-up.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class PDFDocument:
    """Lightweight representation of a parsed PDF."""
    page_count: int
    text: str                                # full document text joined with \n\n
    pages: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def char_count(self) -> int:
        return len(self.text)

    def truncate_to(self, max_chars: int) -> PDFDocument:
        """Return a copy truncated to max_chars — used to fit LLM context budgets."""
        if self.char_count <= max_chars:
            return self
        return PDFDocument(
            page_count=self.page_count,
            text=self.text[:max_chars],
            pages=self.pages,
            metadata={**self.metadata, "truncated_to_chars": max_chars},
        )


def extract_pdf_text(
    source: str | bytes | Path,
    max_pages: int | None = None,
) -> PDFDocument:
    """Extract text + metadata from a PDF.

    Args:
        source: file path, raw bytes, or pathlib.Path
        max_pages: stop after this many pages (None = whole doc)

    Returns:
        PDFDocument with text, per-page text, metadata, and page_count.

    Raises:
        ImportError when pypdf isn't installed
        ValueError when the input isn't a parseable PDF
    """
    try:
        import pypdf
    except ImportError as exc:
        raise ImportError(
            "PDF support requires the 'multimodal' extra. "
            "Install with: pip install 'forgeflow[multimodal]'"
        ) from exc

    # Resolve source -> file-like. Use a context-managed open() for paths;
    # bytes get a nullcontext around a BytesIO that doesn't need closing.
    import io
    from contextlib import nullcontext

    if isinstance(source, (str, Path)):
        ctx: Any = open(source, "rb")  # noqa: SIM115  managed by the `with` below
    elif isinstance(source, bytes):
        ctx = nullcontext(io.BytesIO(source))
    else:
        raise ValueError(f"unsupported PDF source type: {type(source).__name__}")

    with ctx as fh:
        try:
            reader = pypdf.PdfReader(fh)
        except Exception as exc:
            raise ValueError(f"failed to parse PDF: {exc}") from exc

        page_count = len(reader.pages)
        limit = page_count if max_pages is None else min(max_pages, page_count)
        pages: list[str] = []

        for i in range(limit):
            try:
                pages.append(reader.pages[i].extract_text() or "")
            except Exception as exc:
                logger.warning("PDF page %d extraction failed: %s", i, exc)
                pages.append("")

        meta = reader.metadata or {}
        metadata = {
            "title":    str(meta.get("/Title", "")) if meta else "",
            "author":   str(meta.get("/Author", "")) if meta else "",
            "subject":  str(meta.get("/Subject", "")) if meta else "",
            "producer": str(meta.get("/Producer", "")) if meta else "",
            "pages_extracted": limit,
        }

        return PDFDocument(
            page_count=page_count,
            text="\n\n".join(pages),
            pages=pages,
            metadata=metadata,
        )
