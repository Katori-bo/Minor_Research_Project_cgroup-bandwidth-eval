#!/usr/bin/env bash
set -euo pipefail
if [[ $EUID -eq 0 || ! -t 0 || $# -ne 0 ]]; then
  echo 'Run as your normal user in an external interactive terminal, without arguments.' >&2
  exit 1
fi
TASK_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd -- "$TASK_ROOT"
python3 -B diagnostic/nginx_power_confirmation_study.py verify
if [[ -e analysis/runtime_io_nginx_power_confirmation/generation-01/qualification || -e analysis/runtime_io_nginx_power_confirmation/generation-01/campaign ]]; then
  echo 'Preserve the attempted study. No resumes, retries or overwrites.' >&2
  exit 1
fi
python3 -B -c 'import sys;sys.path.insert(0,"diagnostic");import imgproxy_qualify as h;h.desktop_absent()'
echo 'Fresh NGINX confirmation: two fixture cycles, four smoke cohorts, fresh calibration and 24 validation cohorts.'
echo 'All offers retained: throttling is recorded; unsuccessful offers remain misses in every reference and score.'
echo 'Only CPU2 EPP changes. Separate root watchdog restores it; original binaries and evidence remain intact.'
echo 'Up to 10 minutes qualification plus 45 minutes scientific collection. Stay for the sudo prompt.'
sudo -v
exec systemd-inhibit --what=sleep --mode=block --why='Bounded NGINX power-policy calibration-transfer study' \
  python3 -B diagnostic/nginx_power_confirmation_study.py all
