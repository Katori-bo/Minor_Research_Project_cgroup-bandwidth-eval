#!/usr/bin/env bash
set -euo pipefail
if [[ $EUID -eq 0 || ! -t 0 ]]; then
  echo 'Run from your normal-user external interactive terminal.' >&2
  exit 1
fi
TASK_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TASK_SESSION="${1:-$TASK_ROOT/analysis/runtime_io_gc_probe/generation-01}"
if pgrep -u "$(id -u)" -x '(ChatGPT|Codex|codex)' >/dev/null; then
  echo 'Fully quit ChatGPT/Codex before launching the performance run.' >&2
  exit 1
fi
python3 "$TASK_ROOT/diagnostic/runtime_gc_probe.py" verify-preparation --directory "$TASK_SESSION"
export QUOTA_GC_EXTERNAL=1
exec systemd-inhibit --what=sleep --mode=block --why='Same-binary GC / CPU-period diagnostic' \
  python3 "$TASK_ROOT/diagnostic/runtime_gc_probe.py" run --directory "$TASK_SESSION"
