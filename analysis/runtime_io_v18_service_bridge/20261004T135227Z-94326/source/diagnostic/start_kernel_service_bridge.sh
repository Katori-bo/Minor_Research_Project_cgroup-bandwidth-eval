#!/usr/bin/env bash
set -euo pipefail
if [[ $EUID -eq 0 || ! -t 0 ]]; then
  echo 'Run as your normal user in an external interactive terminal.' >&2
  exit 1
fi
TASK_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
TASK_OUTPUT="$TASK_ROOT/analysis/runtime_io_v18_service_bridge/$(date -u +%Y%m%dT%H%M%SZ)-$$"
mkdir -p -- "$(dirname -- "$TASK_OUTPUT")"
echo "Bounded two-CPU/service compatibility; evidence: $TASK_OUTPUT"
echo 'Five short functional cases. Local sudo authentication is required.'
sudo /usr/bin/python3 "$TASK_ROOT/diagnostic/kernel_service_bridge.py" --output "$TASK_OUTPUT"
echo "Summary: $TASK_OUTPUT/summary.json"
