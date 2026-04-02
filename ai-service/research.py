from __future__ import annotations

import asyncio
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
    relevance_score: float = 0.0


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
        self._max_terms = max(3, _env_int("HEXAMIND_RESEARCH_MAX_TERMS", 10))
        self._max_hits_per_term = max(3, _env_int("HEXAMIND_RESEARCH_MAX_HITS_PER_TERM", 8))
        self._fetch_concurrency = max(1, _env_int("HEXAMIND_RESEARCH_FETCH_CONCURRENCY", 5))
        self._min_relevance_score = max(0.0, _env_float("HEXAMIND_RESEARCH_MIN_RELEVANCE", 0.24))

    async def research(self, query: str) -> ResearchContext:
        search_terms = self._build_search_terms(query)
        hits = await self._search_hits(query, search_terms)
        candidates = await self._build_candidates(query, hits)
        sources = _select_sources_with_diversity(candidates, self._max_sources, self._max_sources_per_domain)

        return ResearchContext(
            query=query,
            search_terms=tuple(search_terms),
            sources=tuple(sources),
            generated_at=time.time(),
        )

    async def _search_hits(self, query: str, search_terms: Iterable[str]) -> list[SearchHit]:
        results: list[SearchHit] = []
        async with httpx.AsyncClient(
            timeout=self._timeout_seconds,
            follow_redirects=True,
            headers={"User-Agent": "HexamindResearch/1.0 (+https://example.com)"},
        ) as client:
            for term in list(search_terms)[: self._max_terms]:
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
                for hit in parser.results[: self._max_hits_per_term]:
                    score = _hit_relevance(query, term, hit.title, hit.snippet, hit.url)
                    if score < self._min_relevance_score:
                        continue
                    results.append(
                        SearchHit(
                            title=hit.title,
                            url=hit.url,
                            snippet=hit.snippet,
                            relevance_score=score,
                        )
                    )

                if len(results) >= self._max_sources * 12:
                    break

        unique: list[SearchHit] = []
        seen_urls: set[str] = set()
        for hit in sorted(results, key=lambda item: item.relevance_score, reverse=True):
            canonical_url = _canonicalize_url(hit.url)
            if canonical_url in seen_urls:
                continue
            seen_urls.add(canonical_url)
            unique.append(
                SearchHit(
                    title=hit.title,
                    url=canonical_url,
                    snippet=hit.snippet,
                    relevance_score=hit.relevance_score,
                )
            )

        return unique

    async def _build_candidates(self, query: str, hits: list[SearchHit]) -> list[tuple[float, ResearchSource]]:
        if not hits:
            return []

        semaphore = asyncio.Semaphore(self._fetch_concurrency)

        async with httpx.AsyncClient(
            timeout=self._timeout_seconds,
            follow_redirects=True,
            headers={"User-Agent": "HexamindResearch/1.0 (+https://example.com)"},
        ) as client:
            tasks = [
                self._hydrate_candidate(semaphore, client, query, hit)
                for hit in hits[: self._max_sources * 16]
            ]
            hydrated = await asyncio.gather(*tasks, return_exceptions=True)

        candidates: list[tuple[float, ResearchSource]] = []
        for item in hydrated:
            if isinstance(item, tuple):
                candidates.append(item)
        candidates.sort(key=lambda row: row[0], reverse=True)
        return candidates

    async def _hydrate_candidate(
        self,
        semaphore: asyncio.Semaphore,
        client: httpx.AsyncClient,
        query: str,
        hit: SearchHit,
    ) -> tuple[float, ResearchSource] | None:
        canonical_url = _canonicalize_url(hit.url)
        domain = urlparse(canonical_url).netloc or canonical_url
        if _is_filtered_domain(domain):
            return None

        async with semaphore:
            page_text = await self._fetch_page_text(client, canonical_url)

        authority = _classify_authority(canonical_url)
        credibility_score = _credibility_score(canonical_url)
        excerpt = _extract_evidence_excerpt(page_text or hit.snippet, query, 900)
        if not excerpt:
            return None

        source = ResearchSource(
            id="",
            title=_trim_text(hit.title, 140),
            url=canonical_url,
            domain=domain,
            snippet=_trim_text(hit.snippet, 220),
            excerpt=excerpt,
            authority=authority,
            credibility_score=credibility_score,
        )
        retrieval_score = _retrieval_score(hit.relevance_score, credibility_score, excerpt)
        return retrieval_score, source

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
        core_terms = _top_query_terms(base, 5)
        core_joined = " ".join(core_terms)
        terms = [
            base,
            f"{base} latest evidence",
            f"{base} analysis research",
            f"{base} official documentation",
            f"{base} benchmark evaluation",
            f"{base} failure modes limitations",
            f"{base} implementation guide",
            f"{base} peer reviewed evidence",
            f"{base} methodology",
            f"{base} empirical results",
            f"{base} official policy",
            f"{core_joined} systematic review",
            f"{core_joined} case study",
            f"{base} site:.gov",
            f"{base} site:.edu",
            f"{base} site:arxiv.org",
            f"{base} site:nature.com",
            f"{base} site:ieee.org",
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


def _retrieval_score(relevance_score: float, credibility_score: float, excerpt: str) -> float:
    richness = min(1.0, len(excerpt) / 700.0)
    return (relevance_score * 0.55) + (credibility_score * 0.35) + (richness * 0.10)


def _top_query_terms(query: str, max_terms: int) -> list[str]:
    stop = {
        "the",
        "and",
        "for",
        "with",
        "from",
        "that",
        "this",
        "into",
        "about",
        "how",
        "what",
        "when",
        "where",
        "which",
        "are",
        "was",
        "were",
        "will",
        "would",
        "could",
        "should",
        "can",
        "your",
        "their",
        "our",
    }
    words = re.findall(r"[a-zA-Z0-9]{3,}", query.lower())
    filtered = [word for word in words if word not in stop]
    seen: set[str] = set()
    unique: list[str] = []
    for word in filtered:
        if word in seen:
            continue
        seen.add(word)
        unique.append(word)
        if len(unique) >= max_terms:
            break
    return unique


def _hit_relevance(query: str, term: str, title: str, snippet: str, url: str) -> float:
    q_terms = set(_top_query_terms(query, 12))
    t_terms = set(_top_query_terms(term, 8))
    combined_terms = q_terms.union(t_terms)
    haystack = f"{title} {snippet} {url}".lower()
    if not combined_terms:
        return 0.0

    overlap = sum(1 for token in combined_terms if token in haystack)
    overlap_score = overlap / max(1, len(combined_terms))
    exact_phrase_bonus = 0.18 if query.lower() in haystack else 0.0
    authority_bonus = 0.10 if _classify_authority(url) in {"primary", "high"} else 0.0
    return min(1.0, overlap_score + exact_phrase_bonus + authority_bonus)


def _extract_evidence_excerpt(text: str, query: str, limit: int) -> str:
    cleaned = _clean_text(text)
    if not cleaned:
        return ""

    terms = _top_query_terms(query, 8)
    if not terms:
        return _trim_text(cleaned, limit)

    sentences = re.split(r"(?<=[.!?])\s+", cleaned)
    scored: list[tuple[int, str]] = []
    for sentence in sentences:
        lower = sentence.lower()
        score = sum(1 for term in terms if term in lower)
        if score > 0:
            scored.append((score, sentence.strip()))

    if not scored:
        return _trim_text(cleaned, limit)

    scored.sort(key=lambda item: item[0], reverse=True)
    picked: list[str] = []
    total = 0
    for _, sentence in scored:
        if not sentence:
            continue
        addition = len(sentence) + (1 if picked else 0)
        if total + addition > limit:
            continue
        picked.append(sentence)
        total += addition
        if total >= limit * 0.8:
            break

    joined = " ".join(picked).strip()
    return _trim_text(joined or cleaned, limit)


def _is_filtered_domain(domain: str) -> bool:
    lowered = domain.lower()
    blocked = (
        "pinterest.",
        "instagram.",
        "facebook.",
        "tiktok.",
        "x.com",
    )
    return any(token in lowered for token in blocked)


def _select_sources_with_diversity(
    candidates: list[tuple[float, ResearchSource]],
    max_sources: int,
    max_sources_per_domain: int,
) -> list[ResearchSource]:
    if not candidates:
        return []

    selected: list[ResearchSource] = []
    domain_counts: dict[str, int] = {}

    for _, source in candidates:
        if domain_counts.get(source.domain, 0) >= max_sources_per_domain:
            continue
        selected.append(source)
        domain_counts[source.domain] = domain_counts.get(source.domain, 0) + 1
        if len(selected) >= max_sources:
            break

    result: list[ResearchSource] = []
    for idx, source in enumerate(selected, start=1):
        result.append(
            ResearchSource(
                id=f"S{idx}",
                title=source.title,
                url=source.url,
                domain=source.domain,
                snippet=source.snippet,
                excerpt=source.excerpt,
                authority=source.authority,
                credibility_score=source.credibility_score,
            )
        )

    return result


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


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default
