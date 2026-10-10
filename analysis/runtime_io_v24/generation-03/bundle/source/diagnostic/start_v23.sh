#!/usr/bin/env bash
set -euo pipefail
if [[ $EUID -eq 0 || ! -t 0 ]]; then
  echo 'Run as your normal user in an external interactive terminal.' >&2
  exit 1
fi
if [[ $# -ne 2 || ! "$1" =~ ^(run|resume)$ ]]; then
  echo 'Usage: start_v23.sh run|resume DIRECTORY' >&2
  exit 2
fi
TASK_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd -- "$TASK_ROOT"
python3 "$TASK_ROOT/diagnostic/v23_study.py" verify-preparation --directory "$2"
python3 -c 'import sys; sys.path.insert(0,"diagnostic"); import v23_common as c; c.require_desktop_absent()'
echo "Evidence and progress: $2"
echo 'Codex/ChatGPT must already be fully quit. Qualification, calibration, prediction freezing and validation follow the inventory.'
TASK_AUDIT="$TASK_ROOT/analysis/runtime_io_leftover_observer_audit/v23-launch-$(date +%s%N).json"
echo 'The read-only observer inventory needs your local sudo authentication. Collection runs as your normal user.'
sudo python3 "$TASK_ROOT/diagnostic/leftover_observer_audit.py" --output "$TASK_AUDIT"
python3 "$TASK_ROOT/diagnostic/leftover_observer_review.py" write --audit "$TASK_AUDIT"
exec systemd-inhibit --what=sleep --mode=block --why='V23 prospective validation' \
  python3 "$TASK_ROOT/diagnostic/v23_study.py" _foreground --mode "$1" --directory "$2" --observer-audit "$TASK_AUDIT"
