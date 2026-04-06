# ARIA Framework Options — Speed vs Quality Tradeoffs

## Context
- CPU-only inference (no GPU)
- Models: mistral:7b (agents), llama3.1:70b (final)
- Current V1: ~2-3 min, single synthesiser
- Current V2: ~25 min, 5 sequential agents
- Goal: Reduce time, improve quality, unbiased output

---

## Framework A: "Two-Brain" (Recommended for CPU)

**Agents:** 2 (Researcher + Critic)
**Estimated time:** 4-6 minutes

**Flow:**
1. SearXNG retrieval (30s)
2. **Researcher agent** — writes a structured report from sources (mistral:7b, ~2 min)
3. **Critic agent** — reviews the report for bias, gaps, unsupported claims (mistral:7b, ~2 min)
4. **Final merge** — combines report + critic feedback into final output (llama3.1:70b or deterministic merge)

**Why it works:**
- Only 2 inference calls instead of 5
- Critic ensures bias is flagged and corrected
- Researcher gets full research context, Critic gets the draft + sources
- Final output includes both the report and a bias/quality sidebar

**Technical report:** Generated from Critic's findings (source quality, bias flags, evidence gaps)
**Real report:** Researcher's structured analysis with Critic's corrections applied

---

## Framework B: "Debate Pair"

**Agents:** 2 (Pro + Con) + deterministic merge
**Estimated time:** 5-7 minutes

**Flow:**
1. SearXNG retrieval (30s)
2. **Pro agent** — builds the strongest case FOR the topic (mistral:7b, ~2 min)
3. **Con agent** — builds the strongest case AGAINST the topic (mistral:7b, ~2 min)
4. **Deterministic merge** — no LLM call, structured template combines both sides (0s)

**Why it works:**
- Forces balanced perspective by design
- No bias possible — both sides are always represented
- Deterministic merge is instant (no LLM needed for final step)
- User sees both perspectives clearly

**Technical report:** Source attribution from both sides, overlap analysis
**Real report:** "Arguments For" + "Arguments Against" + "Balanced Assessment"

---

## Framework C: "Research-then-Verify"

**Agents:** 2 (Drafter + Verifier)
**Estimated time:** 5-8 minutes

**Flow:**
1. SearXNG retrieval (30s)
2. **Drafter agent** — writes full structured report (mistral:7b, ~2 min)
3. **Verifier agent** — fact-checks claims against sources, flags unsupported statements (mistral:7b, ~3 min)
4. **Final synthesis** — Drafter output with Verifier annotations (deterministic or llama3.1:70b)

**Why it works:**
- Verifier acts as quality gate
- Claims are explicitly checked against sources
- Output includes confidence levels per claim
- Reduces hallucination risk

**Technical report:** Verification matrix (claim → source → confidence)
**Real report:** Research findings with verification badges

---

## Framework D: "Parallel Perspectives" (Needs GPU)

**Agents:** 4 parallel + 1 sequential merge
**Estimated time:** 3-4 min with GPU, 20+ min on CPU

**Flow:**
1. SearXNG retrieval (30s)
2. **Parallel:** Advocate, Skeptic, Oracle, Verifier (all at once, ~2 min with GPU)
3. **Sequential:** Synthesiser merges all outputs (llama3.1:70b, ~1 min with GPU)

**Why it won't work now:** CPU can only run one model at a time. Parallel = sequential on CPU.

---

## Framework E: "Smart Single-Pass"

**Agents:** 1 (Enhanced Synthesiser)
**Estimated time:** 2-4 minutes

**Flow:**
1. SearXNG retrieval (30s)
2. **Enhanced Synthesiser** — single agent with a carefully designed prompt that forces:
   - Balanced analysis (pro/con sections required)
   - Source citations (must reference specific sources)
   - Risk assessment (must include limitations)
   - Confidence scoring (must rate evidence strength)
3. **Deterministic post-processing** — extracts technical metrics from output (0s)

**Why it works:**
- Fastest possible — single LLM call
- Prompt engineering does the heavy lifting
- Structured output template forces balanced, unbiased reporting
- No quality loss if prompt is well-designed

**Risk:** Single point of failure — if the model hallucinates, no second agent catches it.

**Technical report:** Extracted programmatically from structured output
**Real report:** The structured analysis itself

---

## Framework F: "Retrieval-Heavy, Inference-Light"

**Agents:** 1 (Narrator)
**Estimated time:** 2-3 minutes

**Flow:**
1. **Deep SearXNG retrieval** — 3 rounds of search with query expansion (60s)
2. **Source ranking + extraction** — deterministic scoring of sources (5s)
3. **Narrator agent** — weaves top sources into a coherent narrative (mistral:7b, ~1.5 min)
4. **Deterministic technical report** — generated from retrieval metadata (0s)

**Why it works:**
- Puts effort into retrieval (free, fast) instead of inference (slow, expensive)
- Better sources = better output even with a single agent
- Multiple search rounds catch different angles of the topic
- Technical report is entirely deterministic (source stats, domain diversity, freshness)

**Risk:** Depends heavily on SearXNG returning good results.

---

## Comparison Matrix

| Framework | Agents | Est. Time | Bias Control | Source Quality | Complexity |
|-----------|--------|-----------|--------------|----------------|------------|
| A: Two-Brain | 2 | 4-6 min | Good (Critic) | Good | Medium |
| B: Debate Pair | 2 | 5-7 min | Excellent (by design) | Good | Medium |
| C: Research-Verify | 2 | 5-8 min | Good (Verifier) | Excellent | Medium |
| D: Parallel (GPU) | 5 | 3-4 min* | Excellent | Excellent | High |
| E: Smart Single | 1 | 2-4 min | Moderate (prompt) | Moderate | Low |
| F: Retrieval-Heavy | 1 | 2-3 min | Moderate | Excellent | Low |

*GPU required

## Recommendation for Current Hardware (CPU-only)

**Framework A (Two-Brain)** or **Framework B (Debate Pair)** offer the best balance:
- 2 agents = ~5 min total (acceptable wait)
- Built-in bias control
- Good source utilization
- Clear separation between technical and real reports

**Framework F (Retrieval-Heavy)** is best if speed is the top priority — fastest possible with decent quality.
