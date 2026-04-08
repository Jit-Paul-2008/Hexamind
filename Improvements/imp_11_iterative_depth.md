# Improvement Area 11: Iterative Depth Scaling (Recursive Research)

## The Objective
To implement a "Self-Correcting Search Loop." If an initial research pass yields low-confidence or high-conflict data, Hexamind will automatically spawn a secondary, targeted "Deep Dive" into that specific sub-topic.

## Why this is necessary
Gemini's report includes logs like "I've noted that their success appears rooted in... I am beginning to explore... I will now focus on..." This indicates a **Multi-Stage Inquiry.**

Hexamind currently performs one "Broad Harvest" and then synthesizes. If the harvest misses a crucial detail, the final report is limited by that first-pass luck.

## Maximization Strategy: "The Multi-Stage Hunt"

### 1. Confidence Thresholding
The `Synthesiser` or `Auditor` will be given a "Confidence Score" metric. If a specific section (e.g., "Financial Impact") has less than 2 high-quality anchors, it triggers a **"Depth-Scale Event."**

### 2. Recursive Querying
Instead of stopping, the `Researcher` is re-activated with a **"High-Resolution Query"** specifically for the low-confidence area.
- *Example:* "Find specific Apple vs Samsung market share tables for the JAPANESE market in 2025." (Turning a generic failure into a targeted success).

### 3. Log Visibility
Show the user the "Thinking Evolution."
- "Stage 1: Broad Research complete."
- "Stage 2: Detected gap in Japan regional data. Spawning deep-dive..."

## Expected Outcome
The "Persistence of Logic." Hexamind will no longer "give up" on hard-to-find data; it will narrow its focus and hunt until it finds the "Gold Standard" evidence required to match Gemini's level.

---
**Status:** Elaborated (Draft 1)
