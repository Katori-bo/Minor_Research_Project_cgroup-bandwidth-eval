#!/usr/bin/env bash
set -euo pipefail
if [[ $EUID -eq 0 || ! -t 0 ]]; then
  echo 'Run as your normal user in an external interactive terminal.' >&2
  exit 1
fi
if [[ $# -ne 0 ]]; then
  echo 'Usage: bash diagnostic/start_v31.sh' >&2
  exit 2
fi
TASK_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd -- "$TASK_ROOT"
python3 -B -c 'import sys;sys.path.insert(0,"diagnostic");import v31_common as c;c.require_desktop_absent()'
TASK_SESSION="$TASK_ROOT/analysis/runtime_io_v31/generation-01"
TASK_CAMPAIGN="$TASK_ROOT/analysis/runtime_io_v31_campaign/generation-01"
if [[ -e "$TASK_CAMPAIGN" || -e "$TASK_SESSION/measurement_lifetime.json" || -d "$TASK_SESSION/slots" ]]; then
  echo 'Preserve attempted data; this launcher cannot resume or overwrite a run.' >&2
  exit 1
fi
python3 -B diagnostic/v31_study.py verify-bundle --directory "$TASK_SESSION"
echo 'V31: 16 fresh calibration trials; sealed timing forecasts; 18 held-out validation trials.'
echo 'Stay at the terminal through functional checks and the sudo prompt for the read-only observer inventory.'
mkdir -p -- "$TASK_ROOT/analysis/runtime_io_v31_campaign"
exec systemd-inhibit --what=sleep --mode=block --why='V31 bounded deadline confirmation' \
  python3 -B diagnostic/v31_campaign.py run --directory "$TASK_CAMPAIGN"
