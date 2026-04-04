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
COMMIT_STATE_FILE="reports-versioned/aggregated/.last-commit-run"

timestamp() {
  date -u +"%Y-%m-%dT%H:%M:%SZ"
}

log_line() {
  local line="$1"
  echo "$line"
  echo "$line" >> "$PROGRESS_LOG"
}

init_commit_state() {
  local from_file from_git
  from_file=0
  from_git=0

  if [ -f "$COMMIT_STATE_FILE" ]; then
    from_file="$(cat "$COMMIT_STATE_FILE")"
  fi

  from_git="$(git --no-pager log --oneline | sed -nE 's/.*[Aa]utomated run ([0-9]+)-([0-9]+).*/\2/p' | sort -n | tail -n 1)"
  from_git="${from_git:-0}"

  if [ "$from_file" -gt "$from_git" ]; then
    LAST_COMMIT_RUN="$from_file"
  else
    LAST_COMMIT_RUN="$from_git"
  fi

  echo "$LAST_COMMIT_RUN" > "$COMMIT_STATE_FILE"
  log_line "[$(timestamp)] Commit state initialized at run $LAST_COMMIT_RUN"
}

commit_batch_if_due() {
  local updated_count="$1"

  while [ $((updated_count - LAST_COMMIT_RUN)) -ge 5 ]; do
    local start_run end_run
    start_run=$((LAST_COMMIT_RUN + 1))
    end_run=$((LAST_COMMIT_RUN + 5))
    local commit_message="Automated run ${start_run}-${end_run}"

    git add -A
    if git diff --cached --quiet; then
      log_line "[$(timestamp)] No changes staged for commit ${commit_message}"
    elif git commit -m "$commit_message"; then
      log_line "[$(timestamp)] Commit created: ${commit_message}"
    else
      log_line "[$(timestamp)] Commit failed: ${commit_message}"
      break
    fi

    LAST_COMMIT_RUN="$end_run"
    echo "$LAST_COMMIT_RUN" > "$COMMIT_STATE_FILE"
  done
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

init_commit_state

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
  commit_batch_if_due "$UPDATED"
done
