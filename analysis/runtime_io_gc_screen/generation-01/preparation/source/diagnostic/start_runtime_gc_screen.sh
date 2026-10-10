#!/usr/bin/env bash
set -euo pipefail
if [[ $EUID -eq 0 || ! -t 0 ]]; then
  echo 'Use your normal-user external interactive terminal.' >&2
  exit 1
fi
TASK_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TASK_SESSION="${1:-$TASK_ROOT/analysis/runtime_io_gc_screen/generation-01}"
if pgrep -u "$(id -u)" -x '(ChatGPT|Codex|codex)' >/dev/null; then
  echo 'Fully quit ChatGPT/Codex before launching.' >&2
  exit 1
fi
python3 "$TASK_ROOT/diagnostic/runtime_gc_screen.py" verify-preparation --directory "$TASK_SESSION"
export QUOTA_GC_SCREEN_EXTERNAL=1
exec systemd-inhibit --what=sleep --mode=block --why='Eight-trial GC / CPU-period screen' \
  python3 "$TASK_ROOT/diagnostic/runtime_gc_screen.py" run --directory "$TASK_SESSION"
