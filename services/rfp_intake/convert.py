"""PDF to Markdown conversion boundary."""

from __future__ import annotations

from pathlib import Path


def convert_pdf_to_markdown(pdf_path: Path, markdown_path: Path) -> str:
    """Convert the PDF before any classifier or worker sees its content."""

    try:
        from markitdown import MarkItDown
    except ImportError as exc:
        raise RuntimeError("MarkItDown is required to convert RFP PDFs to Markdown.") from exc

    try:
        result = MarkItDown().convert(str(pdf_path))
        markdown = result.text_content.strip()
    except Exception as exc:
        raise RuntimeError("The uploaded RFP PDF could not be converted to Markdown.") from exc

    if not markdown:
        raise ValueError("The uploaded RFP PDF contains no readable text.")

    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(markdown, encoding="utf-8")
    return markdown
