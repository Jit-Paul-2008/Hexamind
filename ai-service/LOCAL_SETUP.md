# LOCAL DEVELOPMENT SETUP GUIDE
## Running Hexamind v1 with Ollama 70b Models

### Prerequisites
- Ollama installed and running on `http://127.0.0.1:11434`
- 70b model downloaded and loaded (e.g., `mistral:70b`, `llama2:70b`, etc.)
- Sufficient system RAM (70b model typically requires 40-50GB)

---

### Step 1: Verify Ollama is Running

```bash
# Check if Ollama is accessible
curl http://127.0.0.1:11434/v1/models

# Expected output: List of available models in OpenAI-compatible format
# Example:
# {
#   "object": "list",
#   "data": [
#     {"id": "mistral:70b", "object": "model", ...},
#     ...
#   ]
# }
```

If this fails:
- Start Ollama: `ollama serve` (in a separate terminal)
- Verify model is loaded: `ollama list`
- If 70b model not loaded: `ollama pull mistral:70b` (or your preferred 70b model)

---

### Step 2: Configure Local Model Name

Edit `.env.local` and update the model names to match your Ollama setup:

```env
HEXAMIND_LOCAL_MODEL_SMALL=mistral:70b    # or whatever name Ollama shows
HEXAMIND_LOCAL_MODEL_MEDIUM=mistral:70b
HEXAMIND_LOCAL_MODEL_LARGE=mistral:70b
```

To find your exact model names, run:
```bash
ollama list
```

Example output:
```
NAME              ID              SIZE    MODIFIED
mistral:70b       1234567890ab    40GB    2024-01-15 12:00:00
```

Use `mistral:70b` as shown in the NAME column.

---

### Step 3: Use Local Configuration

**Option A: Layer the env files in your shell (safest)**
```bash
cd /home/Jit-Paul-2008/Desktop/Hexamind/ai-service
set -a
source .env
source .env.local
set +a
```

**Option B: Keep separate and source them in backend startup**
```bash
# In your backend startup script, load the base env first, then the local overrides:
source .env
source .env.local
# then start: python main.py
```

---

### Step 4: Restart Backend

```bash
# From the Hexamind root directory
cd /home/Jit-Paul-2008/Desktop/Hexamind

# Stop current backend
docker-compose down  # or kill any running ai-service process

# Start with local config after exporting both env layers
docker-compose -f docker-compose.override.yml up ai-service
# Or if running locally without Docker:
cd ai-service && python main.py
```

Verify startup in logs:
```
✓ LocalPipelineModelProvider initialized
✓ Connecting to http://127.0.0.1:11434/v1
✓ Primary provider: local (mistral:70b)
```

---

### Step 5: Test v1 Pipeline with Local Models

Make a test request to the same "South Korea population decline" query that was used in cloud testing:

```bash
curl -X POST http://127.0.0.1:8000/research \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Why is the population of South Korea declining so rapidly?",
    "reportLength": "moderate",
    "reportType": "comparative",
    "maxDepthLabel": "high"
  }'
```

Expected behavior with local models + hard gates:
- **First attempt:** Local model generates initial answer (~1200+ chars with proper citations)
- **Validation:** Hard gates check:
  - ✓ Length ≥ 1200 chars
  - ✓ Citations ≥ 3
  - ✓ All 9 sections present (Methods, Results, Discussion, References, etc.)
- **Post-process:** Deterministic citation injector fills any missing citations
- **Result:** Academic-quality report with full citations (compare to cloud baseline from earlier test)

---

### Step 6: Monitor Performance

With local models, you'll see:
- **Latency:** 5-15 min per report (depends on system, 70b model speed)
- **Cost:** $0
- **Rate limits:** None (unlimited calls)
- **Design benefit:** Deterministic + reproducible (same model always produces similar outputs)

Compare your local report to the cloud baseline (2764 chars @ 48.7 quality) documented in SAMPLE_REPORT_WITH_HARD_GATES.md.

---

### Step 7: Refine v1 Parameters

Once local testing confirms hard gates work, you can iterate on:
- **Compression rate** (HEXAMIND_COMPRESSION_RATE) – try 0.4, 0.5, 0.6
- **Depth label** (HEXAMIND_RESEARCH_DEPTH) – try "moderate", "high", "exhaustive"
- **Search passes** (HEXAMIND_SEARCH_PASSES) – try 2, 3, 4
- **Token budget** (HEXAMIND_TOKEN_BUDGET) – try 40k, 50k, 60k

Each parameter change requires backend restart.

---

### Troubleshooting

**Problem:** `Connection refused: http://127.0.0.1:11434`
- **Solution:** Start Ollama: `ollama serve`

**Problem:** `Model not found: mistral:70b`
- **Solution:** Load model: `ollama pull mistral:70b`

**Problem:** Out of memory errors
- **Solution:** Your system may not have enough RAM for 70b. Try a smaller model:
  ```bash
  ollama pull mistral:7b    # Much faster, lower quality
  # Then update .env.local:
  HEXAMIND_LOCAL_MODEL_SMALL=mistral:7b
  HEXAMIND_LOCAL_MODEL_MEDIUM=mistral:7b
  HEXAMIND_LOCAL_MODEL_LARGE=mistral:7b
  ```

**Problem:** Hard gates failing (response too short)
- **Solution:** Local model may be underfitting. Try:
  - Increase HEXAMIND_TOKEN_BUDGET to 60000
  - Set HEXAMIND_COMPRESSION_RATE=0.3 (less aggressive)
  - Set HEXAMIND_RESEARCH_DEPTH=exhaustive

**Problem:** Backend not picking up local provider
- **Solution:** Verify:
  - `.env` or `.env.local` has `HEXAMIND_MODEL_PROVIDER=local`
  - Backend restarted after config change
  - Check logs for "LocalPipelineModelProvider initialized"

---

### Next Steps After Local Testing

Once you've confirmed v1 with local models:
1. Document any parameter improvements you discover
2. Deploy improved v1 settings to cloud providers for production
3. Consider: Does multi-agent v2 still benefit performance? (Now you have a working v1 as baseline)
4. Measure v1 vs. v2 on same queries with hard gates enabled on both

---

### Configuration Reference

See `.env.local` in this directory for all environment variables. Key settings for v1 refinement:
- Hard gates (HEXAMIND_FINAL_*) enforce research quality
- Compression controls evidence preservation
- Token budget controls depth vs. latency
- Provider chain allows graceful fallback to deterministic pipeline

All changes testable immediately with local models (no rate limits, zero cost).
