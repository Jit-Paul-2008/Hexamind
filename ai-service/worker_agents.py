import asyncio
import json
import logging
import re
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

    async def gather_evidence(self, topic: str) -> Any:
        """Prefetch research context over the network (run in parallel)."""
        search_query = await self._generate_search_query(topic)
        return await self.researcher.research(search_query)

    async def run_analysis(self, topic: str, research_context: Any, context: Optional[str] = None, initial_draft: Optional[str] = None, anchors: List[Dict[str, str]] = None) -> Dict[str, Any]:
        """Execute the worker's inference as a JSON Editor."""
        logger.info(f"Worker [{self.role}] starting editorial review on topic: {topic}")
        
        # 1. Specialized Analysis (JSON Diff)
        json_diff_str = await self._analyze(topic, research_context.sources, context, initial_draft, anchors)
        
        # 2. Parse JSON safely
        try:
            # Strip any markdown code blocks if the model included them
            clean_json = re.sub(r"```json\s*|\s*```", "", json_diff_str.strip())
            diffs = json.loads(clean_json)
        except Exception:
            logger.error(f"Worker [{self.role}] failed to produce valid JSON: {json_diff_str}")
            diffs = []
            
        return {
            "role": self.role,
            "topic": topic,
            "diffs": diffs,
            "sources": [s.url for s in research_context.sources[:3]]
        }

    async def _generate_search_query(self, topic: str) -> str:
        """Tailor the search query based on the worker's role."""
        normalized_topic = topic.lower()
        # Only focus on IIT if the user explicitly mentioned it
        iit_keywords = ["iit", "indian institute", "jee", "iitian"]
        is_iit_specific = any(token in normalized_topic for token in iit_keywords)

        prompts = {
            WorkerRole.RESEARCHER: f"Find current facts, statistical paradoxes, outcomes, and recent case studies about {topic}",
            WorkerRole.HISTORIAN: f"Find historical evolution, policy shifts, and developmental timeline for {topic}",
            WorkerRole.AUDITOR: f"Find critical assessments, failures, social downsides, and dissenting views on {topic}",
            WorkerRole.ANALYST: f"Find implementation strategies, future projections, and mechanistic outcomes for {topic}"
        }

        query = prompts.get(self.role, topic)
        if is_iit_specific:
            query += " IIT India placement student outcomes case study"
        return query

    async def _analyze(self, topic: str, sources: List[Any], context: Optional[str] = None, initial_draft: Optional[str] = None, anchors: List[Dict[str, str]] = None) -> str:
        """Perform specialized synthesis with JSON Diff output for ADD architecture."""
        source_text = "\n".join([f"- {s.title}: {s.excerpt}" for s in sources[:5]])
        anchors_str = "\n".join([f"[{a['id']}] {a['fact']}" for a in (anchors or [])])
        
        system_prompts = {
            WorkerRole.RESEARCHER: "You are a Fact-Checking Specialist Editor.",
            WorkerRole.HISTORIAN: "You are a Historian Editor.",
            WorkerRole.AUDITOR: "You are a Boolean Verification Auditor. Identify un-anchored or contradictory claims and delete them.",
            WorkerRole.ANALYST: "You are a Technical Analyst Editor."
        }
        
        if self.role == WorkerRole.AUDITOR:
            prompt = (
                f"Review this draft research on: {topic}\n\n"
                f"Draft to Edit:\n{initial_draft or 'No draft provided.'}\n\n"
                f"Provided Anchors (Truth Grounding):\n{anchors_str}\n\n"
                "Task: Find any sentence in the draft that makes a factual claim NOT present in the Provided Anchors, or contradicts them.\n"
                "Output a JSON array of corrections to DELETE those unverified claims.\n"
                "Format: [{\"original_text_snippet\": \"unverified claim text...\", \"replacement_text\": \"\"}]\n"
                "If everything is perfectly grounded, return []."
            )
        else:
            prompt = (
                f"Review this draft research on: {topic}\n\n"
                f"Draft to Edit:\n{initial_draft or 'No draft provided.'}\n\n"
                f"New Evidence to integrate:\n{source_text}\n\n"
                "Task: Identify errors or missing facts in the draft based ONLY on the new evidence.\n"
                "Output ONLY a valid JSON array of corrections.\n"
                "Format: [{\"original_text_snippet\": \"text to replace\", \"replacement_text\": \"new detailed text\"}]\n"
                "If no changes are needed, return an empty array []."
            )
        
        return await self.provider.generate_text(
            prompt,
            system_prompt=system_prompts.get(self.role, "You are an Editor. Output ONLY JSON."),
            max_tokens=150
        )


class AnchorWorker:
    """Extracts Atomic Grounding Anchors from raw context."""
    def __init__(self, provider: Optional[InferenceProvider] = None):
        self.provider = provider if provider is not None else get_provider()

    async def extract(self, topic: str, contexts: List[Any], existing_wiki: Optional[str] = None) -> List[Dict[str, str]]:
        combined_evidence = ""
        for ctx in contexts:
            combined_evidence += f"\n--- Evidence for {ctx.query} ---\n"
            combined_evidence += "\n".join([f"- {s.excerpt}" for s in ctx.sources[:5]])

        if existing_wiki:
            combined_evidence = f"EXISTING WIKI CONTINUITY:\n{existing_wiki}\n\nNEW EVIDENCE:\n{combined_evidence}"

        prompt = (
            f"Extract exactly 8-10 Atomic Grounding Anchors (hard facts, numbers, dates, critical quotes) from the following evidence regarding: {topic}\n\n"
            f"{combined_evidence}\n\n"
            "Requirements:\n"
            "1. Output ONLY a valid JSON array.\n"
            "2. Format: [{\"id\": \"A1\", \"fact\": \"<the exact stat/fact>\"}]\n"
            "3. DO NOT output conversational filler."
        )

        try:
            result_str = await self.provider.generate_text(
                prompt,
                system_prompt="You are an Anchor Extractor. Output ONLY JSON.",
                max_tokens=500
            )
            clean_json = re.sub(r"```json\s*|\s*```", "", result_str.strip())
            return json.loads(clean_json)
        except Exception as e:
            logger.error(f"Anchor extraction failed: {e}")
            return []


class DraftingWorker:
    """Fast drafting worker for ADD architecture (0.5B model)."""
    
    def __init__(self, provider: Optional[InferenceProvider] = None):
        self.provider = provider if provider is not None else get_provider()

    async def draft(self, query: str, contexts: List[Any], existing_wiki: Optional[str] = None, anchors: List[Dict[str, str]] = None) -> str:
        """Generate a full Markdown draft, stringently constrained by Anchors."""
        anchors_str = "\n".join([f"[{a['id']}] {a['fact']}" for a in (anchors or [])])

        if existing_wiki:
            prompt = (
                f"You are a Deterministic Fact Compiler. You are given an existing Wiki Page and a new set of Atomic Grounding Anchors for the query: {query}\n\n"
                f"EXISTING WIKI CONTENT:\n{existing_wiki}\n\n"
                f"MANDATORY NEW ANCHORS TO INTEGRATE:\n{anchors_str}\n\n"
                "Your Task:\n"
                "1. Update the existing Wiki Page to incorporate the new Anchor facts.\n"
                "2. AGA RULE: Every new sentence you write MUST contain an inline citation to an anchor (e.g., 'Growth was 5% [A1]').\n"
                "3. Do not formulate unsupported claims.\n"
                "4. Output the COMPLETE updated Markdown."
            )
        else:
            prompt = (
                f"You are a Deterministic Fact Compiler building a Wiki page for the query: {query}\n\n"
                f"MANDATORY ANCHORS:\n{anchors_str}\n\n"
                "Wiki Layout Requirements:\n"
                "1. Lead with 'Definition & Context'.\n"
                "2. Use H2/H3 headings.\n"
                "3. AGA RULE: Every sentence MUST contain an inline citation to an anchor (e.g., 'The population is 1.4B [A2]').\n"
                "4. If you have no anchors for a section, DO NOT WRITE IT.\n"
                "5. NEVER use conversational filler."
            )
        
        return await self.provider.generate_text(
            prompt,
            system_prompt="You are a Deterministic Fact Compiler. You only assemble given anchors. Output ONLY clean Markdown.",
            max_tokens=2000
        )
