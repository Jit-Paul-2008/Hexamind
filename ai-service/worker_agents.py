import asyncio
import json
import logging
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

    async def run_analysis(self, topic: str, research_context: Any, context: Optional[str] = None, initial_draft: Optional[str] = None) -> Dict[str, Any]:
        """Execute the worker's inference as a JSON Editor."""
        logger.info(f"Worker [{self.role}] starting editorial review on topic: {topic}")
        
        # 1. Specialized Analysis (JSON Diff)
        json_diff_str = await self._analyze(topic, research_context.sources, context, initial_draft)
        
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

    async def _analyze(self, topic: str, sources: List[Any], context: Optional[str] = None, initial_draft: Optional[str] = None) -> str:
        """Perform specialized synthesis with JSON Diff output for ADD architecture."""
        source_text = "\n".join([f"- {s.title}: {s.excerpt}" for s in sources[:5]])
        
        system_prompts = {
            WorkerRole.RESEARCHER: "You are a Fact-Checking Specialist Editor.",
            WorkerRole.HISTORIAN: "You are a Historian Editor.",
            WorkerRole.AUDITOR: "You are a Quality Auditor Editor.",
            WorkerRole.ANALYST: "You are a Technical Analyst Editor."
        }
        
        prompt = (
            f"Review this draft research on: {topic}\n\n"
            f"Draft to Edit:\n{initial_draft or 'No draft provided.'}\n\n"
            f"New Evidence to integrate:\n{source_text}\n\n"
            "Task: Identify errors or missing facts in the draft based ONLY on the new evidence.\n"
            "Output ONLY a valid JSON array of corrections. DO NOT output paragraphs or conversational filler.\n"
            "Format: [{\"original_text_snippet\": \"text to replace\", \"replacement_text\": \"new detailed text\"}]\n"
            "If no changes are needed, return an empty array []."
        )
        
        return await self.provider.generate_text(
            prompt,
            system_prompt=system_prompts.get(self.role, "You are an Editor. Output ONLY JSON."),
            max_tokens=150
        )


class DraftingWorker:
    """Fast drafting worker for ADD architecture (0.5B model)."""
    
    def __init__(self, provider: Optional[InferenceProvider] = None):
        self.provider = provider if provider is not None else get_provider()

    async def draft(self, query: str, contexts: List[Any], existing_wiki: Optional[str] = None) -> str:
        """Generate a full Markdown draft from multiple research contexts, merging with existing wiki if provided."""
        combined_evidence = ""
        for ctx in contexts:
            combined_evidence += f"\n--- Evidence for {ctx.query} ---\n"
            combined_evidence += "\n".join([f"- {s.excerpt}" for s in ctx.sources[:5]])

        if existing_wiki:
            # EXPERT WIKI EDITOR MODE
            prompt = (
                f"You are an Expert Wiki Editor. You are given an existing Wiki Page and newly retrieved Web Evidence for the query: {query}\n\n"
                f"EXISTING WIKI CONTENT:\n{existing_wiki}\n\n"
                f"NEW WEB EVIDENCE:\n{combined_evidence}\n\n"
                "Your Task:\n"
                "1. Update, expand, and rewrite the existing Wiki Page seamlessly to incorporate new facts.\n"
                "2. DO NOT duplicate existing points; merge them logically.\n"
                "3. Maintain the structured 'LLM-Wiki' format (H2/H3 headings).\n"
                "4. Output the COMPLETE updated Markdown. DO NOT output partial snippets."
            )
        else:
            # FRESH DRAFT MODE
            prompt = (
                f"Write a high-fidelity encyclopedic research report in 'LLM-Wiki' format for the query: {query}\n\n"
                f"Use this dense factual record:\n{combined_evidence}\n\n"
                "Wiki Layout Requirements:\n"
                "1. Lead with a 'Definition & Context' section.\n"
                "2. Use H2 for major themes and H3 for sub-details.\n"
                "3. Be objective, factual, and extremely dense with data points.\n"
                "4. NEVER use conversational filler or personal pronouns.\n"
                "5. Ensure every section ends with a logical transition to the next theme."
            )
        
        return await self.provider.generate_text(
            prompt,
            system_prompt="You are a Professional Wiki Editor. Output ONLY clean Markdown.",
            max_tokens=2000
        )
