#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8011}"
PRIMARY_PROVIDER="${PRIMARY_PROVIDER:-groq}"
PROVIDER_CHAIN="${PROVIDER_CHAIN:-groq,gemini,openrouter}"
GROQ_FINAL_MODEL="${GROQ_FINAL_MODEL:-llama-3.3-70b-versatile}"
RETRIEVAL_TIMEOUT_SECONDS="${RETRIEVAL_TIMEOUT_SECONDS:-40}"
AGENT_TIMEOUT_SECONDS="${AGENT_TIMEOUT_SECONDS:-120}"
FINAL_TIMEOUT_SECONDS="${FINAL_TIMEOUT_SECONDS:-180}"

if [[ ! -x "$ROOT_DIR/.venv/bin/python" ]]; then
  echo "Missing virtualenv python at $ROOT_DIR/.venv/bin/python"
  echo "Create it first: python3 -m venv .venv && source .venv/bin/activate && pip install -r ai-service/requirements.txt"
  exit 1
fi

cd "$ROOT_DIR/ai-service"

# Load base environment layers if present.
set -a
[[ -f "$ROOT_DIR/.env" ]] && source "$ROOT_DIR/.env"
if [[ "${INCLUDE_LOCAL_OVERRIDES:-0}" == "1" ]] && [[ -f "$ROOT_DIR/.env.local" ]]; then
  source "$ROOT_DIR/.env.local"
fi
set +a

# Ensure cloud profiles do not inherit local model aliases.
unset HEXAMIND_MODEL_NAME || true
unset HEXAMIND_MODEL_NAME_LOCAL || true
unset HEXAMIND_LOCAL_MODEL_SMALL || true
unset HEXAMIND_LOCAL_MODEL_MEDIUM || true
unset HEXAMIND_LOCAL_MODEL_LARGE || true

# Cloud-first v1 demo profile (free-tier aware).
export HEXAMIND_FRAMEWORK_VERSION="v1"
export HEXAMIND_MODEL_PROVIDER="$PRIMARY_PROVIDER"
export HEXAMIND_PROVIDER_CHAIN="$PROVIDER_CHAIN"

# Keep execution predictable during refinement.
export HEXAMIND_PARALLEL_AGENTS="false"
export HEXAMIND_WEB_RESEARCH="1"
export HEXAMIND_REQUIRE_RESEARCH_SOURCES="1"
export HEXAMIND_HARD_FAIL_ON_NO_SOURCES="0"
export HEXAMIND_RESEARCH_PROVIDER="duckduckgo"
export HEXAMIND_RESEARCH_MAX_TERMS="4"
export HEXAMIND_RESEARCH_MAX_HITS_PER_TERM="4"
export HEXAMIND_RESEARCH_FETCH_CONCURRENCY="4"
export HEXAMIND_SEARCH_RETRY_ATTEMPTS="2"
export HEXAMIND_SEARCH_THROTTLE_SECONDS="0.10"
export HEXAMIND_SEARCH_JITTER_SECONDS="0.05"

# Gate and timeout profile tuned for cloud demo iteration.
export HEXAMIND_FINAL_MIN_LENGTH="1200"
export HEXAMIND_FINAL_MIN_CITATIONS="3"
export HEXAMIND_FINAL_AUTO_RETRY="1"
export HEXAMIND_RETRIEVAL_TIMEOUT_SECONDS="$RETRIEVAL_TIMEOUT_SECONDS"
export HEXAMIND_AGENT_TIMEOUT_SECONDS="$AGENT_TIMEOUT_SECONDS"
export HEXAMIND_FINAL_TIMEOUT_SECONDS="$FINAL_TIMEOUT_SECONDS"
export HEXAMIND_STREAM_MAX_CONCURRENT="2"

# Do not lock to a single provider when free tier is exhausted.
export HEXAMIND_STRICT_PROVIDER="false"

# Improve Groq cloud quality by defaulting synthesis/final stages to a larger model.
export HEXAMIND_MODEL_NAME_GROQ="$GROQ_FINAL_MODEL"

echo "Starting Hexamind v1 cloud-demo profile on ${HOST}:${PORT}"
echo "Primary provider: ${HEXAMIND_MODEL_PROVIDER}"
echo "Provider chain: ${HEXAMIND_PROVIDER_CHAIN}"

exec "$ROOT_DIR/.venv/bin/python" -m uvicorn main:app --host "$HOST" --port "$PORT"
