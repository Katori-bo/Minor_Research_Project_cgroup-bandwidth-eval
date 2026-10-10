#!/usr/bin/env bash
set -euo pipefail
if [[ $EUID -eq 0 || ! -t 0 ]]; then
  echo 'Use your normal-user external interactive terminal.' >&2
  exit 1
fi
TASK_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TASK_AUDIT="${1:?Pass the reviewed root observer-audit JSON.}"
TASK_SESSION="${2:-$TASK_ROOT/analysis/runtime_io_execution_state_continuation/generation-01}"
if pgrep -u "$(id -u)" -x '(ChatGPT|Codex|codex)' >/dev/null; then
  echo 'Fully quit ChatGPT/Codex before launching.' >&2
  exit 1
fi
python3 "$TASK_ROOT/diagnostic/execution_state_continuation.py" verify-preparation --directory "$TASK_SESSION"
python3 "$TASK_ROOT/diagnostic/execution_state_continuation.py" verify-audit --audit "$TASK_AUDIT"
sudo -v
export QUOTA_CONTINUATION_EXTERNAL=1
exec systemd-inhibit --what=sleep --mode=block --why='Four-cell execution-state continuation' \
  python3 "$TASK_ROOT/diagnostic/execution_state_continuation.py" run --directory "$TASK_SESSION" --audit "$TASK_AUDIT"
