"""Universal data source ingestor."""

from __future__ import annotations

import asyncio
import glob
import html
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import httpx

from .cache import DeduplicationCache


@dataclass
class IngestorResult:
    source_uri: str
    records_extracted: int
    dedup_skipped: int
    extraction_log: str
    raw_content: str


class UniversalIngestor:
    def __init__(self) -> None:
        self.dedup_cache = DeduplicationCache()
        self._extracted_hashes: set[str] = set()

    async def extract(self, sources: list[str], dedup: bool = True, tag: str | None = None) -> dict:
        results = {"sources": sources, "records_extracted": 0, "dedup_skipped": 0, "extractions": [], "tag": tag or "default", "raw_content": "", "extraction_log": ""}
        logs: list[str] = []
        for source_uri in sources:
            if source_uri.startswith("file://"):
                result = await self._extract_files(source_uri, dedup)
            elif source_uri.startswith(("http://", "https://", "web://")):
                result = await self._extract_web(source_uri, dedup)
            elif source_uri.startswith("api://"):
                result = await self._extract_api(source_uri, dedup)
            else:
                result = IngestorResult(source_uri, 0, 0, f"Unsupported source: {source_uri}", "")
            results["records_extracted"] += result.records_extracted
            results["dedup_skipped"] += result.dedup_skipped
            results["raw_content"] += result.raw_content
            results["extractions"].append({"source": result.source_uri, "records": result.records_extracted, "skipped": result.dedup_skipped})
            logs.append(result.extraction_log)
        results["extraction_log"] = "\n".join(logs)
        return results

    async def _extract_files(self, file_uri: str, dedup: bool) -> IngestorResult:
        path = file_uri.replace("file://", "")
        matches = glob.glob(path)
        logs: list[str] = []
        raw_content = ""
        records_extracted = 0
        dedup_skipped = 0
        for match in matches:
            file_path = Path(match)
            if file_path.suffix.lower() == ".pdf":
                try:
                    import pypdf
                    reader = pypdf.PdfReader(str(file_path))
                    for page_index, page in enumerate(reader.pages):
                        text = (page.extract_text() or "").strip()
                        if not text:
                            continue
                        content_hash = self.dedup_cache.compute_hash(text)
                        if dedup and content_hash in self._extracted_hashes:
                            dedup_skipped += 1
                            continue
                        self._extracted_hashes.add(content_hash)
                        raw_content += f"\n\n--- {file_path.name} page {page_index + 1} ---\n{text}"
                        records_extracted += 1
                    logs.append(f"PDF {file_path.name}: {len(reader.pages)} pages")
                except Exception as exc:
                    logs.append(f"PDF {file_path.name}: {type(exc).__name__}")
            elif file_path.suffix.lower() in {".txt", ".md", ".json", ".csv"}:
                text = file_path.read_text(encoding="utf-8", errors="ignore").strip()
                if not text:
                    continue
                content_hash = self.dedup_cache.compute_hash(text)
                if dedup and content_hash in self._extracted_hashes:
                    dedup_skipped += 1
                    continue
                self._extracted_hashes.add(content_hash)
                raw_content += f"\n\n--- {file_path.name} ---\n{text}"
                records_extracted += 1
                logs.append(f"Text {file_path.name}: {len(text)} chars")
        return IngestorResult(file_uri, records_extracted, dedup_skipped, "\n".join(logs), raw_content)

    async def _extract_web(self, web_uri: str, dedup: bool) -> IngestorResult:
        url = web_uri.replace("web://", "https://", 1) if web_uri.startswith("web://") else web_uri
        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True, headers={"User-Agent": "Hexamind/1.0"}) as client:
                response = await client.get(url)
                response.raise_for_status()
                text = self._strip_html(response.text)
                content_hash = self.dedup_cache.compute_hash(text)
                if dedup and content_hash in self._extracted_hashes:
                    return IngestorResult(web_uri, 0, 1, f"Deduplicated web source: {web_uri}", "")
                self._extracted_hashes.add(content_hash)
                return IngestorResult(web_uri, 1, 0, f"Fetched web source: {web_uri}", text)
        except Exception as exc:
            return IngestorResult(web_uri, 0, 0, f"Web extraction failed: {type(exc).__name__}: {exc}", "")

    async def _extract_api(self, api_uri: str, dedup: bool) -> IngestorResult:
        endpoint = api_uri.replace("api://", "https://", 1) if api_uri.startswith("api://") else api_uri
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(endpoint)
                response.raise_for_status()
                payload_text = response.text.strip()
                content_hash = self.dedup_cache.compute_hash(payload_text)
                if dedup and content_hash in self._extracted_hashes:
                    return IngestorResult(api_uri, 0, 1, f"Deduplicated API source: {api_uri}", "")
                self._extracted_hashes.add(content_hash)
                return IngestorResult(api_uri, 1, 0, f"Fetched API source: {api_uri}", payload_text)
        except Exception as exc:
            return IngestorResult(api_uri, 0, 0, f"API extraction failed: {type(exc).__name__}: {exc}", "")

    def _strip_html(self, text: str) -> str:
        from html.parser import HTMLParser

        class _Stripper(HTMLParser):
            def __init__(self) -> None:
                super().__init__()
                self.parts: list[str] = []
            def handle_data(self, data: str) -> None:
                self.parts.append(data)
        stripper = _Stripper()
        stripper.feed(text)
        return html.unescape(" ".join(stripper.parts))
