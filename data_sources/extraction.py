"""Data extraction and structure building."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ExtractedContent:
    source_id: str
    title: str | None
    authors: list[str]
    publication_date: str | None
    content: str
    sections: dict[str, str]
    metadata: dict


class DataExtractor:
    def extract(self, raw_content: str, source_type: str) -> ExtractedContent:
        return ExtractedContent(
            source_id="extracted_001",
            title=None,
            authors=[],
            publication_date=None,
            content=raw_content,
            sections={},
            metadata={"source_type": source_type},
        )
