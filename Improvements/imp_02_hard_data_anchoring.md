# Improvement Area 2: Hard-Data Anchoring & Unit Statistics

## The Objective
Eliminate qualitative "fuzziness" (e.g., "rapid growth", "mostly successful") from Hexamind reports by enforcing a strict requirement for scalar data and comparative percentages.

## Why this is necessary
The Gemini Apple report is littered with precise data points:
- "232.1 million iPhones sold in 2024."
- "6.76% year-over-year increase."
- "Retention rate of 92% vs Samsung's 77%."

Hexamind currently delivers excellent prose, but often lacks the "Numerical Authority" that makes a report feel definitive.

## Maximization Strategy: "Scalar Extraction"

### 1. Mandatory Scalar Pass
Update the `Researcher` agent's retrieval instructions. Instead of generic "find info about X," it must use a sub-query strategy:
> "Find [Topic X] statistics, unit sales, market share percentages, and annual growth rates."

### 2. The "Fuzzy Logic" Auditor
The `Auditor` agent will be given a new "Unit Check" constraint. Any paragraph containing qualitative adjectives (large, small, fast, slow) without a corresponding numerical anchor will be flagged for "Numerical Grounding."

### 3. Automatic Table Synthesis
The `Analyst` agent will be prompted to format any competitive data into Markdown tables (as seen in Table 1 & 2 of the Gemini report) to allow for instant visual comparison. 

## Expected Outcome
Reports that transition from "Essay Style" to "Investor Grade" analysis, providing the user with actual metrics they can use for financial or strategic planning.

---
**Status:** Elaborated (Draft 1)
