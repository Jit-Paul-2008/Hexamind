# Implementation Guide: Hexamind LLM-Wiki Architecture

> [!NOTE]
> This is a temporary blueprint file. Gemini Pro must strictly follow this guide to implement the Incremental Knowledge Wiki and must **DELETE THIS FILE** once execution and verification tests have passed.

## Objective
Transition Hexamind from generating isolated `demo_outputs/` files into generating a connected, persistent knowledge base stored inside a `data/wiki/` directory.

## Required Tasks

### Phase 1: Directory Setup & Title Normalization
We must convert standard research queries into valid Wikipedia-style filenames.

- **Modify `run_demo.py`**:
  - Automatically create the `data/wiki/` folder in the project root if it does not exist.
  - Implement a `titleize(query)` function (e.g., "Is Brain Drain Justified?" -> `Brain_Drain.md`). Use a simple regex or NLP token exclusion to strip words like "Is", "What", "How" and use Title Case joined by underscores.
  - Point the `output_path` away from `demo_outputs/` and into `data/wiki/{Title}.md`.

### Phase 2: Memory Retrieval (The Incremental Step)
The engine must check "what it already knows" before starting research.

- **Modify `ai-service/reasoning_graph.py`**:
  - In `AuroraGraph.run()`, before calling `drafter.draft(...)`, check if the destination file `data/wiki/{Title}.md` already exists.
  - If it exists, read the content into a variable called `existing_wiki_content`.
  - Pass `existing_wiki_content` to the `drafter.draft(query, contexts, existing_wiki=...)` method.

### Phase 3: The Drafter Update (Merging Logic)
The fast drafter must learn to merge new facts into old files.

- **Modify `ai-service/worker_agents.py`**:
  - Update `DraftingWorker.draft` to accept the optional `existing_wiki` string.
  - **Prompt Engineering**: 
    - If `existing_wiki` is None, use the standard prompt (write a fresh Wiki entry).
    - If `existing_wiki` is provided, prompt the 7B model clearly: *"You are an Expert Wiki Editor. You are given an existing Wiki Page and newly retrieved Web Evidence. Your task is to update, expand, and rewrite the existing Wiki Page seamlessly to incorporate the new facts. DO NOT duplicate existing points. output the full updated Markdown."*

### Phase 4: Output Overwrite
- **Modify `run_demo.py`**:
  - Ensure the final assembly overwrites the *same* `data/wiki/{Title}.md` file, acting as a true "Save/Update" mechanism, rather than creating timestamped duplicates.

## Verification Checklist
1. [ ] Run `"Impact of AI on Coding"`. Verify `data/wiki/Impact_of_AI_on_Coding.md` is created.
2. [ ] Re-run `"Impact of AI on Coding 2026 data"`. Verify the SAME file is updated with denser facts without losing the original structure.
3. [ ] If successful, automatically delete this implementation guide.
