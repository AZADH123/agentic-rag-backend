"""
Document parsers.

Each parser implements:
    parse(content: bytes, content_type: str) -> list[ParsedPage]

We deliberately preserve page boundaries (where the format supports them)
because the retrieval layer uses page numbers as citations.

Why return a list of pages instead of one big string:
- We can attach page metadata to chunks at index time.
- Citations can point users to "page 4" instead of just "this document".

For formats without page breaks (TXT), we synthesize a single page.
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Protocol

from app.core.exceptions import InvalidFileError


@dataclass
class ParsedPage:
    page: int
    text: str


class DocumentParser(Protocol):
    def parse(self, content: bytes, content_type: str) -> list[ParsedPage]:
        ...


class TxtParser:
    """Plain text. Encoded as one synthetic page."""

    def parse(self, content: bytes, content_type: str) -> list[ParsedPage]:
        # Try UTF-8, fall back to latin-1 (common for legacy .txt files).
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            text = content.decode("latin-1", errors="replace")
        return [ParsedPage(page=1, text=text)]


class PdfParser:
    """PDF via pypdf. Preserves page boundaries."""

    def parse(self, content: bytes, content_type: str) -> list[ParsedPage]:
        try:
            from pypdf import PdfReader
        except ImportError as e:
            raise ImportError("pypdf is required for PDF parsing") from e

        reader = PdfReader(io.BytesIO(content))
        pages: list[ParsedPage] = []
        for i, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            if text.strip():
                pages.append(ParsedPage(page=i, text=text))
        return pages


class DocxParser:
    """
    DOCX via python-docx. The format has no native pages — we approximate
    by splitting at section breaks and producing a 'page' per ~1000 chars.
    """

    def parse(self, content: bytes, content_type: str) -> list[ParsedPage]:
        try:
            from docx import Document
        except ImportError as e:
            raise ImportError("python-docx is required for DOCX parsing") from e

        doc = Document(io.BytesIO(content))
        full_text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
        if not full_text:
            return []
        # Crude pagination: ~1000 chars per "page" so citations have a number.
        page_size = 1000
        pages: list[ParsedPage] = []
        for i in range(0, len(full_text), page_size):
            pages.append(ParsedPage(page=len(pages) + 1, text=full_text[i:i + page_size]))
        return pages


_PARSERS: dict[str, DocumentParser] = {}


def _register_parsers() -> None:
    _PARSERS["application/pdf"] = PdfParser()
    _PARSERS["application/vnd.openxmlformats-officedocument.wordprocessingml.document"] = DocxParser()
    _PARSERS["text/plain"] = TxtParser()


_register_parsers()


def get_parser(content_type: str) -> DocumentParser:
    parser = _PARSERS.get(content_type)
    if parser is None:
        raise InvalidFileError(f"No parser for content type: {content_type}")
    return parser


def parse(content: bytes, content_type: str) -> list[ParsedPage]:
    """Dispatch to the correct parser based on content_type."""
    return get_parser(content_type).parse(content, content_type)