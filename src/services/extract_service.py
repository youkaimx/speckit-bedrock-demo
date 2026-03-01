"""Text extraction from PDF and Markdown for embedding. PDF via pypdf, Markdown as UTF-8 text."""

from io import BytesIO

from pypdf import PdfReader

from src.models.document import DocumentFormat


def extract_text(content: bytes, format: DocumentFormat) -> str:
    """
    Extract plain text from document content for embedding.
    PDF: uses pypdf to extract text from each page.
    Markdown: decoded as UTF-8 (raw text; embedding model accepts it).
    """
    if format == DocumentFormat.PDF:
        return _extract_pdf(content)
    if format == DocumentFormat.MARKDOWN:
        return _extract_markdown(content)
    raise ValueError(f"Unsupported format for extraction: {format}")


def _extract_pdf(content: bytes) -> str:
    """Extract text from PDF bytes using pypdf."""
    reader = PdfReader(BytesIO(content))
    parts = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            parts.append(text)
    return "\n\n".join(parts) if parts else ""


def _extract_markdown(content: bytes) -> str:
    """Decode Markdown as UTF-8 text. No markdown-to-HTML conversion; raw text for embedding."""
    return content.decode("utf-8", errors="replace")
