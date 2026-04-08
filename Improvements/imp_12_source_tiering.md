# Improvement Area 12: Evidence Quality Scoring (Source Tiering)

## The Objective
To move Hexamind away from "Democratic Evidence Retrieval" (where a blog post has the same weight as a peer-reviewed study) and into **"Institutional Evidence Hierarchies."**

## Why this is necessary
Gemini consistently prioritizes:
- **Tier 1:** Federal/Regulatory filings (SEC, DOJ, FTC).
- **Tier 2:** Institutional Research (Forrester, ACSI, Gartner, Jamf).
- **Tier 3:** High-Authority News (CNET, 9to5Mac, Bloomberg).
- **Tier 4:** Community/Sentiment (Reddit, YouTube, Forums).

Hexamind currently allows whatever search result comes first to define the "Anchors."

## Maximization Strategy: "The Authority Filter"

### 1. The Source Scorer
Implement a "Source Authority Map" in `research.py` or a dedicated agent.
- `.gov`, `.edu`, `sec.gov`, `forrester.com` = **Scored 10/10**.
- Major news outlets = **Scored 7/10**.
- Individual blogs/forums = **Scored 3/10**.

### 2. Anchor Competition
When extracting "Atomic Grounding Anchors," the `AnchorWorker` must prioritize the highest-scored sources. If a 10/10 source contradicts a 3/10 source, the 10/10 source replaces it automatically.

### 3. Proof-by-Provenance
The Synthesiser must prefix sections with their "Authority Weight":
- *e.g.,* "Based on Institutional Data (Forrester/ACSI): Apple's retention stands at 92%..."

## Expected Outcome
Reports that are "Resilient to Hallucination." By anchoring the core claims in Tier-1 institutional data, the overall credibility of Hexamind's research increases by orders of magnitude.

---
**Status:** Elaborated (Draft 1)
