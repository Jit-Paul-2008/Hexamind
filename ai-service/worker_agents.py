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

    async def _generate_search_query(self, topic: str) -> str:
        """Tailor the search query based on the worker's role."""
        normalized_topic = topic.lower()
        # Only focus on IIT if the user explicitly mentioned it
        iit_keywords = ["iit", "indian institute", "jee", "iitian"]
        is_iit_specific = any(token in normalized_topic for token in iit_keywords)

        prompts = {
            WorkerRole.RESEARCHER: f"Find current facts, statistical paradoxes, outcomes, and Reddit/forum sentiment regarding {topic}",
            WorkerRole.HISTORIAN: f"Find historical evolution, policy shifts, and developmental timeline for {topic}",
            WorkerRole.AUDITOR: f"Find critical assessments, user complaints, social downsides, and dissenting views on {topic}",
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
                f"Review this draft research on: {topic}\n\n"
                f"Draft to Edit:\n{initial_draft or 'No draft provided.'}\n\n"
                f"Provided Anchors (Truth Grounding):\n{anchors_str}\n\n"
                "Task: Find any sentence in the draft that makes a factual claim NOT present in the Provided Anchors, or contradicts them.\n"
                "Output as JSON object with 'diffs' array and 'rationale' string summary.\n"
                "Format: {\"diffs\": [{\"original_text_snippet\": \"...\", \"replacement_text\": \"\"}], \"rationale\": \"summary of grounding failures\"}\n"
                "If everything is perfectly grounded, return {\"diffs\": [], \"rationale\": \"All claims verified against anchors.\"}."
            )
        else:
            prompt = (
                f"Review this draft research on: {topic}\n\n"
                f"Draft to Edit:\n{initial_draft or 'No draft provided.'}\n\n"
                f"New Evidence to integrate:\n{source_text}\n\n"
                "Task: Identify errors or missing facts in the draft based ONLY on the new evidence.\n"
                "For ANALYSTS: You MUST also identify a relevant Mental Model (e.g. Sunk Cost, Network Effect) to explain the data.\n"
                "Output as JSON object with 'diffs' array and 'rationale' string summary.\n"
                "Format: {\"diffs\": [{\"original_text_snippet\": \"...\", \"replacement_text\": \"...\"}], \"rationale\": \"McKinsey-style summary of economic/behavioral impact\"}\n"
                "If no changes are needed, return empty diffs but provide the rationale."
            )
        
        return await self.provider.generate_text(
            prompt,
            system_prompt=system_prompts.get(self.role, "You are an Expert Strategist. Output ONLY JSON."),
            max_tokens=300 # Increased for rationale
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
