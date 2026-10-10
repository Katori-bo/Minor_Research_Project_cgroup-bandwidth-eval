#!/usr/bin/env bash
set -euo pipefail
if [[ $EUID -eq 0 || ! -t 0 ]]; then
  echo 'Run as your normal user in an external interactive terminal.' >&2
  exit 1
fi
if [[ $# -ne 2 || "$1" != run ]]; then
  echo 'Usage: start_v25.sh run DIRECTORY' >&2
  exit 2
fi
TASK_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd -- "$TASK_ROOT"
python3 diagnostic/v25_study.py verify-bundle --directory "$2"
python3 -c 'import sys;sys.path.insert(0,"diagnostic");import v25_common as c;c.require_desktop_absent()'
python3 diagnostic/v25_study.py prepare-runtime --directory "$2"
TASK_AUDIT="$TASK_ROOT/analysis/runtime_io_leftover_observer_audit/v25-launch-$(date +%s%N).json"
sudo python3 diagnostic/leftover_observer_audit.py --output "$TASK_AUDIT"
python3 diagnostic/leftover_observer_review.py write --audit "$TASK_AUDIT"
exec systemd-inhibit --what=sleep --mode=block --why='V25 bounded repeated-control diagnostic' \
  python3 diagnostic/v25_study.py _foreground --directory "$2" --observer-audit "$TASK_AUDIT"
