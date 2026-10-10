#!/usr/bin/env bash
set -euo pipefail
if [[ $EUID -eq 0 || ! -t 0 ]]; then
  echo 'Run as your normal user in an external interactive terminal.' >&2
  exit 1
fi
if [[ $# -ne 2 || "$1" != run ]]; then
  echo 'Usage: start_v24.sh run DIRECTORY' >&2
  exit 2
fi
TASK_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd -- "$TASK_ROOT"
python3 diagnostic/v24_study.py verify-bundle --directory "$2"
python3 -c 'import sys;sys.path.insert(0,"diagnostic");import v24_common as c;c.require_desktop_absent()'
echo 'V24: deferred runtime qualification, fresh observer review, then12 quiet measurement slots.'
echo "Evidence: $2"
python3 diagnostic/v24_study.py prepare-runtime --directory "$2"
TASK_AUDIT="$TASK_ROOT/analysis/runtime_io_leftover_observer_audit/v24-launch-$(date +%s%N).json"
echo 'The read-only inventory needs local sudo authentication. Collection runs as your normal user.'
sudo python3 diagnostic/leftover_observer_audit.py --output "$TASK_AUDIT"
python3 diagnostic/leftover_observer_review.py write --audit "$TASK_AUDIT"
exec systemd-inhibit --what=sleep --mode=block --why='V24 phase CPU accounting' \
  python3 diagnostic/v24_study.py _foreground --directory "$2" --observer-audit "$TASK_AUDIT"
