# Improvement Area 5: Primary Source Provenance & Fidelity

## The Objective
To move beyond "Web Snippets" and force Hexamind to extract high-fidelity proofs from complex primary sources (PDFs, SEC filings, Academic Papers, and Official Technical Documents).

## Why this is necessary
The Gemini report doesn't just link to "DemandSage"; it provides specific page-level concepts and references to **The American Customer Satisfaction Index (ACSI)** and **Forrester Research**. It feels broad because the "Harvest" is deep.

Hexamind currently relies on quick search snippets which can be superficial.

## Maximization Strategy: "Deep Harvesting"

### 1. Document Type Prioritization
Update the `Researcher` agent to prioritize file types in its search queries. For any complex research topic, it must specifically append `filetype:pdf` or `site:.gov` to at least 30% of its queries.

### 2. Multi-Hop Verification
Implement a "Source Triangulation" rule.
- If a statistic is found on a news site, the `Auditor` must flag it unless the `Researcher` can find a "Primary Document" (the original press release or whitepaper) that confirms the number.

### 3. Footnote Fidelity
The final report should move from "Simple Links" at the bottom to **Contextual Citations** (e.g., [ACSI, 2025]) that link directly to the high-authority source used for that specific paragraph.

## Expected Outcome
The "Aura of Truth." Reports that are legally and academically defensible because they are anchored in primary government/enterprise data rather than blog summaries.

---
**Status:** Elaborated (Draft 1)
