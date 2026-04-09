import asyncio
import json
import logging
import re
from dataclasses import replace
from typing import List, Dict, Any, Optional
from inference_provider import InferenceProvider, get_provider
from research import InternetResearcher

logger = logging.getLogger(__name__)

class WorkerRole:
    RESEARCHER = "researcher"
    ANALYST = "analyst"
    HISTORIAN = "historian"
    AUDITOR = "auditor"

class ResearchWorker:
    """Specialized worker that handles a specific research node."""
    
    def __init__(self, role: str, provider: Optional[InferenceProvider] = None):
        self.role = role
        self.provider = provider if provider is not None else get_provider()
        self.researcher = InternetResearcher()

    async def gather_evidence(self, topic: str, parent_context: Optional[str] = None) -> Any:
        """Prefetch research context over the network (Sequential Discovery).
        If parent_context is provided, refine the search based on parent findings.
        """
        # Pass 1: Targeted search query generation with Scrubbing
        search_query = await self._generate_search_query(topic, parent_context)
        search_query = self._scrub_query(search_query)
        
        print(f"📡 [DISCOVERY] Investigating: {topic} | Query: {search_query}", flush=True)
        initial_context = await self.researcher.research(search_query)
        
        # Pass 2: Niche Recursive Expansion (if first pass yielded enough context)
        if initial_context.sources and len(initial_context.sources) > 3:
            niche_query = await self._generate_niche_expansion_query(topic, initial_context)
            print(f"📡 [LAYERED] Deep-diving into niche: {niche_query}", flush=True)
            niche_context = await self.researcher.research(niche_query)
            
            # Merge sources (avoiding duplicates)
            seen_urls = {s.url for s in initial_context.sources}
            merged_sources = list(initial_context.sources)
            for s in niche_context.sources:
                if s.url not in seen_urls:
                    merged_sources.append(s)
                    seen_urls.add(s.url)
            
            initial_context = replace(initial_context, sources=tuple(merged_sources))
            
        return initial_context

    async def _generate_niche_expansion_query(self, topic: str, context: Any) -> str:
        """Extract a high-specificity sub-topic for the second research pass."""
        prompt = (
            f"Based on the initial research for '{topic}', identify ONE highly specific, "
            f"niche technical detail or structural risk that requires deeper investigation.\n"
            f"Context Snippets:\n" + "\n".join([s.snippet[:150] for s in context.sources[:5]]) + "\n"
            "Output ONLY the search query."
        )
        return await self.provider.generate_text(prompt, max_tokens=20)

    async def run_analysis(self, topic: str, research_context: Any, context: Optional[str] = None, initial_draft: Optional[str] = None, anchors: List[Dict[str, str]] = None) -> Dict[str, Any]:
        """Execute the worker's inference as a JSON Editor."""
        logger.info(f"Worker [{self.role}] starting editorial review on topic: {topic}")
        
        # 1. Specialized Analysis (JSON Diff + Rationale)
        raw_output = await self._analyze(topic, research_context.sources, context, initial_draft, anchors)
        
        # 2. Parse JSON safely and extract rationale
        diffs = []
        analysis_summary = "No significant changes identified."
        
        try:
            # Strip any markdown code blocks if the model included them
            clean_output = re.sub(r"```json\s*|\s*```", "", raw_output.strip())
            
            # Check if output is a wrapper object { "diffs": [], "rationale": "" } or just an array
            parsed = json.loads(clean_output)
            if isinstance(parsed, dict):
                diffs = parsed.get("diffs", [])
                analysis_summary = parsed.get("rationale", "Corrections applied based on new evidence.")
            else:
                diffs = parsed
                analysis_summary = f"Editorial pass completed by {self.role.capitalize()} persona."
        except Exception:
            logger.error(f"Worker [{self.role}] failed to produce valid JSON: {raw_output}")
            # Fallback: if it's not JSON, treat it as the analysis summary itself if it has content
            if len(raw_output.strip()) > 20:
                analysis_summary = raw_output.strip()
            
        return {
            "role": self.role,
            "topic": topic,
            "diffs": diffs,
            "analysis": analysis_summary,
            "sources": [s.url for s in research_context.sources[:3]]
        }

    def _scrub_query(self, query: str) -> str:
        """Removes conversational filler and model meta-talk from search queries."""
        # Remove quotes, "Search for...", etc.
        query = re.sub(r'["\']|search (for|query:?)|here is a query:?', '', query, flags=re.IGNORECASE)
        # Remove common preamble
        query = re.sub(r'^(query|search)\s+', '', query.strip(), flags=re.IGNORECASE)
        return query.strip()

    async def _generate_search_query(self, topic: str, parent_context: Optional[str] = None) -> str:
        """Tailor the search query based on the worker's role and discovery context."""
        if parent_context:
            prompt = (
                f"You are a Research Architect. Generate a high-precision search query for the sub-topic: '{topic}'.\n"
                f"PARENT CONTEXT (Findings from previous nodes):\n{parent_context[:1200]}\n\n"
                "Requirements:\n"
                "1. Focus the query on verifying or EXPLICITLY expanding upon specific details discovered in the parent context.\n"
                "2. NO generic queries. Use technical keywords from the parent findings.\n"
                "3. Output ONLY the search query string."
            )
            return await self.provider.generate_text(prompt, max_tokens=40)

        # Fallback for root nodes (no parent context)
        prompts = {
            WorkerRole.RESEARCHER: f"Find current facts, statistical paradoxes, outcomes, and Reddit/forum sentiment regarding {topic}",
            WorkerRole.HISTORIAN: f"Find historical evolution, policy shifts, and developmental timeline for {topic}",
            WorkerRole.AUDITOR: f"Find critical assessments, user complaints, social downsides, and dissenting views on {topic}",
            WorkerRole.ANALYST: f"Find implementation strategies, future projections, and mechanistic outcomes for {topic}"
        }
        return prompts.get(self.role, topic)

    async def _analyze(self, topic: str, sources: List[Any], context: Optional[str] = None, initial_draft: Optional[str] = None, anchors: List[Dict[str, str]] = None) -> str:
        """Perform specialized synthesis with JSON Diff output for ADD architecture."""
        source_text = "\n".join([f"- {s.title}: {s.excerpt}" for s in sources[:5]])
        anchors_str = "\n".join([f"[{a['id']}] {a['fact']}" for a in (anchors or [])])
        
        # PILLAR 10: Persona Lexicons & PILLAR 4: Behavioral Frameworks integration
        system_prompts = {
            WorkerRole.RESEARCHER: (
                "You are a Fact-Checking Specialist Editor. PILLAR 2: You MUST prioritize hard data, "
                "scalars, market percentages, and unit statistics. Every claim must be grounded in a number if possible."
            ),
            WorkerRole.HISTORIAN: (
                "You are a Senior Historian. Frame developments through institutional evolution. "
                "PILLAR 14: You MUST specifically seek and highlight GEOGRAPHIC DISPARITIES and regional adoption variances (e.g., US vs EU vs Asia)."
            ),
            WorkerRole.AUDITOR: (
                "You are a Structural Risk Officer. PILLAR 3: Your task is Red-Teaming. Identify un-anchored claims, "
                "systemic fragilities, innovation deficits, and regulatory contradictions."
            ),
            WorkerRole.ANALYST: (
                "You are a Senior Behavioral Economist (McKinsey/BCG style). "
                "PILLAR 13: You MUST apply 'Total Economic Impact' (TEI) modeling. Create a 'Composite Organization' "
                "of 1,000 employees and quantify the fiscal impact (ROI/TCO) based on the evidence."
            )
        }
        
        if self.role == WorkerRole.AUDITOR:
            prompt = (
                f"You are the Structural Auditor. Review this draft research for topic: '{topic}'\n\n"
                f"PARENT CONTEXT (High-level findings from parent nodes):\n{context or 'N/A'}\n\n"
                f"Draft to Edit:\n{initial_draft or 'No draft provided.'}\n\n"
                f"Provided Anchors (Truth Grounding):\n{anchors_str}\n\n"
                "Task: Critical Red-Teaming. Find any claim in the draft NOT present in Anchors or that contradicts Parent Context.\n"
                "Output as JSON object with 'diffs' array and 'rationale' string summary.\n"
                "Format: {\"diffs\": [{\"original_text_snippet\": \"...\", \"replacement_text\": \"\"}], \"rationale\": \"Identify specific grounding failures or contradictions.\"}\n"
                "Crucial: Do NOT repeat the input text. If grounded, rationale='Analysis verified against anchors.' and diffs=[]"
            )
        else:
            prompt = (
                f"You are the {self.role.capitalize()} Agent. Review this draft for: '{topic}'\n\n"
                f"PARENT CONTEXT (Previous findings to build upon):\n{context or 'N/A'}\n\n"
                f"Draft to Edit:\n{initial_draft or 'No draft provided.'}\n\n"
                f"New Evidence to integrate:\n{source_text}\n\n"
                "Task: Refine the draft by integrating new facts from Evidence that aren't already covered. Use parent context for continuity.\n"
                "For ANALYSTS: You MUST apply a technical Mental Model to the new data.\n"
                "Output as JSON object with 'diffs' array and 'rationale' string summary.\n"
                "Format: {\"diffs\": [{\"original_text_snippet\": \"...\", \"replacement_text\": \"...\"}], \"rationale\": \"Short, insightful summary of how this new data shifts the narrative.\"}\n"
                "Crucial: Rationale MUST ONLY contain NEW insights. DO NOT REPEAT PARENT CONTEXT OR DRAFT CONTENT. If no new data, keep diffs empty and rationale='No unique additions'."
            )
        
        return await self.provider.generate_text(
            prompt,
            system_prompt=system_prompts.get(self.role, "You are an Expert Strategist. Output ONLY JSON."),
            max_tokens=300 # Increased for rationale
        )


class DistillationWorker:
    """Parallel foraging worker for the Atomic Distillation Swarm (0.5B model).
    Extracts high-density Fact Triplets from raw source snippets.
    """
    def __init__(self, provider: Optional[InferenceProvider] = None):
        self.provider = provider if provider is not None else get_provider()

    async def distill(self, topic: str, snippets: List[str]) -> List[str]:
        """Distill 10-15 raw snippets into a list of atomic, verifiable facts."""
        combined = "\n".join([f"- {s}" for s in snippets])
        prompt = (
            f"Extract exactly 5-8 Atomic Facts (Subject -> Link -> Metric/Data) from these sources regarding: {topic}\n\n"
            f"{combined}\n\n"
            "Requirements:\n"
            "1. Output ONLY a bulleted list of facts.\n"
            "2. Each fact must be a single, standalone sentence.\n"
            "3. Focus on numbers, dates, and proper nouns."
        )
        try:
            result = await self.provider.generate_text(
                prompt,
                system_prompt="You are an Atomic Distiller. Output ONLY bullet points.",
                max_tokens=250
            )
            return [line.strip("- ").strip() for line in result.split("\n") if line.strip()]
        except Exception as e:
            logger.error(f"Distillation failed: {e}")
            return []


class AnchorWorker:
    """Synthesizes the Distilled Ledger into high-fidelity Grounding Anchors."""
    def __init__(self, provider: Optional[InferenceProvider] = None):
        self.provider = provider if provider is not None else get_provider()

    async def extract(self, topic: str, fact_ledger: List[str], existing_wiki: Optional[str] = None) -> List[Dict[str, str]]:
        combined_facts = "\n".join([f"- {f}" for f in fact_ledger])

        if existing_wiki:
            combined_facts = f"EXISTING WIKI CONTINUITY:\n{existing_wiki}\n\nNEW DISTILLED FACTS:\n{combined_facts}"

        prompt = (
            f"Synthesize the following list of raw distilled facts into 8-10 'Atomic Grounding Anchors' for the topic: {topic}\n\n"
            f"{combined_facts}\n\n"
            "Requirements:\n"
            "1. Output ONLY a valid JSON array.\n"
            "2. Format: [{\"id\": \"A1\", \"fact\": \"<the exact stat/fact>\"}]\n"
            "3. Deduplicate and prioritize high-impact metrics."
        )

        try:
            result_str = await self.provider.generate_text(
                prompt,
                system_prompt="You are an Anchor Synthesizer. Output ONLY JSON.",
                max_tokens=500
            )
            clean_json = re.sub(r"```json\s*|\s*```", "", result_str.strip())
            return json.loads(clean_json)
        except Exception as e:
            logger.error(f"Anchor synthesis failed: {e}")
            return []


class DraftingWorker:
    """Fast drafting worker for ADD architecture (0.5B model)."""
    
    def __init__(self, provider: Optional[InferenceProvider] = None):
        self.provider = provider if provider is not None else get_provider()

    async def draft(self, query: str, contexts: List[Any], existing_wiki: Optional[str] = None, anchors: List[Dict[str, str]] = None) -> str:
        """Generate a high-fidelity Strategic Narrative, strictly constrained by Anchors."""
        anchors_str = "\n".join([f"[{a['id']}] {a['fact']}" for a in (anchors or [])])

        if existing_wiki:
            prompt = (
                f"You are a Senior Strategic Synthesiser. Update the following Wiki Page for the query: {query}\n\n"
                f"EXISTING WIKI CONTENT:\n{existing_wiki}\n\n"
                f"MANDATORY NEW ANCHORS TO INTEGRATE:\n{anchors_str}\n\n"
                "Your Task:\n"
                "1. Update the document with a focus on THEMATIC FLOW and strategic insight.\n"
                "2. PILLAR 4: Use professional lexicons (McKinsey/BCG style).\n"
                "3. AGA RULE: Every new sentence MUST contain an inline citation to an anchor (e.g., [A1]).\n"
                "4. Do not just append; weave the new data into the existing logic.\n"
                "5. Output the COMPLETE updated Markdown."
            )
        else:
            prompt = (
                f"You are a Senior Strategic Synthesiser building a high-fidelity intelligence report for: {query}\n\n"
                f"MANDATORY ANCHORS:\n{anchors_str}\n\n"
                "Report Requirements:\n"
                "1. Lead with a 'Strategic Executive Summary'.\n"
                "2. Use H2/H3 headings inspired by Business Intelligence frameworks.\n"
                "3. AGA RULE: Every sentence MUST contain an inline citation to an anchor (e.g., [A2]).\n"
                "4. PILLAR 1: Ensure sections address Economic impact and Psychological drivers.\n"
                "5. NEVER use conversational filler. Maintain an 'Air of Authority'."
            )
        
        return await self.provider.generate_text(
            prompt,
            system_prompt="You are a High-Precision Strategic Synthesiser. Output ONLY clean, authoritative Markdown.",
            max_tokens=2500
        )
