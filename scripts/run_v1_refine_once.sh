#!/usr/bin/env bash
set -euo pipefail

API_BASE="${API_BASE:-http://127.0.0.1:8011}"
QUERY="${1:-Why is the population of South Korea declining so rapidly?}"
REPORT_LENGTH="${REPORT_LENGTH:-moderate}"

if ! command -v jq >/dev/null 2>&1; then
  echo "jq is required. Install it and retry."
  exit 1
fi

start_payload="$(jq -n --arg q "$QUERY" --arg rl "$REPORT_LENGTH" '{query:$q, reportLength:$rl}')"
start_resp="$(curl -sS --max-time 30 -X POST "$API_BASE/api/pipeline/start" -H "Content-Type: application/json" -d "$start_payload")"

session_id="$(printf '%s' "$start_resp" | jq -r '.sessionId // empty')"
if [[ -z "$session_id" ]]; then
  echo "Failed to create session"
  echo "$start_resp"
  exit 1
fi

out_dir="/tmp/hexamind-refine"
mkdir -p "$out_dir"
stream_file="$out_dir/${session_id}.sse"
quality_file="$out_dir/${session_id}.quality.json"

curl -sS --max-time 1800 "$API_BASE/api/pipeline/${session_id}/stream" > "$stream_file"
curl -sS --max-time 30 "$API_BASE/api/pipeline/${session_id}/quality" > "$quality_file"

overall="$(jq -r '.overallScore // 0' "$quality_file")"
trust="$(jq -r '.trustScore // 0' "$quality_file")"
citations="$(jq -r '.metrics.citationCount // 0' "$quality_file")"
sources="$(jq -r '.metrics.sourceCount // 0' "$quality_file")"

printf "Session: %s\n" "$session_id"
printf "Overall score: %s\n" "$overall"
printf "Trust score: %s\n" "$trust"
printf "Citations: %s\n" "$citations"
printf "Sources: %s\n" "$sources"
printf "Stream file: %s\n" "$stream_file"
printf "Quality file: %s\n" "$quality_file"
