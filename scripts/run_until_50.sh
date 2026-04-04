#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

source .venv/bin/activate
set -a
source .env.autonomous
set +a

TARGET="${1:-50}"
HEARTBEAT_SECONDS="${HEARTBEAT_SECONDS:-60}"
MAX_RUN_SECONDS="${MAX_RUN_SECONDS:-1800}"

PROGRESS_LOG="reports-versioned/aggregated/autonomous-progress.log"

timestamp() {
  date -u +"%Y-%m-%dT%H:%M:%SZ"
}

log_line() {
  local line="$1"
  echo "$line"
  echo "$line" >> "$PROGRESS_LOG"
}

run_count() {
  python - <<'PY'
import json
from pathlib import Path
p = Path('reports-versioned/aggregated/run-metrics-history.json')
if not p.exists():
    print(0)
else:
    try:
        print(len(json.loads(p.read_text(encoding='utf-8'))))
    except Exception:
        print(0)
PY
}

while true; do
  CURRENT="$(run_count)"
  if [ "$CURRENT" -ge "$TARGET" ]; then
    log_line "[$(timestamp)] Reached target reports: $CURRENT"
    break
  fi

  RUN_NUMBER="$((CURRENT + 1))"
  RUN_START_EPOCH="$(date +%s)"
  log_line "[$(timestamp)] Run $RUN_NUMBER/$TARGET started"

  timeout "$MAX_RUN_SECONDS" python scripts/extract_and_research.py &
  RUN_PID=$!

  while kill -0 "$RUN_PID" 2>/dev/null; do
    sleep "$HEARTBEAT_SECONDS"
    if kill -0 "$RUN_PID" 2>/dev/null; then
      NOW_EPOCH="$(date +%s)"
      ELAPSED="$((NOW_EPOCH - RUN_START_EPOCH))"
      log_line "[$(timestamp)] heartbeat: run $RUN_NUMBER still running (${ELAPSED}s elapsed)"
    fi
  done

  wait "$RUN_PID"
  RUN_EXIT_CODE=$?

  if [ "$RUN_EXIT_CODE" -ne 0 ]; then
    log_line "[$(timestamp)] Run $RUN_NUMBER failed with exit code $RUN_EXIT_CODE"
    continue
  fi

  UPDATED="$(run_count)"
  RUN_END_EPOCH="$(date +%s)"
  DURATION="$((RUN_END_EPOCH - RUN_START_EPOCH))"
  log_line "[$(timestamp)] Run:($UPDATED) is completed in ${DURATION}s"
done
