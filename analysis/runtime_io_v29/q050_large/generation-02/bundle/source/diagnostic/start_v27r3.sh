#!/usr/bin/env bash
set -euo pipefail
if [[ $EUID -eq 0 || ! -t 0 ]]; then
  echo 'Run as your normal user in an external interactive terminal.' >&2
  exit 1
fi
if [[ $# -ne 2 || "$1" != run ]]; then
  echo 'Usage: start_v27r3.sh run DIRECTORY' >&2
  exit 2
fi
TASK_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd -- "$TASK_ROOT"
python3 -B diagnostic/v27r3_study.py verify-bundle --directory "$2"
python3 -B -c 'import sys;sys.path.insert(0,"diagnostic");import v27r3_common as c;c.require_desktop_absent()'
python3 -B diagnostic/v27r3_study.py prepare-runtime --directory "$2"
TASK_AUDIT="$TASK_ROOT/analysis/runtime_io_leftover_observer_audit/v27r3-launch-$(date +%s%N).json"
sudo python3 -B diagnostic/leftover_observer_audit.py --output "$TASK_AUDIT"
python3 -B diagnostic/leftover_observer_review.py write --audit "$TASK_AUDIT"
exec systemd-inhibit --what=sleep --mode=block --why='V27r3 bounded load-composition comparison' \
  python3 -B diagnostic/v27r3_study.py _foreground --directory "$2" --observer-audit "$TASK_AUDIT"
