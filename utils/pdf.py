"""
Extract plain text from uploaded PDFs for use as model context.

Uses pypdf; scanned-only documents without a text layer will fail with a clear error.
"""

from __future__ import annotations

from io import BytesIO

from pypdf import PdfReader

import config as app_config
from agent.errors import StudyAgentError


def extract_text_from_pdf(
    file_bytes: bytes,
    *,
    max_pages: int | None = None,
    max_chars: int | None = None,
) -> str:
    """
    Extract text from a PDF with page and character caps from config by default.

    Raises:
        StudyAgentError: Empty file, unreadable PDF, encryption, or no extractable text.
    """
    max_pages = max_pages if max_pages is not None else app_config.PDF_MAX_PAGES
    max_chars = max_chars if max_chars is not None else app_config.PDF_MAX_CHARS

    if not file_bytes:
        raise StudyAgentError("The uploaded PDF file is empty.")

    try:
        reader = PdfReader(BytesIO(file_bytes))
    except Exception as exc:  # noqa: BLE001 — pypdf may raise varied types
        raise StudyAgentError(
            "Could not read this PDF. It may be corrupted or not a valid PDF."
        ) from exc

    if reader.is_encrypted:
        raise StudyAgentError(
            "This PDF appears to be password-protected. Please upload an unlocked file."
        )

    parts: list[str] = []
    n = min(len(reader.pages), max_pages)
    for i in range(n):
        try:
            page = reader.pages[i]
            text = page.extract_text() or ""
        except Exception as exc:  # noqa: BLE001
            raise StudyAgentError(f"Could not read page {i + 1} of the PDF.") from exc
        if text.strip():
            parts.append(text)

    full = "\n\n".join(parts).strip()
    if not full:
        raise StudyAgentError(
            "No text could be extracted from this PDF. Scanned image-only PDFs need OCR "
            "outside this app, or try a text-based export."
        )

    if len(full) > max_chars:
        full = (
            full[:max_chars]
            + "\n\n[…truncated: only the beginning was sent to stay within size limits.]"
        )

    return full
