from __future__ import annotations

import html as html_lib
import os
import re
import time
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Iterable
from urllib.parse import parse_qs, unquote, urljoin, urlparse

import httpx


@dataclass(frozen=True)
class ResearchSource:
    id: str
    title: str
    url: str
    domain: str
    snippet: str
    excerpt: str
    authority: str
    credibility_score: float


@dataclass(frozen=True)
class ResearchContext:
    query: str
    search_terms: tuple[str, ...]
    sources: tuple[ResearchSource, ...]
    generated_at: float


@dataclass(frozen=True)
class SearchHit:
    title: str
    url: str
    snippet: str


class _DuckDuckGoResultParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.results: list[SearchHit] = []
        self._current: dict[str, str] | None = None
        self._in_title = False
        self._in_snippet = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {key: value or "" for key, value in attrs}
        classes = attr_map.get("class", "")
        if tag == "a" and "result__a" in classes:
            self._current = {
                "title": "",
                "url": _canonicalize_url(attr_map.get("href", "")),
                "snippet": "",
            }
            self._in_title = True
            self._in_snippet = False
        elif tag == "a" and "result__snippet" in classes and self._current:
            self._in_snippet = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._in_title:
            self._in_title = False
            return

        if tag == "a" and self._in_snippet:
            self._in_snippet = False
            if self._current and self._current.get("title") and self._current.get("url"):
                self.results.append(
                    SearchHit(
                        title=_clean_text(self._current["title"]),
                        url=self._current["url"],
                        snippet=_clean_text(self._current.get("snippet", "")),
                    )
                )
            self._current = None

    def handle_data(self, data: str) -> None:
        if not self._current:
            return

        if self._in_title:
            self._current["title"] += data
        elif self._in_snippet:
            self._current["snippet"] += data


class _VisibleTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._chunks: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript", "svg", "iframe"}:
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript", "svg", "iframe"} and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        cleaned = _clean_text(data)
        if cleaned:
            self._chunks.append(cleaned)

    def text(self) -> str:
        return _clean_text(" ".join(self._chunks))


class InternetResearcher:
    def __init__(self, timeout_seconds: float = 12.0, max_sources: int = 8) -> None:
        self._timeout_seconds = timeout_seconds
        configured_max_sources = _env_int("HEXAMIND_RESEARCH_MAX_SOURCES", max_sources)
        self._max_sources = max(1, configured_max_sources)
        self._max_sources_per_domain = max(1, _env_int("HEXAMIND_MAX_SOURCES_PER_DOMAIN", 2))

    async def research(self, query: str) -> ResearchContext:
        search_terms = self._build_search_terms(query)
        hits = await self._search_hits(search_terms)

        sources: list[ResearchSource] = []
        seen_urls: set[str] = set()
        domain_counts: dict[str, int] = {}
        async with httpx.AsyncClient(
            timeout=self._timeout_seconds,
            follow_redirects=True,
            headers={"User-Agent": "HexamindResearch/1.0 (+https://example.com)"},
        ) as client:
            for index, hit in enumerate(hits, start=1):
                canonical_url = _canonicalize_url(hit.url)
                if canonical_url in seen_urls:
                    continue
                seen_urls.add(canonical_url)

                domain = urlparse(canonical_url).netloc or canonical_url
                if domain_counts.get(domain, 0) >= self._max_sources_per_domain:
                    continue

                page_text = await self._fetch_page_text(client, canonical_url)
                authority = _classify_authority(canonical_url)
                credibility_score = _credibility_score(canonical_url)
                excerpt = _trim_text(page_text or hit.snippet, 900)
                if not excerpt:
                    continue

                sources.append(
                    ResearchSource(
                        id=f"S{len(sources) + 1}",
                        title=_trim_text(hit.title, 140),
                        url=canonical_url,
                        domain=domain,
                        snippet=_trim_text(hit.snippet, 220),
                        excerpt=excerpt,
                        authority=authority,
                        credibility_score=credibility_score,
                    )
                )
                domain_counts[domain] = domain_counts.get(domain, 0) + 1

                if len(sources) >= self._max_sources:
                    break

        return ResearchContext(
            query=query,
            search_terms=tuple(search_terms),
            sources=tuple(sources),
            generated_at=time.time(),
        )

    async def _search_hits(self, search_terms: Iterable[str]) -> list[SearchHit]:
        results: list[SearchHit] = []
        async with httpx.AsyncClient(
            timeout=self._timeout_seconds,
            follow_redirects=True,
            headers={"User-Agent": "HexamindResearch/1.0 (+https://example.com)"},
        ) as client:
            for term in search_terms:
                try:
                    response = await client.get(
                        "https://html.duckduckgo.com/html/",
                        params={"q": term},
                    )
                    response.raise_for_status()
                except httpx.HTTPError:
                    continue

                parser = _DuckDuckGoResultParser()
                parser.feed(response.text)
                results.extend(parser.results)

                if len(results) >= self._max_sources * 3:
                    break

        unique: list[SearchHit] = []
        seen_urls: set[str] = set()
        for hit in results:
            canonical_url = _canonicalize_url(hit.url)
            if canonical_url in seen_urls:
                continue
            seen_urls.add(canonical_url)
            unique.append(SearchHit(title=hit.title, url=canonical_url, snippet=hit.snippet))

        return unique

    async def _fetch_page_text(self, client: httpx.AsyncClient, url: str) -> str:
        try:
            response = await client.get(url)
            response.raise_for_status()
        except httpx.HTTPError:
            return ""

        content_type = response.headers.get("content-type", "").lower()
        if "html" not in content_type and "text" not in content_type and "json" not in content_type:
            return ""

        parser = _VisibleTextExtractor()
        parser.feed(response.text)
        return parser.text()

    def _build_search_terms(self, query: str) -> list[str]:
        base = _clean_text(query)
        terms = [
            base,
            f"{base} latest evidence",
            f"{base} analysis research",
            f"{base} official documentation",
            f"{base} benchmark evaluation",
            f"{base} failure modes limitations",
            f"{base} implementation guide",
        ]
        seen: set[str] = set()
        deduped: list[str] = []
        for term in terms:
            key = term.lower().strip()
            if not key or key in seen:
                continue
            seen.add(key)
            deduped.append(term)
        return deduped


def format_research_context(context: ResearchContext | None) -> str:
    if not context or not context.sources:
        return "No live web sources were retrieved for this question."

    lines = [
        f"Query: {context.query}",
        f"Search terms: {', '.join(context.search_terms)}",
        "",
        "Source pack:",
    ]
    for source in context.sources:
        lines.extend(
            [
                f"[{source.id}] {source.title}",
                f"URL: {source.url}",
                f"Domain: {source.domain} | Authority: {source.authority} | Credibility: {source.credibility_score:.2f}",
                f"Snippet: {source.snippet or 'n/a'}",
                f"Excerpt: {source.excerpt}",
                "",
            ]
        )
    return "\n".join(lines).strip()


def source_inventory_markdown(context: ResearchContext | None) -> str:
    if not context or not context.sources:
        return "| ID | Title | Domain | Authority | Credibility | URL |\n| --- | --- | --- | --- | --- | --- |\n| - | No live sources retrieved | - | - | - | - |"

    rows = ["| ID | Title | Domain | Authority | Credibility | URL |", "| --- | --- | --- | --- | --- | --- |"]
    for source in context.sources:
        rows.append(
            f"| {source.id} | {source.title.replace('|', '/') } | {source.domain} | {source.authority} | {source.credibility_score:.2f} | {source.url} |"
        )
    return "\n".join(rows)


def _canonicalize_url(url: str) -> str:
    if not url:
        return url

    if url.startswith("//"):
        url = f"https:{url}"

    parsed = urlparse(url)
    if "duckduckgo.com" in parsed.netloc and parsed.path.startswith("/l/"):
        uddg = parse_qs(parsed.query).get("uddg", [""])[0]
        if uddg:
            return unquote(uddg)

    return url


def _classify_authority(url: str) -> str:
    domain = urlparse(url).netloc.lower()
    if domain.endswith(".gov") or domain.endswith(".edu"):
        return "primary"
    if any(token in domain for token in ("docs", "developer", "research", "acm", "ieee", "nature", "science")):
        return "high"
    return "secondary"


def _credibility_score(url: str) -> float:
    domain = urlparse(url).netloc.lower()
    score = 0.45
    if domain.endswith(".gov") or domain.endswith(".edu"):
        score += 0.45
    if any(token in domain for token in ("docs", "developer", "research", "acm", "ieee", "nature", "science")):
        score += 0.3
    if any(token in domain for token in ("wikipedia", "medium", "substack", "blog", "forum", "reddit")):
        score -= 0.15
    return max(0.05, min(1.0, score))


def _clean_text(text: str) -> str:
    return _trim_text(html_lib.unescape(re.sub(r"\s+", " ", text)).strip(), 10000)


def _trim_text(text: str, limit: int) -> str:
    collapsed = re.sub(r"\s+", " ", text).strip()
    if len(collapsed) <= limit:
        return collapsed
    return collapsed[: limit - 1].rstrip() + "…"


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default
