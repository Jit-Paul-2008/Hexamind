from __future__ import annotations

import asyncio
import html as html_lib
import os
import re
import time
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Iterable
from urllib.parse import parse_qs, quote, unquote, urljoin, urlparse

import httpx

from workflow import ResearchWorkflowProfile, build_workflow_profile


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
    recency_score: float = 0.0
    discovery_pass: str = ""


@dataclass(frozen=True)
class ResearchContext:
    query: str
    workflow_profile: ResearchWorkflowProfile
    search_terms: tuple[str, ...]
    search_passes: tuple[str, ...]
    sources: tuple[ResearchSource, ...]
    generated_at: float
    contradictions: tuple[tuple[str, str, str], ...] = ()


@dataclass(frozen=True)
class SearchHit:
    title: str
    url: str
    snippet: str
    relevance_score: float = 0.0
    discovery_pass: str = ""


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
        self._tavily_api_key = os.getenv("TAVILY_API_KEY", "").strip()
        self._search_provider = _research_provider(self._tavily_api_key)
        configured_max_sources = _env_int("HEXAMIND_RESEARCH_MAX_SOURCES", max_sources)
        self._max_sources = max(1, configured_max_sources)
        self._max_sources_per_domain = max(1, _env_int("HEXAMIND_MAX_SOURCES_PER_DOMAIN", 2))
        self._max_terms = max(3, _env_int("HEXAMIND_RESEARCH_MAX_TERMS", 10))
        self._max_hits_per_term = max(3, _env_int("HEXAMIND_RESEARCH_MAX_HITS_PER_TERM", 8))
        self._tavily_max_calls = max(1, _env_int("HEXAMIND_TAVILY_MAX_CALLS", 10))
        self._fetch_concurrency = max(1, _env_int("HEXAMIND_RESEARCH_FETCH_CONCURRENCY", 5))
        self._min_relevance_score = max(0.0, _env_float("HEXAMIND_RESEARCH_MIN_RELEVANCE", 0.24))
        self._cache_ttl_seconds = max(120.0, _env_float("HEXAMIND_RESEARCH_CACHE_TTL_SECONDS", 1800.0))
        self._research_cache: dict[str, tuple[float, ResearchContext]] = {}
        self._require_sources = _env_bool("HEXAMIND_REQUIRE_RESEARCH_SOURCES", False)
        if self._search_provider == "tavily" and not self._tavily_api_key:
            raise RuntimeError("Tavily provider is enabled but TAVILY_API_KEY is missing.")

    async def research(self, query: str) -> ResearchContext:
        cache_key = self._cache_key(query)
        cached = self._load_cached_research(cache_key)
        if cached is not None:
            return cached

        workflow_profile = build_workflow_profile(query)
        search_passes = self._build_search_passes(query, workflow_profile)
        search_terms = self._build_search_terms(query, workflow_profile, search_passes)
        hits = await self._search_hits(query, search_terms, workflow_profile, search_passes)
        candidates = await self._build_candidates(query, hits, workflow_profile)
        sources = _select_sources_with_diversity(
            candidates,
            max(self._max_sources, workflow_profile.max_sources),
            max(self._max_sources_per_domain, workflow_profile.required_source_mix),
            workflow_profile,
        )
        contradictions = tuple(_detect_source_contradictions(query, sources))

        if len(sources) < 2 and self._search_provider != "tavily":
            fallback = await self._wikipedia_fallback_sources(query, workflow_profile)
            merged = list(sources)
            seen_urls = {item.url for item in merged}
            for item in fallback:
                if item.url in seen_urls:
                    continue
                merged.append(item)
                seen_urls.add(item.url)
            sources = _assign_source_ids(merged[: max(self._max_sources, workflow_profile.max_sources)])

        result = ResearchContext(
            query=query,
            workflow_profile=workflow_profile,
            search_terms=tuple(search_terms),
            search_passes=tuple(search_passes),
            sources=tuple(sources),
            generated_at=time.time(),
            contradictions=contradictions,
        )
        if self._require_sources and not result.sources:
            raise RuntimeError("No research sources were retrieved.")
        self._store_cached_research(cache_key, result)
        return result

    def _build_search_passes(self, query: str, workflow_profile: ResearchWorkflowProfile) -> list[str]:
        passes = list(workflow_profile.search_passes)
        if not passes:
            passes = ["official", "recent", "evidence", "failure_modes"]
        # Beast workflow default: enforce 5-pass retrieval backbone.
        for required in ("official", "recent", "counter_evidence", "implementation", "disagreement"):
            if required not in passes:
                passes.append(required)
        if any(token in query.lower() for token in ("comparison", "vs", "versus", "tradeoff")) and "comparison" not in passes:
            passes.append("comparison")
        deduped: list[str] = []
        seen: set[str] = set()
        for item in passes:
            key = item.lower().strip()
            if not key or key in seen:
                continue
            seen.add(key)
            deduped.append(item)
        return deduped

    def _cache_key(self, query: str) -> str:
        return _clean_text(query).lower()

    def _load_cached_research(self, cache_key: str) -> ResearchContext | None:
        cached = self._research_cache.get(cache_key)
        if not cached:
            return None
        cached_at, context = cached
        if time.time() - cached_at > self._cache_ttl_seconds:
            self._research_cache.pop(cache_key, None)
            return None
        return context

    def _store_cached_research(self, cache_key: str, context: ResearchContext) -> None:
        self._research_cache[cache_key] = (time.time(), context)

    async def _search_hits(
        self,
        query: str,
        search_terms: Iterable[str],
        workflow_profile: ResearchWorkflowProfile,
        search_passes: Iterable[str],
    ) -> list[SearchHit]:
        if self._search_provider == "tavily":
            return await self._search_hits_tavily(query, search_terms, workflow_profile, search_passes)
        return await self._search_hits_duckduckgo(query, search_terms, workflow_profile, search_passes)

    async def _search_hits_duckduckgo(
        self,
        query: str,
        search_terms: Iterable[str],
        workflow_profile: ResearchWorkflowProfile,
        search_passes: Iterable[str],
    ) -> list[SearchHit]:
        results: list[SearchHit] = []
        max_terms = max(self._max_terms, workflow_profile.max_terms)
        min_relevance_score = min(self._min_relevance_score, workflow_profile.min_relevance)
        async with httpx.AsyncClient(
            timeout=self._timeout_seconds,
            follow_redirects=True,
            headers={"User-Agent": "HexamindResearch/1.0 (+https://example.com)"},
        ) as client:
            ordered_terms = list(search_terms)[: max_terms]
            passes = list(search_passes) or ["evidence"]
            for pass_name in passes:
                for term in ordered_terms:
                    if not _term_matches_pass(term, pass_name):
                        continue
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
                    for hit in parser.results[: max(self._max_hits_per_term, workflow_profile.max_hits_per_term)]:
                        score = _hit_relevance(query, term, hit.title, hit.snippet, hit.url)
                        score *= _pass_weight(pass_name)
                        if score < min_relevance_score:
                            continue
                        results.append(
                            SearchHit(
                                title=hit.title,
                                url=hit.url,
                                snippet=hit.snippet,
                                relevance_score=score,
                                discovery_pass=pass_name,
                            )
                        )

                    if len(results) >= max(self._max_sources, workflow_profile.max_sources) * 12:
                        break

        return _dedupe_hits(results)

    async def _search_hits_tavily(
        self,
        query: str,
        search_terms: Iterable[str],
        workflow_profile: ResearchWorkflowProfile,
        search_passes: Iterable[str],
    ) -> list[SearchHit]:
        if not self._tavily_api_key:
            return []

        results: list[SearchHit] = []
        max_terms = max(self._max_terms, workflow_profile.max_terms)
        max_hits = max(self._max_hits_per_term, workflow_profile.max_hits_per_term)
        min_relevance_score = min(self._min_relevance_score, workflow_profile.min_relevance)
        ordered_terms = list(search_terms)[:max_terms]
        passes = list(search_passes) or ["evidence"]
        max_calls = max(1, min(self._tavily_max_calls, len(ordered_terms) * max(1, len(passes))))
        calls_made = 0

        async with httpx.AsyncClient(timeout=self._timeout_seconds, follow_redirects=True) as client:
            for pass_name in passes:
                for term in ordered_terms:
                    if calls_made >= max_calls:
                        break
                    if not _term_matches_pass(term, pass_name):
                        continue

                    payload = {
                        "api_key": self._tavily_api_key,
                        "query": f"{term} ({pass_name} evidence)",
                        "search_depth": "advanced",
                        "max_results": max_hits,
                        "include_raw_content": True,
                        "include_images": False,
                        "include_answer": False,
                    }

                    try:
                        response = await client.post("https://api.tavily.com/search", json=payload)
                        response.raise_for_status()
                        body = response.json()
                    except Exception:
                        calls_made += 1
                        continue

                    for item in body.get("results", []):
                        if not isinstance(item, dict):
                            continue
                        title = _clean_text(str(item.get("title", "")))
                        url = _canonicalize_url(str(item.get("url", "")))
                        raw_content = _clean_text(str(item.get("raw_content", "")))
                        content = _clean_text(str(item.get("content", "")))
                        snippet = _trim_text(content or raw_content, 220)
                        if not title or not url:
                            continue
                        score = float(item.get("score") or 0.0)
                        if score <= 0.0:
                            score = _hit_relevance(query, term, title, snippet, url)
                        score *= _pass_weight(pass_name)
                        if score < min_relevance_score:
                            continue
                        results.append(
                            SearchHit(
                                title=title,
                                url=url,
                                snippet=snippet,
                                relevance_score=score,
                                discovery_pass=pass_name,
                            )
                        )

                    calls_made += 1

                if calls_made >= max_calls:
                    break

        return _dedupe_hits(results)

    async def _build_candidates(
        self,
        query: str,
        hits: list[SearchHit],
        workflow_profile: ResearchWorkflowProfile,
    ) -> list[tuple[float, ResearchSource]]:
        if not hits:
            return []

        semaphore = asyncio.Semaphore(max(self._fetch_concurrency, workflow_profile.fetch_concurrency))

        async with httpx.AsyncClient(
            timeout=self._timeout_seconds,
            follow_redirects=True,
            headers={"User-Agent": "HexamindResearch/1.0 (+https://example.com)"},
        ) as client:
            tasks = [
                self._hydrate_candidate(semaphore, client, query, hit, workflow_profile)
                for hit in hits[: max(self._max_sources, workflow_profile.max_sources) * 16]
            ]
            hydrated = await asyncio.gather(*tasks, return_exceptions=True)

        candidates: list[tuple[float, ResearchSource]] = []
        for item in hydrated:
            if isinstance(item, tuple):
                candidates.append(item)
        candidates.sort(key=lambda row: row[0], reverse=True)
        return _rank_and_dedupe_candidates(candidates, workflow_profile)

    async def _hydrate_candidate(
        self,
        semaphore: asyncio.Semaphore,
        client: httpx.AsyncClient,
        query: str,
        hit: SearchHit,
        workflow_profile: ResearchWorkflowProfile,
    ) -> tuple[float, ResearchSource] | None:
        canonical_url = _canonicalize_url(hit.url)
        domain = urlparse(canonical_url).netloc or canonical_url
        if _is_filtered_domain(domain):
            return None

        async with semaphore:
            page_text = await self._fetch_page_text(client, canonical_url)

        authority = _classify_authority(canonical_url)
        credibility_score = _credibility_score(canonical_url)
        excerpt = _extract_evidence_excerpt(
            page_text or hit.snippet,
            query,
            workflow_profile.evidence_excerpt_limit,
        )
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
            recency_score=_recency_score(canonical_url, hit.title, hit.snippet, page_text),
            discovery_pass=hit.discovery_pass,
        )
        if _is_boilerplate_source(source.title, source.snippet, source.excerpt):
            return None

        retrieval_score = _retrieval_score(hit.relevance_score, credibility_score, source.recency_score, excerpt)
        retrieval_score += _authority_bonus(authority, workflow_profile.requires_primary_sources, workflow_profile.audience)
        retrieval_score += _domain_trust_bonus(domain)
        retrieval_score += _recency_bonus(source.recency_score)
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

    def _build_search_terms(
        self,
        query: str,
        workflow_profile: ResearchWorkflowProfile,
        search_passes: Iterable[str],
    ) -> list[str]:
        base = _clean_text(query)
        core_terms = _top_query_terms(base, max(5, workflow_profile.max_terms // 2))
        core_joined = " ".join(core_terms)
        terms = list(workflow_profile.search_intents) + list(workflow_profile.adversarial_queries) + [
            f"{core_joined} systematic review",
            f"{core_joined} case study",
        ]
        pass_set = set(search_passes)
        if pass_set.intersection({"official", "primary_sources"}):
            terms.extend([f"{base} official", f"{base} site:.gov", f"{base} site:.edu"])
        if pass_set.intersection({"recent", "benchmark"}):
            terms.extend([f"{base} latest", f"{base} recent review", f"{base} current evidence"])
        if pass_set.intersection({"failure_modes", "comparison"}):
            terms.extend([f"{base} limitations", f"{base} failures", f"{base} tradeoff analysis"])
        if "counter_evidence" in pass_set:
            terms.extend(
                [
                    f"{base} counter evidence",
                    f"{base} criticism limitations",
                    f"{base} failure analysis",
                ]
            )
        if "implementation" in pass_set:
            terms.extend(
                [
                    f"{base} implementation guide",
                    f"{base} practical case study",
                    f"{base} benchmark results",
                ]
            )
        if "disagreement" in pass_set:
            terms.extend(
                [
                    f"{base} conflicting evidence",
                    f"{base} expert debate",
                    f"{base} disputed findings",
                ]
            )
        seen: set[str] = set()
        deduped: list[str] = []
        for term in terms:
            key = term.lower().strip()
            if not key or key in seen:
                continue
            seen.add(key)
            deduped.append(term)
        return deduped

    async def _wikipedia_fallback_sources(
        self,
        query: str,
        workflow_profile: ResearchWorkflowProfile,
    ) -> list[ResearchSource]:
        params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "format": "json",
            "utf8": "1",
            "srlimit": str(max(3, min(6, workflow_profile.max_sources))),
        }
        async with httpx.AsyncClient(
            timeout=self._timeout_seconds,
            follow_redirects=True,
            headers={"User-Agent": "HexamindResearch/1.0 (+https://example.com)"},
        ) as client:
            try:
                response = await client.get("https://en.wikipedia.org/w/api.php", params=params)
                response.raise_for_status()
                payload = response.json()
            except Exception:
                return []

            entries = payload.get("query", {}).get("search", [])
            if not isinstance(entries, list):
                return []

            sources: list[ResearchSource] = []
            for entry in entries:
                title = str(entry.get("title", "")).strip()
                snippet = _clean_text(str(entry.get("snippet", "")))
                if not title:
                    continue
                page_url = f"https://en.wikipedia.org/wiki/{quote(title.replace(' ', '_'))}"
                summary_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{quote(title)}"
                try:
                    summary_response = await client.get(summary_url)
                    summary_response.raise_for_status()
                    summary_payload = summary_response.json()
                    extract = _clean_text(str(summary_payload.get("extract", "")))
                except Exception:
                    extract = snippet

                excerpt = _extract_evidence_excerpt(extract or snippet, query, workflow_profile.evidence_excerpt_limit)
                if not excerpt:
                    continue

                sources.append(
                    ResearchSource(
                        id="",
                        title=_trim_text(title, 140),
                        url=page_url,
                        domain="en.wikipedia.org",
                        snippet=_trim_text(snippet, 220),
                        excerpt=excerpt,
                        authority="high",
                        credibility_score=0.66,
                        recency_score=_recency_score(page_url, title, snippet, extract),
                        discovery_pass="fallback",
                    )
                )

            return sources


def format_research_context(context: ResearchContext | None) -> str:
    if not context or not context.sources:
        return "No live web sources were retrieved for this question."

    lines = [
        f"Query: {context.query}",
        f"Audience profile: {context.workflow_profile.audience}",
        f"Depth profile: {context.workflow_profile.depth_label}",
        f"Topic complexity: {context.workflow_profile.complexity_score:.2f}",
        f"Token mode: {context.workflow_profile.token_mode}",
        f"Search terms: {', '.join(context.search_terms)}",
        f"Subquestions: {' | '.join(context.workflow_profile.subquestions)}",
        "",
        "Source pack:",
    ]
    for source in context.sources[: context.workflow_profile.context_source_cap]:
        lines.extend(
            [
                f"[{source.id}] {source.title}",
                f"URL: {source.url}",
                f"Domain: {source.domain} | Authority: {source.authority} | Credibility: {source.credibility_score:.2f}",
                f"Pass: {source.discovery_pass or 'n/a'} | Recency: {source.recency_score:.2f}",
                f"Snippet: {source.snippet or 'n/a'}",
                f"Excerpt: {_trim_text(source.excerpt, context.workflow_profile.evidence_excerpt_limit)}",
                "",
            ]
        )
    if context.contradictions:
        lines.extend(["", "Contradictions:"])
        for source_a, source_b, reason in context.contradictions[:5]:
            lines.append(f"- {source_a} vs {source_b}: {reason}")
    return "\n".join(lines).strip()


def source_inventory_markdown(context: ResearchContext | None) -> str:
    if not context or not context.sources:
        return "| ID | Title | Domain | Authority | Credibility | URL |\n| --- | --- | --- | --- | --- | --- |\n| - | No live sources retrieved | - | - | - | - |"

    rows = [
        "| ID | Title | Domain | Authority | Credibility | URL |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
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


def _retrieval_score(relevance_score: float, credibility_score: float, recency_score: float, excerpt: str) -> float:
    richness = min(1.0, len(excerpt) / 700.0)
    return (relevance_score * 0.48) + (credibility_score * 0.28) + (recency_score * 0.14) + (richness * 0.10)


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
    workflow_profile: ResearchWorkflowProfile,
) -> list[ResearchSource]:
    if not candidates:
        return []

    selected: list[ResearchSource] = []
    domain_counts: dict[str, int] = {}
    covered_domains: set[str] = set()

    required_unique_domains = max(1, workflow_profile.required_source_mix)

    def can_take(source: ResearchSource) -> bool:
        return domain_counts.get(source.domain, 0) < max_sources_per_domain

    for _, source in candidates:
        if source.domain in covered_domains:
            continue
        if not can_take(source):
            continue
        selected.append(source)
        domain_counts[source.domain] = domain_counts.get(source.domain, 0) + 1
        covered_domains.add(source.domain)
        if len(covered_domains) >= required_unique_domains or len(selected) >= max_sources:
            break

    for _, source in candidates:
        if len(selected) >= max_sources:
            break
        if source in selected:
            continue
        if not can_take(source):
            continue
        selected.append(source)
        domain_counts[source.domain] = domain_counts.get(source.domain, 0) + 1

    return _assign_source_ids(selected)


def _assign_source_ids(sources: list[ResearchSource]) -> list[ResearchSource]:
    result: list[ResearchSource] = []
    for idx, source in enumerate(sources, start=1):
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
                recency_score=source.recency_score,
                discovery_pass=source.discovery_pass,
            )
        )
    return result


def _rank_and_dedupe_candidates(
    candidates: list[tuple[float, ResearchSource]],
    workflow_profile: ResearchWorkflowProfile,
) -> list[tuple[float, ResearchSource]]:
    selected: list[tuple[float, ResearchSource]] = []
    seen_urls: set[str] = set()
    signatures: list[set[str]] = []

    for score, source in sorted(candidates, key=lambda row: row[0], reverse=True):
        canonical_url = _canonicalize_url(source.url)
        if canonical_url in seen_urls:
            continue
        if _is_boilerplate_source(source.title, source.snippet, source.excerpt):
            continue

        signature = _text_signature(source.title, source.excerpt)
        if any(_signature_overlap(signature, existing) >= 0.72 for existing in signatures):
            continue

        selected.append((score + _source_quality_bonus(source, workflow_profile), source))
        seen_urls.add(canonical_url)
        signatures.append(signature)

    selected.sort(key=lambda row: row[0], reverse=True)
    return selected


def _authority_bonus(authority: str, requires_primary_sources: bool, audience: str) -> float:
    if authority == "primary":
        return 0.18 if requires_primary_sources else 0.12
    if authority == "high":
        return 0.08 if audience in {"phd", "professor"} else 0.05
    return 0.0


def _domain_trust_bonus(domain: str) -> float:
    lowered = domain.lower()
    if lowered.endswith((".gov", ".edu")):
        return 0.08
    if any(token in lowered for token in ("docs", "developer", "research", "acm", "ieee", "nature", "science")):
        return 0.05
    if any(token in lowered for token in ("blog", "medium", "substack", "reddit", "forum")):
        return -0.04
    return 0.0


def _recency_score(url: str, title: str, snippet: str, body: str) -> float:
    current_year = time.gmtime().tm_year
    haystack = f"{url} {title} {snippet} {body}"
    years = [int(year) for year in re.findall(r"(?<!\d)(20\d{2})(?!\d)", haystack)]
    if not years:
        if any(token in haystack.lower() for token in ("latest", "recent", "current", "updated")):
            return 0.4
        return 0.15

    delta = min(abs(current_year - year) for year in years)
    if delta == 0:
        return 1.0
    if delta == 1:
        return 0.75
    if delta == 2:
        return 0.5
    return 0.2


def _recency_bonus(recency_score: float) -> float:
    return min(0.12, recency_score * 0.12)


def _is_boilerplate_source(title: str, snippet: str, excerpt: str) -> bool:
    text = f"{title} {snippet} {excerpt}".lower()
    boilerplate_tokens = (
        "cookie",
        "privacy policy",
        "terms of service",
        "subscribe",
        "javascript",
        "all rights reserved",
        "sign up",
        "log in",
        "newsletter",
        "advertising",
        "enable cookies",
    )
    if any(token in text for token in boilerplate_tokens):
        return True
    words = re.findall(r"[a-zA-Z0-9]{3,}", text)
    if len(words) < 35:
        return False
    unique_ratio = len(set(words)) / max(1, len(words))
    return unique_ratio < 0.38


def _text_signature(title: str, excerpt: str) -> set[str]:
    words = re.findall(r"[a-zA-Z0-9]{4,}", f"{title} {excerpt}".lower())
    stop = {
        "that",
        "this",
        "with",
        "from",
        "into",
        "about",
        "their",
        "there",
        "which",
        "when",
        "where",
        "what",
        "will",
        "should",
        "could",
        "would",
    }
    return {word for word in words if word not in stop}


def _signature_overlap(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    union = left | right
    if not union:
        return 0.0
    return len(left & right) / len(union)


def _source_quality_bonus(source: ResearchSource, workflow_profile: ResearchWorkflowProfile) -> float:
    bonus = source.credibility_score * 0.08
    bonus += source.recency_score * 0.06
    if source.authority == "primary" and workflow_profile.requires_primary_sources:
        bonus += 0.05
    if source.discovery_pass in {"official", "primary_sources"}:
        bonus += 0.03
    return bonus


def _detect_source_contradictions(query: str, sources: tuple[ResearchSource, ...]) -> list[tuple[str, str, str]]:
    if len(sources) < 2:
        return []

    findings: list[tuple[str, str, str]] = []
    for index, source_a in enumerate(sources):
        for source_b in sources[index + 1 :]:
            score_a = _stance_score(source_a.excerpt)
            score_b = _stance_score(source_b.excerpt)
            if score_a == 0 and score_b == 0:
                continue
            if score_a * score_b < 0 and abs(score_a - score_b) >= 2:
                findings.append(
                    (
                        source_a.id,
                        source_b.id,
                        f"Evidence polarity differs for query '{query}' across {source_a.domain} and {source_b.domain}.",
                    )
                )
    return findings[:5]


def _stance_score(text: str) -> int:
    normalized = text.lower()
    positive_cues = [
        "improve",
        "improved",
        "effective",
        "success",
        "increase",
        "benefit",
        "outperform",
        "recommended",
        "strong evidence",
    ]
    negative_cues = [
        "fail",
        "failed",
        "risk",
        "limitation",
        "uncertain",
        "not effective",
        "decline",
        "worse",
        "harm",
        "weak evidence",
    ]
    positive = sum(1 for cue in positive_cues if cue in normalized)
    negative = sum(1 for cue in negative_cues if cue in normalized)
    return positive - negative


def _term_matches_pass(term: str, pass_name: str) -> bool:
    lowered = term.lower()
    if pass_name == "official":
        return any(token in lowered for token in ("official", "documentation", "docs", "site:.gov", "site:.edu"))
    if pass_name == "recent":
        return any(token in lowered for token in ("latest", "recent", "current", "2025", "2026", "updated"))
    if pass_name == "evidence":
        return any(token in lowered for token in ("evidence", "review", "study", "benchmark", "evaluation", "method"))
    if pass_name == "failure_modes":
        return any(token in lowered for token in ("failure", "fail", "limitations", "risk", "tradeoff", "limitations failures"))
    if pass_name == "comparison":
        return any(token in lowered for token in ("compare", "comparison", "versus", "vs", "tradeoff", "between"))
    if pass_name == "methodology":
        return any(token in lowered for token in ("method", "methodology", "protocol", "experiment", "evaluation", "benchmark", "dataset"))
    if pass_name == "benchmark":
        return any(token in lowered for token in ("benchmark", "evaluation", "dataset", "metric", "measure", "test"))
    if pass_name == "primary_sources":
        return any(token in lowered for token in ("official", "primary", "docs", "site:.gov", "site:.edu", "specification"))
    if pass_name == "counter_evidence":
        return any(token in lowered for token in ("counter", "criticism", "limitations", "fail", "risk", "disputed"))
    if pass_name == "implementation":
        return any(token in lowered for token in ("implementation", "guide", "case study", "benchmark", "practical", "how to"))
    if pass_name == "disagreement":
        return any(token in lowered for token in ("conflicting", "debate", "disagreement", "disputed", "versus", "tradeoff"))
    return True


def _pass_weight(pass_name: str) -> float:
    weights = {
        "official": 1.06,
        "recent": 1.04,
        "evidence": 1.0,
        "failure_modes": 1.02,
        "comparison": 1.01,
        "methodology": 1.03,
        "benchmark": 1.05,
        "primary_sources": 1.07,
        "counter_evidence": 1.03,
        "implementation": 1.02,
        "disagreement": 1.02,
    }
    return weights.get(pass_name, 1.0)


def _dedupe_hits(results: list[SearchHit]) -> list[SearchHit]:
    seen_urls: dict[str, SearchHit] = {}

    for hit in sorted(results, key=lambda item: item.relevance_score, reverse=True):
        canonical_url = _canonicalize_url(hit.url)
        existing = seen_urls.get(canonical_url)
        if existing is None or hit.relevance_score > existing.relevance_score:
            seen_urls[canonical_url] = SearchHit(
                title=hit.title,
                url=canonical_url,
                snippet=hit.snippet,
                relevance_score=hit.relevance_score,
                discovery_pass=hit.discovery_pass,
            )

    unique = list(seen_urls.values())
    unique.sort(key=lambda item: item.relevance_score, reverse=True)
    return unique


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


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _research_provider(tavily_api_key: str) -> str:
    configured = os.getenv("HEXAMIND_RESEARCH_PROVIDER", "auto").strip().lower()
    if configured in {"tavily", "duckduckgo"}:
        return configured
    return "tavily" if tavily_api_key else "duckduckgo"
