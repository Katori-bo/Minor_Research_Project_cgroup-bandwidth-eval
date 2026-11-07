#!/usr/bin/env bash
set -euo pipefail
if [[ $EUID -eq 0 || ! -t 0 || $# -ne 0 ]]; then
  echo 'Run as your normal user in an external interactive terminal, without arguments.' >&2
  exit 1
fi
TASK_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd -- "$TASK_ROOT"
python3 -B diagnostic/nginx_rate_transfer_study.py verify
if [[ -e analysis/runtime_io_nginx_rate_transfer/generation-01/qualification || -e analysis/runtime_io_nginx_rate_transfer/generation-01/campaign ]]; then
  echo 'Preserve the attempted study. No resumes, retries or overwrites.' >&2
  exit 1
fi
python3 -B -c 'import sys;sys.path.insert(0,"diagnostic");import imgproxy_qualify as h;h.desktop_absent()'
echo 'Fixed-P0 rate-transfer study: three smoke cohorts and a full 4/s lifetime qualification.'
echo 'Then six fresh calibration cohorts at 4/5/8 per second and twelve validation cohorts at 4/8.'
echo 'Power settings are checked, without changes. All offers and throttling are retained.'
echo 'Up to 10 minutes qualification plus 45 minutes collection. Sudo is only for the read-only observer inventory.'
sudo -v
exec systemd-inhibit --what=sleep --mode=block --why='Bounded fixed-P0 NGINX rate-matched calibration study' \
  python3 -B diagnostic/nginx_rate_transfer_study.py all
