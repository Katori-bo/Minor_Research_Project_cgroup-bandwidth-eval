#!/usr/bin/env bash
set -euo pipefail
if [[ $EUID -eq 0 || ! -t 0 || $# -ne 0 ]]; then
  echo 'Run bash start_v31_host02.sh as your normal user in an external interactive terminal.' >&2
  exit 1
fi
TASK_PACKAGE_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd -- "$TASK_PACKAGE_ROOT"
python3 -B scripts/host02_cli.py check
python3 -B -c 'import sys;sys.path.insert(0,"diagnostic");import v31_common as c;c.require_desktop_absent()'
TASK_SESSION="$TASK_PACKAGE_ROOT/runs/host02/study/generation-01"
TASK_CAMPAIGN="$TASK_PACKAGE_ROOT/runs/host02/campaign/generation-01"
if [[ -e "$TASK_CAMPAIGN" || -e "$TASK_SESSION/measurement_lifetime.json" || -d "$TASK_SESSION/slots" || -d "$TASK_SESSION/preparation" ]]; then
  echo 'Preserve existing qualification/collection attempts. Automatic restart or resume is prohibited.' >&2
  exit 1
fi
python3 -B diagnostic/v31_study.py verify-bundle --directory "$TASK_SESSION"
mkdir -p -- "$TASK_PACKAGE_ROOT/runs/host02"
TASK_LOG="$TASK_PACKAGE_ROOT/runs/host02/launch.log"
if [[ -e "$TASK_LOG" ]]; then
  echo 'Preserve the existing launch log; review before another attempt.' >&2
  exit 1
fi
echo 'V31 HOST02: resource preflight and six functional cases, then 16 calibration + 18 validation trials.'
echo '10 ms is the response deadline; CPU quota/period is 25/100 ms. No 300-trial matrix.'
echo 'Stay present for the read-only observer-inventory sudo prompt. Ctrl+C preserves partial results.'
set +e
systemd-inhibit --what=sleep --mode=block --why='V31 host02 bounded independent replication' \
  taskset -c 0,1 python3 -B -u diagnostic/v31_campaign.py run --directory "$TASK_CAMPAIGN" 2>&1 | tee "$TASK_LOG"
TASK_RESULT=${PIPESTATUS[0]}
exit "$TASK_RESULT"
