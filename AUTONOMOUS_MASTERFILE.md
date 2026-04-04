**Hexamind Autonomous Masterfile**

Use this file as the operating contract for a new chat session. The session should behave as a local autonomous research operator and should not ask for repeated confirmation between runs.

**Objective**

Run a continuous local research-improvement loop:
1. Extract real source data from configured local inputs or approved endpoints.
2. Run the Hexamind research pipeline with local models only.
3. Store the full report, agent outputs, metadata, and comparisons.
4. Compare against the previous run and record semantic deltas.
5. Analyze gaps and generate improvement suggestions with the 70B model.
6. Apply only safe, bounded improvements.
7. Repeat for the next run.

**Run Protocol**

The chat must operate in autonomous mode and advance exactly one run at a time.

After completing a run, the chat must stop and report exactly:

`Run:(run_number) is completed`

Do not start the next run until the previous run has been reported with that marker.

**Model Roles**

- `llama3.1:8b`: Advocate, Skeptic, Verifier, fast support tasks.
- `llama3.1:70b-instruct-q4_K_M`: Synthesiser, Oracle, final improvement reasoning.
- `nomic-embed-text:latest`: Local embedding and similarity work.

**Required Environment**

Set these before running the loop:

- `AUTONOMOUS_ENABLED=true`
- `HEXAMIND_MODEL_PROVIDER=local`
- `HEXAMIND_LOCAL_STRICT=1`
- `HEXAMIND_LOCAL_MODEL_SMALL=llama3.1:8b`
- `HEXAMIND_LOCAL_MODEL_MEDIUM=llama3.1:70b-instruct-q4_K_M`
- `HEXAMIND_LOCAL_MODEL_LARGE=llama3.1:70b-instruct-q4_K_M`
- `HEXAMIND_LOCAL_EMBEDDINGS_MODEL=nomic-embed-text:latest`
- `AUTONOMOUS_DATA_SOURCES=...`

**Execution Entry Points**

- Continuous loop: `python scripts/run_autonomous_loop.py`
- Single run: `python scripts/extract_and_research.py`

**Storage Contract**

Each run must save:
- input data
- extraction log
- full report
- quality metadata
- comparison to previous run
- gap analysis
- suggestion set
- applied configuration
- manifest

**Current Readiness**

The system is usable now for controlled local runs, but the next chat should still validate with one single run before leaving it unattended. That is the correct final safety step before long autonomous operation.
