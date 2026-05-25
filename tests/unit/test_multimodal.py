"""Tests for multimodal input — image data-URL encoding + PDF errors."""

from __future__ import annotations

import base64
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from forgeflow.multimodal.images import (
    MAX_IMAGE_BYTES,
    _extract_objects,
    describe_image,
    image_to_data_url,
)
from forgeflow.multimodal.pdf import PDFDocument, extract_pdf_text

# --------------------------------------------------------------------------
# image_to_data_url
# --------------------------------------------------------------------------

class TestDataURL:
    def test_bytes_with_explicit_mime(self):
        url = image_to_data_url(b"\x89PNG\r\n", mime_type="image/png")
        assert url.startswith("data:image/png;base64,")
        # Base64 chunk decodes back to the original bytes
        encoded = url.split(",", 1)[1]
        assert base64.b64decode(encoded) == b"\x89PNG\r\n"

    def test_path_with_inferred_mime(self, tmp_path):
        p = tmp_path / "test.jpeg"
        p.write_bytes(b"\xff\xd8\xff")  # JPEG magic bytes
        url = image_to_data_url(p)
        assert url.startswith("data:image/jpeg;base64,")

    def test_unsupported_mime_raises(self):
        with pytest.raises(ValueError, match="unsupported image MIME"):
            image_to_data_url(b"abc", mime_type="application/pdf")

    def test_oversize_raises(self):
        too_big = b"\x00" * (MAX_IMAGE_BYTES + 1)
        with pytest.raises(ValueError, match="too large"):
            image_to_data_url(too_big, mime_type="image/png")

    def test_unsupported_source_type_raises(self):
        with pytest.raises(ValueError, match="unsupported image source"):
            image_to_data_url(42)  # type: ignore[arg-type]


# --------------------------------------------------------------------------
# describe_image — the LLM is mocked; we verify call shape, not content
# --------------------------------------------------------------------------

class TestDescribeImage:
    @pytest.mark.asyncio
    async def test_calls_model_with_image_url_block(self):
        fake_model = MagicMock()
        fake_model.ainvoke = AsyncMock(return_value=MagicMock(content="A red apple"))

        result = await describe_image(
            source=b"\x89PNG\r\n",
            prompt="What's here?",
            model=fake_model,
        )

        # The call shape matters — both OpenAI and Anthropic understand it
        msg = fake_model.ainvoke.call_args[0][0][0]
        # HumanMessage.content is a list of blocks
        blocks = msg.content
        assert blocks[0] == {"type": "text", "text": "What's here?"}
        assert blocks[1]["type"] == "image_url"
        assert blocks[1]["image_url"]["url"].startswith("data:image/png;base64,")

        assert result.description == "A red apple"

    @pytest.mark.asyncio
    async def test_llm_failure_returns_error_description(self):
        fake_model = MagicMock()
        fake_model.ainvoke = AsyncMock(side_effect=RuntimeError("vision down"))

        result = await describe_image(
            source=b"\x89PNG\r\n", model=fake_model
        )
        assert "error" in result.description.lower()
        assert result.confidence == 0.0


# --------------------------------------------------------------------------
# _extract_objects — heuristic noun pull
# --------------------------------------------------------------------------

class TestExtractObjects:
    def test_pulls_comma_list_after_i_see(self):
        text = "I see a red apple, a green pear, and a banana."
        assert _extract_objects(text) == ["a red apple", "a green pear", "a banana"]

    def test_handles_includes_phrase(self):
        text = "The image includes laptop, coffee mug, and notebook."
        objs = _extract_objects(text)
        assert "laptop" in objs
        assert "coffee mug" in objs

    def test_empty_returns_empty(self):
        assert _extract_objects("") == []

    def test_no_match_returns_empty(self):
        assert _extract_objects("This is a beautiful day.") == []


# --------------------------------------------------------------------------
# extract_pdf_text — pypdf import is optional, mock the module
# --------------------------------------------------------------------------

class TestExtractPDF:
    def test_unsupported_source_raises_value_error(self):
        with pytest.raises(ValueError, match="unsupported PDF source"):
            extract_pdf_text(42)  # type: ignore[arg-type]

    def test_missing_pypdf_raises_helpful_import_error(self):
        with (
            patch.dict(sys.modules, {"pypdf": None}),
            pytest.raises(ImportError, match=r"forgeflow\[multimodal\]"),
        ):
            extract_pdf_text(b"%PDF-1.7")

    def test_with_mock_pypdf_returns_pages_and_metadata(self):
        # Build a fake pypdf module that returns 2 pages
        page1 = MagicMock()
        page1.extract_text = MagicMock(return_value="page one text")
        page2 = MagicMock()
        page2.extract_text = MagicMock(return_value="page two text")

        reader = MagicMock()
        reader.pages = [page1, page2]
        reader.metadata = {"/Title": "Demo", "/Author": "test"}

        fake_pypdf = MagicMock()
        fake_pypdf.PdfReader = MagicMock(return_value=reader)

        with patch.dict(sys.modules, {"pypdf": fake_pypdf}):
            doc = extract_pdf_text(b"%PDF-1.7 fake-bytes")

        assert doc.page_count == 2
        assert doc.pages == ["page one text", "page two text"]
        assert doc.text == "page one text\n\npage two text"
        assert doc.metadata["title"] == "Demo"
        assert doc.metadata["pages_extracted"] == 2

    def test_max_pages_truncates(self):
        pages = [MagicMock(extract_text=MagicMock(return_value=f"p{i}")) for i in range(5)]
        reader = MagicMock(pages=pages, metadata={})
        fake_pypdf = MagicMock(PdfReader=MagicMock(return_value=reader))

        with patch.dict(sys.modules, {"pypdf": fake_pypdf}):
            doc = extract_pdf_text(b"%PDF", max_pages=2)
        assert doc.pages == ["p0", "p1"]
        assert doc.metadata["pages_extracted"] == 2


# --------------------------------------------------------------------------
# PDFDocument.truncate_to
# --------------------------------------------------------------------------

class TestTruncate:
    def test_no_op_when_under_limit(self):
        doc = PDFDocument(page_count=1, text="hello")
        out = doc.truncate_to(100)
        assert out.text == "hello"
        assert "truncated_to_chars" not in out.metadata

    def test_clips_and_marks_metadata(self):
        doc = PDFDocument(page_count=1, text="hello world")
        out = doc.truncate_to(5)
        assert out.text == "hello"
        assert out.metadata["truncated_to_chars"] == 5
