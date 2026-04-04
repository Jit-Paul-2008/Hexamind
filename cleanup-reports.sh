#!/bin/bash
# Hexamind Reports Cleanup Script
# Removes duplicate and old reports, keeping only the latest batch

set -e

REPORTS_DIR="ai-service/.data/reports"
BENCHMARKS_DIR="ai-service/.data/benchmarks"
ARCHIVE_REPORTS="ai-service/.data/reports-archive"
ARCHIVE_BENCHMARKS="ai-service/.data/benchmarks-archive"

echo "=== Hexamind Reports Cleanup ==="
echo

# Create archive directories if they don't exist
mkdir -p "$ARCHIVE_REPORTS" "$ARCHIVE_BENCHMARKS"

# Identify old batch reports (timestamps before 05:54)
echo "Archiving old batch reports (04:12-05:53 timestamps)..."
for f in "$REPORTS_DIR"/random-topic-full-report-20260404-0[3-5][0-5]*.md; do
  if [ -f "$f" ]; then
    timestamp=$(basename "$f" | grep -oE "20260404-[0-9]{6}" | cut -d- -f2)
    if [ "$timestamp" -lt "055400" ]; then
      echo "  -> Archiving: $(basename "$f")"
      mv "$f" "$ARCHIVE_REPORTS/"
    fi
  fi
done

# Remove the early test report (no run number)
if [ -f "$REPORTS_DIR/random-topic-full-report-20260404-035511.md" ]; then
  echo "Removing early test report..."
  rm "$REPORTS_DIR/random-topic-full-report-20260404-035511.md"
fi

echo "Archiving old batch benchmarks..."
for f in "$BENCHMARKS_DIR"/benchmark-random-topic-run0[1-9]-20260404-0[3-5][0-4]*.json; do
  if [ -f "$f" ]; then
    timestamp=$(basename "$f" | grep -oE "20260404-[0-9]{6}" | cut -d- -f2)
    if [ "$timestamp" -lt "055400" ]; then
      echo "  -> Archiving: $(basename "$f")"
      mv "$f" "$ARCHIVE_BENCHMARKS/"
    fi
  fi
done

echo
echo "=== Cleanup Complete ==="
echo "Reports retained: $(ls -1 "$REPORTS_DIR"/*.md 2>/dev/null | grep -c random-topic)"
echo "Benchmarks retained: $(ls -1 "$BENCHMARKS_DIR"/*.json 2>/dev/null | grep -c random-topic)"
echo "Reports archived: $(ls -1 "$ARCHIVE_REPORTS"/*.md 2>/dev/null | grep -c random-topic || echo 0)"
echo "Benchmarks archived: $(ls -1 "$ARCHIVE_BENCHMARKS"/*.json 2>/dev/null | grep -c random-topic || echo 0)"
