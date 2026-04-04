"""Universal data source ingestor."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional
from dataclasses import dataclass


@dataclass
class IngestorResult:
    """Result from data ingestion."""
    source_uri: str
    records_extracted: int
    dedup_skipped: int
    extraction_log: str
    raw_content: str


class UniversalIngestor:
    """Extracts data from multiple source types: PDF, web, API, files."""
    
    def __init__(self) -> None:
        self.dedup_cache = {}
    
    async def extract(
        self,
        sources: list[str],
        dedup: bool = True,
        tag: str | None = None,
    ) -> dict:
        """
        Extract from sources in format:
        - file:///path/to/papers/*.pdf
        - web://arxiv.org/list/ai
        - api://https://api.example.com/research
        """
        results = {
            "sources": sources,
            "records_extracted": 0,
            "dedup_skipped": 0,
            "extractions": [],
            "tag": tag or "default",
        }
        
        for source_uri in sources:
            try:
                if source_uri.startswith("file://"):
                    result = await self._extract_files(source_uri, dedup)
                elif source_uri.startswith("web://"):
                    result = await self._extract_web(source_uri, dedup)
                elif source_uri.startswith("api://"):
                    result = await self._extract_api(source_uri, dedup)
                else:
                    print(f"[Ingestor] Unknown source type: {source_uri}")
                    continue
                
                results["records_extracted"] += result.records_extracted
                results["dedup_skipped"] += result.dedup_skipped
                results["extractions"].append({
                    "source": result.source_uri,
                    "records": result.records_extracted,
                    "skipped": result.dedup_skipped,
                })
            except Exception as e:
                print(f"[Ingestor] Error extracting {source_uri}: {e}")
        
        return results
    
    async def _extract_files(self, file_uri: str, dedup: bool) -> IngestorResult:
        """Extract from local files (PDF, TXT, etc)."""
        import glob
        from pathlib import Path
        
        # Parse file:///path/to/pattern format
        file_path = file_uri.replace("file://", "")
        extraction_log = []
        raw_content = ""
        records_extracted = 0
        dedup_skipped = 0
        
        try:
            # Support glob patterns
            matching_files = glob.glob(file_path)
            if not matching_files:
                return IngestorResult(
                    source_uri=file_uri,
                    records_extracted=0,
                    dedup_skipped=0,
                    extraction_log=f"No files matched pattern: {file_path}",
                    raw_content="",
                )
            
            for file in matching_files:
                try:
                    if file.endswith(".pdf"):
                        # PDF extraction (requires pypdf)
                        try:
                            import PyPDF2
                            with open(file, "rb") as f:
                                reader = PyPDF2.PdfReader(f)
                                for page_num, page in enumerate(reader.pages):
                                    text = page.extract_text()
                                    if text.strip():
                                        raw_content += f"\n\n--- PDF {Path(file).name} Page {page_num + 1} ---\n{text}"
                                        records_extracted += 1
                                extraction_log.append(f"✓ Extracted {len(reader.pages)} pages from {Path(file).name}")
                        except ImportError:
                            extraction_log.append(f"⚠ PyPDF2 not installed, skipping {Path(file).name}")
                    
                    elif file.endswith((".txt", ".md")):
                        # Text file extraction
                        with open(file, "r", encoding="utf-8") as f:
                            text = f.read().strip()
                            if text:
                                # Check dedup
                                content_hash = self.dedup_cache.compute_hash(text) if hasattr(self, 'dedup_cache') else None
                                if dedup and content_hash and content_hash in getattr(self, '_extracted_hashes', set()):
                                    dedup_skipped += 1
                                    extraction_log.append(f"⟳ Dedup: {Path(file).name}")
                                else:
                                    raw_content += f"\n\n--- {Path(file).name} ---\n{text}"
                                    records_extracted += 1
                                    if hasattr(self, '_extracted_hashes'):
                                        self._extracted_hashes.add(content_hash)
                                extraction_log.append(f"✓ Read {Path(file).name} ({len(text)} chars)")
                except Exception as e:
                    extraction_log.append(f"✗ Error reading {file}: {type(e).__name__}")
        
        except Exception as e:
            extraction_log.append(f"✗ File extraction failed: {type(e).__name__}: {e}")
        
        return IngestorResult(
            source_uri=file_uri,
            records_extracted=records_extracted,
            dedup_skipped=dedup_skipped,
            extraction_log="\n".join(extraction_log),
            raw_content=raw_content,
        )
    
    async def _extract_web(self, web_uri: str, dedup: bool) -> IngestorResult:
        """Extract from web sources (ArXiv, websites, etc)."""
        # TODO: Implement web scraping
        return IngestorResult(
            source_uri=web_uri,
            records_extracted=0,
            dedup_skipped=0,
            extraction_log="Web extraction not yet implemented",
            raw_content="",
        )
    
    async def _extract_api(self, api_uri: str, dedup: bool) -> IngestorResult:
        """Extract from API endpoints."""
        # TODO: Implement API data fetching
        return IngestorResult(
            source_uri=api_uri,
            records_extracted=0,
            dedup_skipped=0,
            extraction_log="API extraction not yet implemented",
            raw_content="",
        )
