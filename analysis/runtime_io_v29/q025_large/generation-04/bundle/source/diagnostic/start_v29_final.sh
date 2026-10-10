#!/usr/bin/env bash
set -euo pipefail
if [[ $EUID -eq 0 || ! -t 0 ]]; then
  echo 'Run as your normal user in an external interactive terminal.' >&2
  exit 1
fi
if [[ $# -ne 0 ]]; then
  echo 'Usage: bash diagnostic/start_v29_final.sh' >&2
  exit 2
fi
TASK_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd -- "$TASK_ROOT"
export RESEARCH_V29_CONTEXT=q025_large
python3 -B -c 'import sys;sys.path.insert(0,"diagnostic");import v29r4_common as c;c.require_desktop_absent()'
TASK_SESSION="$TASK_ROOT/analysis/runtime_io_v29/q025_large/generation-04"
TASK_CAMPAIGN="$TASK_ROOT/analysis/runtime_io_v29_campaign/generation-04-final"
if [[ -e "$TASK_CAMPAIGN" || -e "$TASK_SESSION/measurement_lifetime.json" || -d "$TASK_SESSION/slots" ]]; then
  echo 'Preserve attempted data; this launcher cannot resume or overwrite a run.' >&2
  exit 1
fi
python3 -B diagnostic/v29r4_study.py verify-bundle --directory "$TASK_SESSION"
echo 'Fresh q025_large: 16 calibration trials, then frozen forecasts and 16 validation trials.'
echo 'Stay at the terminal through functional checks; sudo may then prompt for the read-only inventory.'
mkdir -p -- "$TASK_ROOT/analysis/runtime_io_v29_campaign"
exec systemd-inhibit --what=sleep --mode=block --why='V29 final-context bounded collection' \
  python3 -B diagnostic/v29r4_campaign.py run --directory "$TASK_CAMPAIGN"
