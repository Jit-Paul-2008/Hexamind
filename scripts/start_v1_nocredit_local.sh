#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8011}"
LOCAL_MODEL="${LOCAL_MODEL:-llama3.1:70b-instruct-q4_K_M}"
LOCAL_BASE_URL="${LOCAL_BASE_URL:-http://127.0.0.1:11434/v1}"

if [[ ! -x "$ROOT_DIR/.venv/bin/python" ]]; then
  echo "Missing virtualenv python at $ROOT_DIR/.venv/bin/python"
  echo "Create it first: python3 -m venv .venv && source .venv/bin/activate && pip install -r ai-service/requirements.txt"
  exit 1
fi

cd "$ROOT_DIR/ai-service"

# Load project env, then hard override into no-credit local mode.
set -a
[[ -f "$ROOT_DIR/.env" ]] && source "$ROOT_DIR/.env"
[[ -f "$ROOT_DIR/.env.local" ]] && source "$ROOT_DIR/.env.local"
set +a

# Hard no-credit guardrails: disable all cloud keys and pools.
export GOOGLE_API_KEY=""
export GOOGLE_API_KEYS=""
export GROQ_API_KEY=""
export GROQ_API_KEYS=""
export OPENROUTER_API_KEY=""
export OPENROUTER_API_KEYS=""

# v1 local-only profile.
export HEXAMIND_FRAMEWORK_VERSION="v1"
export HEXAMIND_MODEL_PROVIDER="local"
export HEXAMIND_PROVIDER_CHAIN="local"
export HEXAMIND_STRICT_PROVIDER="true"
export HEXAMIND_LOCAL_STRICT="1"

# Local model mapping (single model for all roles for determinism).
export HEXAMIND_LOCAL_BASE_URL="$LOCAL_BASE_URL"
export HEXAMIND_MODEL_NAME="$LOCAL_MODEL"
export HEXAMIND_LOCAL_MODEL_SMALL="$LOCAL_MODEL"
export HEXAMIND_LOCAL_MODEL_MEDIUM="$LOCAL_MODEL"
export HEXAMIND_LOCAL_MODEL_LARGE="$LOCAL_MODEL"

# No-credit execution defaults.
export HEXAMIND_WEB_RESEARCH="0"
export HEXAMIND_REQUIRE_RESEARCH_SOURCES="0"
export HEXAMIND_HARD_FAIL_ON_NO_SOURCES="0"
export HEXAMIND_PARALLEL_AGENTS="false"

# Keep quality gates active while iterating locally.
export HEXAMIND_FINAL_MIN_LENGTH="1200"
export HEXAMIND_FINAL_MIN_CITATIONS="3"
export HEXAMIND_FINAL_AUTO_RETRY="1"
export HEXAMIND_RETRIEVAL_TIMEOUT_SECONDS="40"
export HEXAMIND_AGENT_TIMEOUT_SECONDS="180"
export HEXAMIND_FINAL_TIMEOUT_SECONDS="300"
export HEXAMIND_STREAM_MAX_CONCURRENT="1"

echo "Starting Hexamind v1 NO-CREDIT LOCAL mode on ${HOST}:${PORT}"
echo "Provider chain: ${HEXAMIND_PROVIDER_CHAIN}"
echo "Local model: ${LOCAL_MODEL}"

exec "$ROOT_DIR/.venv/bin/python" -m uvicorn main:app --host "$HOST" --port "$PORT"
