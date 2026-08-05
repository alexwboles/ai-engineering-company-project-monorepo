"""HealthCore knowledge-base loading and semantic Markdown chunking."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any


HEALTHCORE_COMPANY = "HealthCore"
HEALTHCORE_LANGUAGE = "en"
DEFAULT_CORPUS_DIR = Path(__file__).resolve().parents[2] / "docs" / "company-knowledge-base"


def load_documents(corpus_dir: Path | str = DEFAULT_CORPUS_DIR) -> list[dict[str, str]]:
    """Read the approved HealthCore Markdown corpus in deterministic order."""

    root = Path(corpus_dir)
    return [
        {"source_document": path.name, "text": path.read_text(encoding="utf-8")}
        for path in sorted(root.glob("*.md"))
    ]


def chunk_documents(
    documents: list[dict[str, str]],
    *,
    company: str = HEALTHCORE_COMPANY,
    language: str = HEALTHCORE_LANGUAGE,
) -> list[dict[str, Any]]:
    """Split Markdown at headings while keeping each policy section intact.

    The corpus is intentionally small and policy-heavy. Heading boundaries are
    safer than fixed character windows because they avoid separating a rule
    from its scope or exception. A long section is split only at paragraph
    boundaries, never in the middle of a paragraph.
    """

    chunks: list[dict[str, Any]] = []
    for document in documents:
        source_document = document["source_document"]
        sections = _sections(document["text"])
        for section_index, section in enumerate(sections):
            heading = section["heading"] or "Overview"
            paragraphs = [part.strip() for part in section["body"].split("\n\n") if part.strip()]
            current: list[str] = []
            current_words = 0
            part_index = 0
            for paragraph in paragraphs:
                paragraph_words = len(paragraph.split())
                if current and current_words + paragraph_words > 220:
                    chunks.append(_payload(source_document, heading, company, language, section_index, part_index, current))
                    current = []
                    current_words = 0
                    part_index += 1
                current.append(paragraph)
                current_words += paragraph_words
            if current:
                chunks.append(_payload(source_document, heading, company, language, section_index, part_index, current))

    for index, chunk in enumerate(chunks):
        chunk["chunk_index"] = index
    return chunks


def build_healthcore_chunks(corpus_dir: Path | str = DEFAULT_CORPUS_DIR) -> list[dict[str, Any]]:
    """Load and chunk the HealthCore source corpus used by ``setup``."""

    return chunk_documents(load_documents(corpus_dir))


def _sections(markdown: str) -> list[dict[str, str]]:
    matches = list(re.finditer(r"(?m)^(#{1,3})\s+(.+?)\s*$", markdown))
    if not matches:
        return [{"heading": "Overview", "body": markdown.strip()}]

    sections: list[dict[str, str]] = []
    preamble = markdown[: matches[0].start()].strip()
    if preamble:
        sections.append({"heading": "Overview", "body": preamble})
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(markdown)
        body = markdown[match.end() : end].strip()
        if body:
            sections.append({"heading": match.group(2).strip(), "body": body})
    return sections


def _payload(
    source_document: str,
    section: str,
    company: str,
    language: str,
    section_index: int,
    part_index: int,
    paragraphs: list[str],
) -> dict[str, Any]:
    return {
        "source_document": source_document,
        "section": section,
        "company": company,
        "language": language,
        "chunk_index": section_index * 1000 + part_index,
        "text": "\n\n".join(paragraphs),
    }
