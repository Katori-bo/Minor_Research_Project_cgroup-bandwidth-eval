#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$ROOT"
SESSION="$ROOT/results/sessions/$(date +%Y%m%d-%H%M%S)"
mkdir -p "$ROOT/results/launch-logs"
LOG="$ROOT/results/launch-logs/$(basename "$SESSION").log"
echo "Session: $SESSION"
echo "Log: $LOG"
echo "Keep power connected and automatic suspend disabled for this run."
# A standalone terminal survives closing the editor/ChatGPT. No automatic shutdown.
set +e
taskset -c 0,1 "$ROOT/venv/bin/python" -u "$ROOT/scripts/experiment.py" new --session "$SESSION" "$@" 2>&1 | tee "$LOG"
RESULT=${PIPESTATUS[0]}
exit "$RESULT"
