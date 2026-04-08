# Improvement Area 10: Expert Persona Lexicons (Lexical Infusion)

## The Objective
To move Hexamind beyond a single "AI Voice" and into **"The Echo of Expertise."** Each agent will be assigned a specific domain lexicon (e.g., McKinsey Consultant, Tech Engineer, Behavioral Sociologist) to ensure the report uses professional, context-appropriate terminology.

## Why this is necessary
Gemini's report feels "Premium" because it uses high-level professional language:
- "Multifaceted strategy"
- "Veblen goods"
- "Proprietary protocols"
- "Vertical integration"

Hexamind's default voice is often "Neutral AI." We need to infuse it with **Role-Specific Lexicons**.

## Maximization Strategy: "The Lexical Overlay"

### 1. Persona-Specific Toolkits
Update `ai-service/agents.py` with expanded system prompts for each role.
- **Synthesiser:** "You are a Senior Partner at a Tier-1 Strategy Consulting firm (McKinsey/BCG). Use concise, direct, and multi-pillared executive language."
- **Analyst:** "You are a Behavioral Economist. Frame all user habits through the lens of cognitive biases and choice architecture."
- **Auditor:** "You are a Structural Risk Officer. Use the language of compliance, antitrust, and systemic failure."

### 2. Forbidden Phrases & Target Keywords
Inject "Target Keywords" for each agent to force usage of high-value concepts.
- *Synthesiser Keywords:* Ecosystem, Synergy, Lock-in, TCO, ROI.
- *Auditor Keywords:* Antitrust, Monopoly, Fragility, Regulatory Headwind, Sideloading.

### 3. Sentence Structure Constraints
The `Synthesiser` will be instructed to use "Analytical Lead-ins" like *"Perhaps the most formidable driver of..."* or *"The financial impact is profound..."* (directly inspired by Gemini's phrasing).

## Expected Outcome
The "Tone of Authority." The user will feel they are reading a report written by a panel of high-cost human experts, not a generic LLM.

---
**Status:** Elaborated (Draft 1)
