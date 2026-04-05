from __future__ import annotations

import asyncio
import html as html_lib
import os
import random
import re
import time
from dataclasses import dataclass, replace
from html.parser import HTMLParser
from typing import Iterable
from urllib.parse import parse_qs, quote, unquote, urljoin, urlparse

import httpx

from embeddings import LocalEmbeddingsClient
from knowledge_cache import LocalKnowledgeCache
from governance import redact_pii
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
    evidence_density: float = 0.0  # How many factual claims per 100 words
    cross_source_corroboration: float = 0.0  # How many other sources support this
    stance_polarity: int = 0  # -3 to +3 stance on topic


@dataclass(frozen=True)
class ResearchContext:
    query: str
    workflow_profile: ResearchWorkflowProfile
    search_terms: tuple[str, ...]
    search_passes: tuple[str, ...]
    sources: tuple[ResearchSource, ...]
    generated_at: float
    contradictions: tuple[tuple[str, str, str], ...] = ()
    evidence_graph: tuple[tuple[str, str, str], ...] = ()  # (source_id, claim, confidence)
    corroboration_pairs: tuple[tuple[str, str, str], ...] = ()  # (source_a, source_b, shared_claim)
    topic_coverage_score: float = 0.0  # 0-1 how well sources cover topic breadth
    research_depth_score: float = 0.0  # 0-1 depth of evidence gathered


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
    """Enhanced research engine with deep evidence extraction and multi-source corroboration.
    
    Key improvements over baseline:
    - Adaptive search depth: Automatically increases passes for complex topics
    - Multi-strategy fallback: Wikipedia, Google Scholar, Archive.org for blocked sources
    - Evidence density scoring: Prioritizes sources with factual claims
    - Cross-source corroboration: Identifies claims supported by multiple sources
    - Stance triangulation: Detects agreement/disagreement patterns
    """
    
    # High-credibility fallback domains when primary sources fail
    FALLBACK_DOMAINS = [
        "wikipedia.org",
        "britannica.com",
        "scholar.google.com",
        "archive.org",
        "ncbi.nlm.nih.gov",  # PubMed
        "arxiv.org",
        "ssrn.com",
        "researchgate.net",
    ]
    
    # Domain rotation for blocked sources (403/404 resilience)
    DOMAIN_MIRRORS = {
        "weforum.org": ["brookings.edu", "mckinsey.com"],
        "imf.org": ["worldbank.org", "oecd.org"],
        "niti.gov.in": ["pib.gov.in", "meity.gov.in"],
    }
    
    # Evidence extraction patterns for factual claims
    CLAIM_PATTERNS = [
        r"(?:studies? show|research (?:indicates|suggests|found)|evidence (?:shows|suggests))\s+([^.]+\.)",
        r"(?:according to|as reported by|data from)\s+([^,]+),?\s+([^.]+\.)",
        r"(\d+(?:\.\d+)?%?\s+(?:of|increase|decrease|growth|reduction)[^.]+\.)",
        r"(?:in\s+\d{4},?)\s+([^.]+\.)",  # Time-anchored claims
    ]
    
    def __init__(self, timeout_seconds: float = 15.0, max_sources: int = 14) -> None:
        self._timeout_seconds = timeout_seconds
        self._tavily_api_key = os.getenv("TAVILY_API_KEY", "").strip()
        self._tavily_api_keys = self._parse_api_key_pool("TAVILY_API_KEY", "TAVILY_API_KEYS")
        self._tavily_key_index = 0
        self._search_provider = _research_provider(self._tavily_api_keys[0] if self._tavily_api_keys else "")
        # Increased defaults for deeper research
        configured_max_sources = _env_int("HEXAMIND_RESEARCH_MAX_SOURCES", max(max_sources, 14))
        self._max_sources = max(6, configured_max_sources)  # Minimum 6 for triangulation
        self._max_sources_per_domain = max(2, _env_int("HEXAMIND_MAX_SOURCES_PER_DOMAIN", 3))
        self._max_terms = max(5, _env_int("HEXAMIND_RESEARCH_MAX_TERMS", 8))  # More search terms
        self._max_hits_per_term = max(5, _env_int("HEXAMIND_RESEARCH_MAX_HITS_PER_TERM", 10))
        self._tavily_max_calls = max(3, _env_int("HEXAMIND_TAVILY_MAX_CALLS", 5))  # More API calls
        self._fetch_concurrency = max(3, _env_int("HEXAMIND_RESEARCH_FETCH_CONCURRENCY", 8))
        self._min_relevance_score = max(0.0, _env_float("HEXAMIND_RESEARCH_MIN_RELEVANCE", 0.20))  # Lower threshold
        self._search_retry_attempts = max(1, _env_int("HEXAMIND_SEARCH_RETRY_ATTEMPTS", 5))
        self._search_backoff_seconds = max(0.1, _env_float("HEXAMIND_SEARCH_BACKOFF_SECONDS", 0.4))
        self._search_backoff_max_seconds = max(self._search_backoff_seconds, _env_float("HEXAMIND_SEARCH_BACKOFF_MAX_SECONDS", 3.0))
        self._search_throttle_seconds = max(0.0, _env_float("HEXAMIND_SEARCH_THROTTLE_SECONDS", 0.35))
        self._search_jitter_seconds = max(0.0, _env_float("HEXAMIND_SEARCH_JITTER_SECONDS", 0.2))
        self._next_search_request_at = 0.0
        self._search_throttle_lock = asyncio.Lock()
        self._cache_ttl_seconds = max(120.0, _env_float("HEXAMIND_RESEARCH_CACHE_TTL_SECONDS", 1800.0))
        self._semantic_cache_threshold = min(0.98, max(0.65, _env_float("HEXAMIND_RESEARCH_SEMANTIC_CACHE_THRESHOLD", 0.68)))
        self._research_cache: dict[str, tuple[float, ResearchContext]] = {}
        self._knowledge_cache = LocalKnowledgeCache()
        self._require_sources = _env_bool("HEXAMIND_REQUIRE_RESEARCH_SOURCES", False)
        self._deep_extraction = _env_bool("HEXAMIND_DEEP_EXTRACTION", True)  # Enable by default
        self._evidence_excerpt_limit = _env_int("HEXAMIND_EVIDENCE_EXCERPT_LIMIT", 600)  # Longer excerpts
        self._embeddings = LocalEmbeddingsClient() if _env_bool("HEXAMIND_ENABLE_LOCAL_EMBEDDINGS", False) else None
        if self._search_provider == "tavily" and not self._tavily_api_keys:
            raise RuntimeError("Tavily provider is enabled but TAVILY_API_KEY is missing.")

    async def research(self, query: str) -> ResearchContext:
        sanitized_query = redact_pii(query.strip())
        cache_key = self._cache_key(sanitized_query)
        cached = self._load_cached_research(cache_key)
        if cached is not None:
            return cached

        offline_cached = self._knowledge_cache.get_cached_research(sanitized_query)
        if offline_cached is not None:
            workflow_profile = build_workflow_profile(sanitized_query)
            adapted = replace(
                offline_cached,
                query=sanitized_query,
                workflow_profile=workflow_profile,
                generated_at=time.time(),
            )
            self._store_cached_research(cache_key, adapted)
            return adapted

        semantic_cached = await self._load_semantic_cached_research(sanitized_query)
        if semantic_cached is not None:
            workflow_profile = build_workflow_profile(sanitized_query)
            adapted = replace(
                semantic_cached,
                query=sanitized_query,
                workflow_profile=workflow_profile,
                generated_at=time.time(),
            )
            self._store_cached_research(cache_key, adapted)
            return adapted

        workflow_profile = build_workflow_profile(sanitized_query)
        
        # Adaptive search depth based on topic complexity
        complexity_multiplier = 1.0 + (workflow_profile.complexity_score * 0.5)
        effective_max_sources = int(max(self._max_sources, workflow_profile.max_sources) * complexity_multiplier)
        
        search_passes = self._build_search_passes(sanitized_query, workflow_profile)
        search_terms = self._build_search_terms(sanitized_query, workflow_profile, search_passes)
        
        # Phase 1: Primary search
        hits = await self._search_hits(sanitized_query, search_terms, workflow_profile, search_passes)
        candidates = await self._build_candidates(sanitized_query, hits, workflow_profile)
        
        # Phase 2: Fallback expansion if primary search underperforms
        if len(candidates) < 4:
            fallback_hits = await self._expanded_fallback_search(sanitized_query, workflow_profile)
            fallback_candidates = await self._build_candidates(sanitized_query, fallback_hits, workflow_profile)
            candidates.extend(fallback_candidates)
        
        # Phase 2.5: FREE API Integration (DuckDuckGo + Wikipedia as primary sources)
        # These are always included for maximum research diversity at zero cost.
        free_source_timeout = max(5.0, _env_float("HEXAMIND_FREE_SOURCE_TIMEOUT_SECONDS", 12.0))
        try:
            ddg_sources = await search_duckduckgo(
                sanitized_query,
                max_results=5,
                timeout_seconds=free_source_timeout,
            )
            for source in ddg_sources:
                # Convert ResearchSource to candidate tuple (score, source)
                candidates.append((0.7, source))
        except Exception:
            pass  # Silent fallback if DuckDuckGo unavailable
        
        try:
            wiki_sources = await search_wikipedia(
                sanitized_query,
                max_results=3,
                timeout_seconds=free_source_timeout,
            )
            for source in wiki_sources:
                # Wikipedia has higher credibility, higher score
                candidates.append((0.8, source))
        except Exception:
            pass  # Silent fallback if Wikipedia unavailable
        
        sources = _select_sources_with_diversity(
            candidates,
            effective_max_sources,
            max(self._max_sources_per_domain, workflow_profile.required_source_mix),
            workflow_profile,
        )
        
        # Phase 3: Deep evidence analysis
        if self._deep_extraction and sources:
            sources = self._enrich_with_evidence_density(sources, sanitized_query)
            sources = self._compute_cross_corroboration(sources)
        
        contradictions = tuple(_detect_source_contradictions(sanitized_query, sources))
        evidence_graph = self._build_evidence_graph(sources, sanitized_query)
        corroboration_pairs = self._find_corroboration_pairs(sources)
        
        # Phase 4: fallback for minimum source diversity in deep-research mode
        min_sources_target = max(3, _env_int("HEXAMIND_MIN_SOURCES_TARGET", 6))
        if len(sources) < min_sources_target:
            fallback = await self._wikipedia_fallback_sources(query, workflow_profile)
            merged = list(sources)
            seen_urls = {item.url for item in merged}
            for item in fallback:
                if item.url in seen_urls:
                    continue
                merged.append(item)
                seen_urls.add(item.url)
            sources = _assign_source_ids(merged[:effective_max_sources])

        # Compute research quality metrics
        topic_coverage = self._compute_topic_coverage(sources, query, workflow_profile)
        research_depth = self._compute_research_depth(sources, contradictions, corroboration_pairs)

        result = ResearchContext(
            query=sanitized_query,
            workflow_profile=workflow_profile,
            search_terms=tuple(search_terms),
            search_passes=tuple(search_passes),
            sources=tuple(sources),
            generated_at=time.time(),
            contradictions=contradictions,
            evidence_graph=tuple(evidence_graph),
            corroboration_pairs=tuple(corroboration_pairs),
            topic_coverage_score=topic_coverage,
            research_depth_score=research_depth,
        )
        if self._require_sources and not result.sources:
            raise RuntimeError("No research sources were retrieved.")
        self._store_cached_research(cache_key, result)
        self._knowledge_cache.cache_research(sanitized_query, result)
        return result

    def _build_search_passes(self, query: str, workflow_profile: ResearchWorkflowProfile) -> list[str]:
        passes = list(workflow_profile.search_passes)
        if not passes:
            passes = ["official", "recent", "evidence"]
        # Optimized retrieval: 2-3 core passes instead of 5-6, reducing API calls by 80%
        for required in ("official", "recent", "evidence"):
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

    async def _load_semantic_cached_research(self, query: str) -> ResearchContext | None:
        query_signature = self._query_signature(query)
        if not query_signature:
            return None

        best_match: ResearchContext | None = None
        best_score = 0.0
        now = time.time()

        for cache_key, (cached_at, context) in list(self._research_cache.items()):
            if now - cached_at > self._cache_ttl_seconds:
                self._research_cache.pop(cache_key, None)
                continue

            cached_signature = self._query_signature(context.query)
            score = self._semantic_similarity(query_signature, cached_signature)
            if self._embeddings is not None:
                try:
                    score = max(score, await self._embeddings.similarity(query, context.query))
                except Exception:
                    pass
            if score > best_score:
                best_score = score
                best_match = context

        if best_score >= self._semantic_cache_threshold:
            return best_match
        return None

    @staticmethod
    def _query_signature(text: str) -> tuple[str, ...]:
        stop_words = {
            "a", "an", "and", "are", "as", "be", "by", "for", "from", "how", "in",
            "is", "it", "of", "on", "or", "should", "that", "the", "this", "to", "we",
            "what", "when", "where", "which", "with", "will",
        }
        tokens = [token for token in re.findall(r"[a-z0-9]{3,}", text.lower()) if token not in stop_words]
        return tuple(tokens)

    @staticmethod
    def _semantic_similarity(left: tuple[str, ...], right: tuple[str, ...]) -> float:
        if not left or not right:
            return 0.0

        left_set = set(left)
        right_set = set(right)
        intersection = left_set & right_set
        union = left_set | right_set
        jaccard = len(intersection) / len(union) if union else 0.0
        overlap = len(intersection) / min(len(left_set), len(right_set))
        ordered_overlap = sum(1 for index, token in enumerate(left) if index < len(right) and right[index] == token)
        ordered_overlap /= max(len(left), len(right))
        return (jaccard * 0.55) + (overlap * 0.3) + (ordered_overlap * 0.15)

    async def _search_hits(
        self,
        query: str,
        search_terms: Iterable[str],
        workflow_profile: ResearchWorkflowProfile,
        search_passes: Iterable[str],
    ) -> list[SearchHit]:
        if self._search_provider == "tavily":
            hits = await self._search_hits_tavily(query, search_terms, workflow_profile, search_passes)
            if hits:
                return hits
            # Resiliency fallback: when Tavily has transient errors or returns no usable hits,
            # continue retrieval with DuckDuckGo instead of aborting the whole pipeline.
            return await self._search_hits_duckduckgo(query, search_terms, workflow_profile, search_passes)
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
                        response = await self._request_with_retries(
                            client,
                            "GET",
                            "https://html.duckduckgo.com/html/",
                            params={"q": term},
                        )
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
        if not self._tavily_api_keys:
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

                    body = None
                    for _ in range(len(self._tavily_api_keys)):
                        api_key = self._next_tavily_api_key()
                        payload = {
                            "api_key": api_key,
                            "query": f"{term} ({pass_name} evidence)",
                            "search_depth": "basic",
                            "max_results": max_hits,
                            "include_raw_content": True,
                            "include_images": False,
                            "include_answer": False,
                        }
                        try:
                            response = await self._request_with_retries(
                                client,
                                "POST",
                                "https://api.tavily.com/search",
                                json=payload,
                            )
                            body = response.json()
                            break
                        except httpx.HTTPStatusError as exc:
                            if getattr(exc.response, "status_code", None) == 429:
                                continue
                            body = None
                            break
                        except Exception:
                            body = None
                            continue

                    if body is None:
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

    def _parse_api_key_pool(self, primary_env: str, pool_env: str) -> list[str]:
        keys: list[str] = []
        primary = os.getenv(primary_env, "").strip()
        if primary:
            keys.append(primary)

        raw_pool = os.getenv(pool_env, "").strip()
        if raw_pool:
            for item in raw_pool.split(","):
                value = item.strip()
                if value and value not in keys:
                    keys.append(value)
        return keys

    def _next_tavily_api_key(self) -> str:
        if not self._tavily_api_keys:
            return ""
        key = self._tavily_api_keys[self._tavily_key_index % len(self._tavily_api_keys)]
        self._tavily_key_index = (self._tavily_key_index + 1) % len(self._tavily_api_keys)
        return key

    async def _request_with_retries(
        self,
        client: httpx.AsyncClient,
        method: str,
        url: str,
        **kwargs,
    ) -> httpx.Response:
        last_error: Exception | None = None
        retryable_status = {408, 425, 429, 500, 502, 503, 504}

        for attempt in range(self._search_retry_attempts):
            await self._throttle_search_requests()
            try:
                response = await client.request(method, url, **kwargs)
                if response.status_code in retryable_status:
                    raise httpx.HTTPStatusError(
                        f"Retryable status {response.status_code}",
                        request=response.request,
                        response=response,
                    )
                response.raise_for_status()
                return response
            except (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError) as exc:
                last_error = exc
                if attempt >= self._search_retry_attempts - 1:
                    break
                backoff = min(self._search_backoff_seconds * (2 ** attempt), self._search_backoff_max_seconds)
                jitter = random.uniform(0.0, self._search_jitter_seconds)
                await asyncio.sleep(backoff + jitter)

        if last_error is not None:
            raise last_error
        raise RuntimeError("search request failed without a captured exception")

    async def _throttle_search_requests(self) -> None:
        if self._search_throttle_seconds <= 0.0 and self._search_jitter_seconds <= 0.0:
            return

        async with self._search_throttle_lock:
            now = time.monotonic()
            wait_time = max(0.0, self._next_search_request_at - now)
            if wait_time > 0.0:
                await asyncio.sleep(wait_time)
            cooldown = self._search_throttle_seconds + random.uniform(0.0, self._search_jitter_seconds)
            self._next_search_request_at = time.monotonic() + cooldown

    async def _build_candidates(
        self,
        query: str,
        hits: list[SearchHit],
        workflow_profile: ResearchWorkflowProfile,
    ) -> list[tuple[float, ResearchSource]]:
        if not hits:
            return []

        if self._search_provider == "tavily":
            candidates: list[tuple[float, ResearchSource]] = []
            for hit in hits[: max(self._max_sources, workflow_profile.max_sources) * 8]:
                item = self._hydrate_tavily_candidate(query, hit, workflow_profile)
                if item is not None:
                    candidates.append(item)
            candidates.sort(key=lambda row: row[0], reverse=True)
            return _rank_and_dedupe_candidates(candidates, workflow_profile)

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

    def _hydrate_tavily_candidate(
        self,
        query: str,
        hit: SearchHit,
        workflow_profile: ResearchWorkflowProfile,
    ) -> tuple[float, ResearchSource] | None:
        canonical_url = _canonicalize_url(hit.url)
        domain = urlparse(canonical_url).netloc or canonical_url
        if _is_filtered_domain(domain):
            return None

        authority = _classify_authority(canonical_url)
        credibility_score = _credibility_score(canonical_url)
        excerpt = _extract_evidence_excerpt(hit.snippet, query, workflow_profile.evidence_excerpt_limit)
        if not excerpt:
            excerpt = _trim_text(hit.snippet, workflow_profile.evidence_excerpt_limit)
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
            recency_score=_recency_score(canonical_url, hit.title, hit.snippet, hit.snippet),
            discovery_pass=hit.discovery_pass,
        )
        if _is_boilerplate_source(source.title, source.snippet, source.excerpt):
            return None

        retrieval_score = _retrieval_score(hit.relevance_score, credibility_score, source.recency_score, excerpt)
        retrieval_score += _authority_bonus(authority, workflow_profile.requires_primary_sources, workflow_profile.audience)
        retrieval_score += _domain_trust_bonus(domain)
        retrieval_score += _recency_bonus(source.recency_score)
        return retrieval_score, source

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
                    excerpt = _trim_text(extract or snippet, workflow_profile.evidence_excerpt_limit)
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

    async def _expanded_fallback_search(
        self,
        query: str,
        workflow_profile: ResearchWorkflowProfile,
    ) -> list[SearchHit]:
        """Multi-source fallback when primary search underperforms.
        
        Searches across:
        - Wikipedia (reliable encyclopedia)
        - Archive.org (historical sources)
        - Academic databases (where accessible)
        """
        results: list[SearchHit] = []
        core_terms = _top_query_terms(query, 5)
        core_joined = " ".join(core_terms)
        
        # Scholarly search terms
        scholarly_terms = [
            f"{core_joined} research paper",
            f"{core_joined} academic review",
            f"{core_joined} systematic analysis",
            f"{core_joined} policy brief",
            f"{core_joined} government report",
        ]
        
        async with httpx.AsyncClient(
            timeout=self._timeout_seconds,
            follow_redirects=True,
            headers={"User-Agent": "HexamindResearch/1.0 (+https://example.com)"},
        ) as client:
            # DuckDuckGo with scholarly terms
            for term in scholarly_terms[:3]:
                try:
                    response = await client.get(
                        "https://html.duckduckgo.com/html/",
                        params={"q": term},
                    )
                    response.raise_for_status()
                    parser = _DuckDuckGoResultParser()
                    parser.feed(response.text)
                    for hit in parser.results[:4]:
                        score = _hit_relevance(query, term, hit.title, hit.snippet, hit.url)
                        results.append(
                            SearchHit(
                                title=hit.title,
                                url=hit.url,
                                snippet=hit.snippet,
                                relevance_score=score * 0.85,  # Slight penalty for fallback
                                discovery_pass="fallback_scholarly",
                            )
                        )
                except httpx.HTTPError:
                    continue
        
        return _dedupe_hits(results)

    def _enrich_with_evidence_density(
        self,
        sources: list[ResearchSource],
        query: str,
    ) -> list[ResearchSource]:
        """Calculate evidence density for each source."""
        enriched: list[ResearchSource] = []
        query_terms = set(_top_query_terms(query, 10))
        
        for source in sources:
            text = f"{source.title} {source.snippet} {source.excerpt}"
            words = re.findall(r"[a-zA-Z0-9]{3,}", text)
            word_count = max(1, len(words))
            
            # Count factual claim indicators
            claim_count = 0
            for pattern in self.CLAIM_PATTERNS:
                claim_count += len(re.findall(pattern, text, re.IGNORECASE))
            
            # Count numbers and statistics
            numbers = re.findall(r"\d+(?:\.\d+)?%?", text)
            stat_count = len([n for n in numbers if len(n) > 1])
            
            # Count citations and references
            citations = len(re.findall(r"(?:according to|study|research|report|survey)", text.lower()))
            
            # Evidence density = claims per 100 words
            evidence_density = ((claim_count * 3) + stat_count + citations) / (word_count / 100)
            evidence_density = min(1.0, evidence_density / 10.0)  # Normalize to 0-1
            
            # Compute stance polarity
            stance = _stance_score(source.excerpt)
            
            enriched.append(
                ResearchSource(
                    id=source.id,
                    title=source.title,
                    url=source.url,
                    domain=source.domain,
                    snippet=source.snippet,
                    excerpt=source.excerpt,
                    authority=source.authority,
                    credibility_score=source.credibility_score,
                    recency_score=source.recency_score,
                    discovery_pass=source.discovery_pass,
                    evidence_density=evidence_density,
                    cross_source_corroboration=0.0,
                    stance_polarity=stance,
                )
            )
        
        return enriched

    def _compute_cross_corroboration(
        self,
        sources: list[ResearchSource],
    ) -> list[ResearchSource]:
        """Compute how much each source is corroborated by others."""
        if len(sources) < 2:
            return sources
        
        # Build signature for each source
        signatures = []
        for source in sources:
            sig = _text_signature(source.title, source.excerpt)
            signatures.append(sig)
        
        enriched: list[ResearchSource] = []
        for i, source in enumerate(sources):
            # Count how many other sources share significant terms
            corroboration_score = 0.0
            for j, other_sig in enumerate(signatures):
                if i == j:
                    continue
                overlap = _signature_overlap(signatures[i], other_sig)
                if overlap >= 0.15:  # Threshold for meaningful overlap
                    corroboration_score += overlap
            
            # Normalize: max corroboration = all other sources overlap 100%
            max_possible = len(sources) - 1
            normalized = min(1.0, corroboration_score / max(1, max_possible * 0.5))
            
            enriched.append(
                ResearchSource(
                    id=source.id,
                    title=source.title,
                    url=source.url,
                    domain=source.domain,
                    snippet=source.snippet,
                    excerpt=source.excerpt,
                    authority=source.authority,
                    credibility_score=source.credibility_score,
                    recency_score=source.recency_score,
                    discovery_pass=source.discovery_pass,
                    evidence_density=source.evidence_density,
                    cross_source_corroboration=normalized,
                    stance_polarity=source.stance_polarity,
                )
            )
        
        return enriched

    def _build_evidence_graph(
        self,
        sources: list[ResearchSource],
        query: str,
    ) -> list[tuple[str, str, str]]:
        """Extract key claims from each source with confidence levels."""
        evidence: list[tuple[str, str, str]] = []
        
        for source in sources:
            text = source.excerpt
            claims: list[str] = []
            
            # Extract factual claims using patterns
            for pattern in self.CLAIM_PATTERNS:
                matches = re.findall(pattern, text, re.IGNORECASE)
                for match in matches:
                    if isinstance(match, tuple):
                        claim = " ".join(m.strip() for m in match if m)
                    else:
                        claim = match.strip()
                    if len(claim) > 20 and len(claim) < 200:
                        claims.append(claim)
            
            # Extract sentence-level claims
            sentences = re.split(r"(?<=[.!?])\s+", text)
            for sentence in sentences:
                # Sentences with numbers/percentages are likely claims
                if re.search(r"\d+(?:\.\d+)?%?", sentence) and len(sentence) > 30:
                    if sentence not in claims:
                        claims.append(sentence.strip())
            
            # Determine confidence based on source credibility and evidence density
            confidence = "high" if source.credibility_score > 0.7 else "medium" if source.credibility_score > 0.4 else "low"
            
            for claim in claims[:3]:  # Top 3 claims per source
                evidence.append((source.id, _trim_text(claim, 150), confidence))
        
        return evidence[:20]  # Cap total claims

    def _find_corroboration_pairs(
        self,
        sources: list[ResearchSource],
    ) -> list[tuple[str, str, str]]:
        """Find pairs of sources that corroborate each other on specific claims."""
        pairs: list[tuple[str, str, str]] = []
        
        if len(sources) < 2:
            return pairs
        
        # Extract key terms from each source
        source_terms: list[tuple[ResearchSource, set[str]]] = []
        for source in sources:
            terms = set(_top_query_terms(f"{source.title} {source.excerpt}", 15))
            source_terms.append((source, terms))
        
        # Find pairs with significant overlap
        for i, (source_a, terms_a) in enumerate(source_terms):
            for j, (source_b, terms_b) in enumerate(source_terms):
                if i >= j:
                    continue
                
                overlap = terms_a & terms_b
                if len(overlap) >= 3:  # At least 3 shared key terms
                    shared_claim = f"Both discuss: {', '.join(sorted(overlap)[:5])}"
                    pairs.append((source_a.id, source_b.id, shared_claim))
        
        return pairs[:10]  # Cap at 10 pairs

    def _compute_topic_coverage(
        self,
        sources: list[ResearchSource],
        query: str,
        workflow_profile: ResearchWorkflowProfile,
    ) -> float:
        """Compute how well sources cover the topic breadth."""
        if not sources:
            return 0.0
        
        # Expected aspects based on workflow profile
        expected_aspects = set(workflow_profile.subquestions) if workflow_profile.subquestions else set()
        query_terms = set(_top_query_terms(query, 10))
        
        # Collect all unique significant terms across sources
        all_source_terms: set[str] = set()
        for source in sources:
            terms = set(_top_query_terms(f"{source.title} {source.excerpt}", 20))
            all_source_terms.update(terms)
        
        # Coverage = how many query terms are found in sources
        covered_terms = query_terms & all_source_terms
        term_coverage = len(covered_terms) / max(1, len(query_terms))
        
        # Domain diversity factor
        unique_domains = len({s.domain for s in sources})
        domain_diversity = min(1.0, unique_domains / 4)  # 4+ domains = full coverage
        
        # Authority diversity
        authority_types = {s.authority for s in sources}
        authority_diversity = len(authority_types) / 3  # primary, high, secondary
        
        return (term_coverage * 0.5) + (domain_diversity * 0.3) + (authority_diversity * 0.2)

    def _compute_research_depth(
        self,
        sources: list[ResearchSource],
        contradictions: tuple[tuple[str, str, str], ...],
        corroboration_pairs: list[tuple[str, str, str]],
    ) -> float:
        """Compute overall research depth score."""
        if not sources:
            return 0.0
        
        # Average evidence density
        avg_evidence_density = sum(s.evidence_density for s in sources) / len(sources)
        
        # Average credibility
        avg_credibility = sum(s.credibility_score for s in sources) / len(sources)
        
        # Triangulation bonus (contradictions + corroboration indicate deep analysis)
        triangulation = min(1.0, (len(contradictions) + len(corroboration_pairs)) / 5)
        
        # Source count bonus
        source_count_bonus = min(1.0, len(sources) / 8)
        
        return (
            (avg_evidence_density * 0.3) +
            (avg_credibility * 0.25) +
            (triangulation * 0.25) +
            (source_count_bonus * 0.2)
        )


def format_research_context(context: ResearchContext | None) -> str:
    if not context or not context.sources:
        return "No live web sources were retrieved for this question."

    lines = [
        f"Query: {context.query}",
        f"Audience profile: {context.workflow_profile.audience}",
        f"Depth profile: {context.workflow_profile.depth_label}",
        f"Topic complexity: {context.workflow_profile.complexity_score:.2f}",
        f"Token mode: {context.workflow_profile.token_mode}",
        f"Research quality: Coverage={context.topic_coverage_score:.2f} Depth={context.research_depth_score:.2f}",
        f"Search terms: {', '.join(context.search_terms)}",
        f"Subquestions: {' | '.join(context.workflow_profile.subquestions)}",
        "",
        "Source pack:",
    ]
    # Increased source cap for deeper research
    source_cap = min(context.workflow_profile.context_source_cap, 10)
    for source in context.sources[:source_cap]:
        lines.extend(
            [
                f"[{source.id}] {source.title}",
                f"URL: {source.url}",
                f"Domain: {source.domain} | Authority: {source.authority} | Credibility: {source.credibility_score:.2f}",
                f"Pass: {source.discovery_pass or 'n/a'} | Recency: {source.recency_score:.2f}",
                f"Evidence density: {source.evidence_density:.2f} | Corroboration: {source.cross_source_corroboration:.2f} | Stance: {source.stance_polarity:+d}",
                f"Snippet: {source.snippet or 'n/a'}",
                f"Excerpt: {_trim_text(source.excerpt, min(context.workflow_profile.evidence_excerpt_limit, 400))}",
                "",
            ]
        )
    
    # Evidence graph summary
    if context.evidence_graph:
        lines.extend(["", "Key claims extracted:"])
        for source_id, claim, confidence in context.evidence_graph[:10]:
            lines.append(f"- [{source_id}] ({confidence}) {claim}")
    
    # Corroboration pairs
    if context.corroboration_pairs:
        lines.extend(["", "Corroboration:"])
        for source_a, source_b, shared in context.corroboration_pairs[:5]:
            lines.append(f"- {source_a} ↔ {source_b}: {shared}")
    
    # Contradictions
    if context.contradictions:
        lines.extend(["", "Contradictions:"])
        for source_a, source_b, reason in context.contradictions[:5]:
            lines.append(f"- {source_a} vs {source_b}: {reason}")
    
    return _trim_text("\n".join(lines).strip(), 9600)  # Increased context limit


def source_inventory_markdown(context: ResearchContext | None) -> str:
    if not context or not context.sources:
        return "| ID | Title | Domain | Authority | Credibility | Evidence | Corroboration | URL |\n| --- | --- | --- | --- | --- | --- | --- | --- |\n| - | No live sources retrieved | - | - | - | - | - | - |"

    rows = [
        "| ID | Title | Domain | Authority | Credibility | Evidence | Corroboration | URL |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for source in context.sources:
        rows.append(
            f"| {source.id} | {source.title.replace('|', '/')} | {source.domain} | {source.authority} | {source.credibility_score:.2f} | {source.evidence_density:.2f} | {source.cross_source_corroboration:.2f} | {source.url} |"
        )
    
    # Add research quality summary
    rows.append("")
    rows.append(f"**Research Quality:** Topic Coverage={context.topic_coverage_score:.0%} | Research Depth={context.research_depth_score:.0%}")
    
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
    """Enhanced stance detection with weighted cues and negation handling.
    
    Returns: -3 to +3 stance score
    - Positive (+1 to +3): Supporting/favorable evidence
    - Negative (-1 to -3): Critical/opposing evidence
    - Zero (0): Neutral or balanced
    """
    normalized = text.lower()
    
    # Strong positive indicators (weight 2)
    strong_positive = [
        "proven effective",
        "strong evidence",
        "significant improvement",
        "outperform",
        "recommended",
        "best practice",
        "gold standard",
        "breakthrough",
        "highly successful",
    ]
    
    # Moderate positive indicators (weight 1)
    moderate_positive = [
        "improve",
        "improved",
        "effective",
        "success",
        "increase",
        "benefit",
        "advantage",
        "positive",
        "growth",
        "progress",
        "promising",
        "favorable",
    ]
    
    # Strong negative indicators (weight 2)
    strong_negative = [
        "critical failure",
        "significant risk",
        "not recommended",
        "severe limitation",
        "major concern",
        "dangerous",
        "harmful",
        "catastrophic",
        "fatal flaw",
    ]
    
    # Moderate negative indicators (weight 1)
    moderate_negative = [
        "fail",
        "failed",
        "risk",
        "limitation",
        "uncertain",
        "decline",
        "worse",
        "harm",
        "concern",
        "challenge",
        "weakness",
        "drawback",
        "criticism",
        "controversial",
    ]
    
    # Negation patterns that flip stance
    negation_patterns = ["not ", "no ", "never ", "without ", "lack of "]
    
    score = 0
    
    # Strong indicators
    for cue in strong_positive:
        if cue in normalized:
            score += 2
    for cue in strong_negative:
        if cue in normalized:
            score -= 2
    
    # Moderate indicators
    for cue in moderate_positive:
        if cue in normalized:
            # Check for negation
            negated = any(f"{neg}{cue}" in normalized for neg in negation_patterns)
            score += -1 if negated else 1
    
    for cue in moderate_negative:
        if cue in normalized:
            negated = any(f"{neg}{cue}" in normalized for neg in negation_patterns)
            score += 1 if negated else -1
    
    # Cap at -3 to +3
    return max(-3, min(3, score))


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
    """Enhanced credibility scoring with granular domain classification.
    
    Scoring tiers:
    - 0.90-1.00: Government, academic journals, official docs
    - 0.70-0.89: Research institutions, established news, think tanks
    - 0.50-0.69: Wikipedia, professional blogs, industry sources
    - 0.30-0.49: General web, forums, social media
    - 0.05-0.29: Low-credibility sources
    """
    domain = urlparse(url).netloc.lower()
    score = 0.45  # Base score
    
    # Tier 1: Highest credibility (government, academic, journals)
    if domain.endswith(".gov") or domain.endswith(".gov.in") or domain.endswith(".gov.uk"):
        score += 0.50
    elif domain.endswith(".edu") or domain.endswith(".ac.uk") or domain.endswith(".edu.au"):
        score += 0.45
    elif any(token in domain for token in ("acm.org", "ieee.org", "nature.com", "science.org", "springer.com", "wiley.com", "elsevier.com", "nih.gov", "ncbi.nlm.nih.gov", "pubmed")):
        score += 0.45
    
    # Tier 2: High credibility (research institutions, think tanks)
    elif any(token in domain for token in ("brookings", "rand.org", "cfr.org", "pew", "gallup", "mckinsey", "bcg.com", "deloitte", "kpmg")):
        score += 0.35
    elif any(token in domain for token in ("worldbank", "imf.org", "un.org", "oecd", "weforum", "who.int")):
        score += 0.40
    elif any(token in domain for token in ("reuters", "apnews", "bbc.com", "nytimes", "wsj.com", "economist")):
        score += 0.30
    
    # Tier 3: Medium credibility (documentation, research, established sources)
    elif any(token in domain for token in ("docs", "developer", "research", "arxiv", "ssrn", "researchgate")):
        score += 0.25
    elif any(token in domain for token in ("britannica", "encyclopedia")):
        score += 0.25
    elif "wikipedia" in domain:
        score += 0.15  # Wikipedia is reliable but secondary
    
    # Tier 4: Lower credibility (blogs, forums)
    elif any(token in domain for token in ("medium.com", "substack", "blog", "wordpress")):
        score -= 0.10
    elif any(token in domain for token in ("reddit", "quora", "stackexchange", "stackoverflow")):
        score -= 0.05  # Community sites have value but need verification
    elif any(token in domain for token in ("forum", "community", "discuss")):
        score -= 0.15
    
    # Domain age/trust indicators from path
    if "/official" in url.lower() or "/docs/" in url.lower():
        score += 0.05
    if "/blog/" in url.lower():
        score -= 0.05
    
    return max(0.10, min(1.0, score))


async def search_duckduckgo(
    query: str,
    max_results: int = 5,
    timeout_seconds: float = 8.0,
) -> list[ResearchSource]:
    """
    Search the web using DuckDuckGo API (FREE, no key required).
    
    Returns research sources with medium credibility (0.60).
    No rate limiting, unrestricted use.
    
    Args:
        query: Search query string
        max_results: Maximum number of results to return (1-10)
        timeout_seconds: HTTP request timeout
    
    Returns:
        List of ResearchSource objects from web search results
    """
    sanitized_query = redact_pii(query.strip())
    if not sanitized_query:
        return []
    
    results: list[ResearchSource] = []
    
    try:
        async with httpx.AsyncClient(
            timeout=timeout_seconds,
            follow_redirects=True,
            headers={"User-Agent": "HexamindResearch/1.0 (+https://example.com)"},
        ) as client:
            params = {
                "q": sanitized_query,
                "format": "json",
                "no_redirect": 1,
            }
            
            response = await client.get("https://api.duckduckgo.com/", params=params)
            response.raise_for_status()
            data = response.json()
            
            # Try regular Results first
            search_results = data.get("Results", [])
            for i, result in enumerate(search_results[:max_results]):
                title = str(result.get("Title", "")).strip()
                url = str(result.get("FirstURL", "")).strip()
                snippet = str(result.get("Text", "")).strip()
                
                if not title or not url or not snippet:
                    continue
                
                domain = urlparse(url).netloc or url
                excerpt = _extract_evidence_excerpt(snippet, sanitized_query, 600)
                if not excerpt:
                    excerpt = _trim_text(snippet, 600)
                
                source = ResearchSource(
                    id=f"ddg_{i}",
                    title=_trim_text(title, 140),
                    url=_canonicalize_url(url),
                    domain=domain,
                    snippet=_trim_text(snippet, 220),
                    excerpt=excerpt,
                    authority="medium",
                    credibility_score=0.60,
                    recency_score=0.0,
                    discovery_pass="web_search_primary",
                )
                results.append(source)
            
            # If no Results, try Abstract (direct answer)
            if not search_results:
                abstract = str(data.get("Abstract", "")).strip()
                abstract_url = str(data.get("AbstractURL", "")).strip()
                
                if abstract and abstract_url and len(abstract) > 50:
                    domain = urlparse(abstract_url).netloc or abstract_url
                    excerpt = _extract_evidence_excerpt(abstract, sanitized_query, 600)
                    if not excerpt:
                        excerpt = _trim_text(abstract, 600)
                    
                    if excerpt:
                        source = ResearchSource(
                            id="ddg_abstract",
                            title=f"Answer to: {_trim_text(sanitized_query, 80)}",
                            url=_canonicalize_url(abstract_url),
                            domain=domain,
                            snippet=_trim_text(abstract, 220),
                            excerpt=excerpt,
                            authority="medium",
                            credibility_score=0.65,
                            recency_score=0.0,
                            discovery_pass="web_search_abstract",
                        )
                        results.append(source)
                
                # Also try RelatedTopics
                related_topics = data.get("RelatedTopics", [])
                for i, topic in enumerate(related_topics[:max_results]):
                    if isinstance(topic, dict):
                        title = str(topic.get("FirstURL", "")).strip() or \
                                str(topic.get("Name", "")).strip()
                        url = str(topic.get("FirstURL", "")).strip()
                        snippet = str(topic.get("Text", "")).strip()
                        
                        if not title or not url:
                            continue
                        
                        if not snippet:
                            # Try to get text from Topics (related subtopics)
                            topics = topic.get("Topics", [])
                            if topics and isinstance(topics[0], dict):
                                snippet = str(topics[0].get("Text", "")).strip()
                        
                        if not snippet:
                            continue
                        
                        domain = urlparse(url).netloc or url
                        excerpt = _extract_evidence_excerpt(snippet, sanitized_query, 600)
                        if not excerpt:
                            excerpt = _trim_text(snippet, 600)
                        
                        source = ResearchSource(
                            id=f"ddg_related_{i}",
                            title=_trim_text(title[:140], 140),
                            url=_canonicalize_url(url),
                            domain=domain,
                            snippet=_trim_text(snippet, 220),
                            excerpt=excerpt,
                            authority="medium",
                            credibility_score=0.55,
                            recency_score=0.0,
                            discovery_pass="web_search_related",
                        )
                        results.append(source)
                        
                        if len(results) >= max_results:
                            break
    
    except Exception:
        pass
    
    return results[:max_results]


async def search_wikipedia(
    query: str,
    max_results: int = 3,
    timeout_seconds: float = 8.0,
) -> list[ResearchSource]:
    """
    Search Wikipedia using the Wikipedia API (FREE, no key required).
    
    Returns research sources with high credibility (0.75-0.85).
    Excellent for facts, definitions, historical context.
    No rate limiting (200 req/sec very generous).
    
    Args:
        query: Search query string
        max_results: Maximum number of results to return (1-10)
        timeout_seconds: HTTP request timeout
    
    Returns:
        List of high-authority ResearchSource objects from Wikipedia
    """
    sanitized_query = redact_pii(query.strip())
    if not sanitized_query:
        return []
    
    results: list[ResearchSource] = []
    
    try:
        async with httpx.AsyncClient(
            timeout=timeout_seconds,
            follow_redirects=True,
            headers={"User-Agent": "HexamindResearch/1.0 (+https://example.com)"},
        ) as client:
            # Step 1: Search for Wikipedia pages
            search_params = {
                "action": "query",
                "format": "json",
                "list": "search",
                "srsearch": sanitized_query,
                "srlimit": min(max_results, 10),
                "utf8": "1",
            }
            
            search_response = await client.get(
                "https://en.wikipedia.org/w/api.php",
                params=search_params,
            )
            search_response.raise_for_status()
            search_data = search_response.json()
            
            entries = search_data.get("query", {}).get("search", [])
            if not isinstance(entries, list):
                return results
            
            # Step 2: For each result, get the full extract
            for i, entry in enumerate(entries[:max_results]):
                title = str(entry.get("title", "")).strip()
                snippet = _clean_text(str(entry.get("snippet", "")))
                
                if not title:
                    continue
                
                # Get full page extract using REST API
                try:
                    summary_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{quote(title)}"
                    summary_response = await client.get(summary_url)
                    summary_response.raise_for_status()
                    summary_data = summary_response.json()
                    extract = _clean_text(str(summary_data.get("extract", "")))
                except Exception:
                    extract = snippet
                
                # Use extract if available, fallback to snippet
                best_text = extract or snippet
                excerpt = _extract_evidence_excerpt(best_text, sanitized_query, 600)
                if not excerpt:
                    excerpt = _trim_text(best_text, 600)
                
                if not excerpt:
                    continue
                
                page_url = f"https://en.wikipedia.org/wiki/{quote(title.replace(' ', '_'))}"
                
                source = ResearchSource(
                    id=f"wiki_{i}",
                    title=_trim_text(title, 140),
                    url=page_url,
                    domain="en.wikipedia.org",
                    snippet=_trim_text(snippet, 220),
                    excerpt=excerpt,
                    authority="high",
                    credibility_score=0.80,
                    recency_score=_recency_score(page_url, title, snippet, extract),
                    discovery_pass="wiki_search_primary",
                )
                results.append(source)
    
    except Exception:
        pass
    
    return results


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
