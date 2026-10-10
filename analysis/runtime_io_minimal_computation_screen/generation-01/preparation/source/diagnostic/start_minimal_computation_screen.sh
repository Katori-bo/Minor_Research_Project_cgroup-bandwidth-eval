#!/usr/bin/env bash
set -euo pipefail
if [[ $EUID -eq 0 || ! -t 0 ]]; then
  echo 'Use your normal-user external interactive terminal.' >&2
  exit 1
fi
TASK_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TASK_AUDIT="${1:?Pass the completed root observer-audit JSON path.}"
TASK_SESSION="${2:-$TASK_ROOT/analysis/runtime_io_minimal_computation_screen/generation-01}"
if pgrep -u "$(id -u)" -x '(ChatGPT|Codex|codex)' >/dev/null; then
  echo 'Fully quit ChatGPT/Codex before launching.' >&2
  exit 1
fi
python3 "$TASK_ROOT/diagnostic/minimal_computation_screen.py" verify-audit --audit "$TASK_AUDIT"
python3 "$TASK_ROOT/diagnostic/minimal_computation_screen.py" verify-preparation --directory "$TASK_SESSION"
export QUOTA_MINIMAL_EXTERNAL=1
exec systemd-inhibit --what=sleep --mode=block --why='Bounded full-service / minimal SHA comparison' \
  python3 "$TASK_ROOT/diagnostic/minimal_computation_screen.py" run --directory "$TASK_SESSION" --audit "$TASK_AUDIT"
