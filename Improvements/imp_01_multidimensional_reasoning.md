# Improvement Area 1: Multidimensional Reasoning Loops

## The Objective
To transition Hexamind from a "Data Aggregator" to a "Strategic Analyst" by forcing the model to synthesize every fact through three distinct filters: **Economic Impact**, **Psychological Driver**, and **Structural Risk**.

## Why this is necessary
In the `gemini_reports` analysis of Apple, the AI didn't just say "People like iPhones." It explained:
1. **Psychology:** Maslow's Hierarchy (Self-Actualization via Brand).
2. **Economics:** Veblen Goods (Higher price = Higher demand).
3. **Sociology:** The "Green Bubble" social stigma in Gen Z.

Hexamind currently treats these as separate agent tasks. We need to "Loop" them.

## Proposed Strategy: The "Reasoning Cube"

Instead of linear agent execution, we will modify the **Synthesiser** and **Analyst** nodes to use a "Triangulation Prompting" technique.

### 1. The Expert Synthesis Filter
Every key finding in the final report must be "Triangulated" using this formula:
> **[Fact]** + **[Economic Rationale]** + **[Human Driver]** = **[Strategic Insight]**

### 2. Prompt Injection (Implementation)
We will update `ai-service/agents.py` (or the dynamic prompt loader) to include the following directive for the `synthesiser`:

```markdown
Mandatory Structural Check:
For every major conclusion, you MUST address:
- THE TCO (Total Cost of Ownership/Action): What is the long-term price of this trend?
- THE PSYCHOLOGICAL ANCHOR: What human desire (fear of missing out, status signaling, safety) is driving this?
- THE NETWORK EFFECT: How does this trend scale as more people join?
```

## Step-by-Step Implementation Plan
1. **Expert Context Update:** Inject the "Behavioral Economics Library" into the system prompt of the `Analyst`.
2. **Double-Pass Reasoning:** The `Synthesiser` will now perform two passes.
   - *Pass 1:* Narrative Draft.
   - *Pass 2:* "Dimension Injection" - looking for missing economic/psychological anchors.
3. **Verification:** The `Auditor` will be updated to flag any "Flat Reports" (reports that only contain facts without multidimensional synthesis).

## Expected Outcome
Reports that read like high-level strategy documents (McKinsey/Gemini level) rather than well-written Wikipedia summaries.

---
**Status:** Elaborated (Draft 1)
**Next:** I will wait for user feedback on this specific area before proceeding to Area 2 or implementing the code.
