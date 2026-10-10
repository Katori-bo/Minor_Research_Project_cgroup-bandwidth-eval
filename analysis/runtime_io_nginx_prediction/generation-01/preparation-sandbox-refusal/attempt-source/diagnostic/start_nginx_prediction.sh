#!/usr/bin/env bash
set -euo pipefail
if [[ $EUID -eq 0 || ! -t 0 || $# -ne 0 ]]; then
  echo 'Run as your normal user in an external interactive terminal, without arguments.' >&2
  exit 1
fi
TASK_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd -- "$TASK_ROOT"
python3 -B diagnostic/nginx_prediction_prepare.py verify
if [[ -e analysis/runtime_io_nginx_prediction/generation-01/campaign ]]; then
  echo 'Preserve the attempted campaign; cannot resume, repeat or overwrite.' >&2
  exit 1
fi
python3 -B -c 'import sys;sys.path.insert(0,"diagnostic");import imgproxy_qualify as q;q.desktop_absent()'
echo 'NGINX: three new-rate qualification cohorts, four fresh calibration cohorts, frozen forecast, 18 held-out trials.'
echo 'About 30 minutes; total limit 45 minutes. Stay for the sudo prompt.'
echo 'Stops at the first technical/applicability exit; no replacement. This does not establish novelty.'
sudo -v
exec systemd-inhibit --what=sleep --mode=block --why='Bounded prospective NGINX prediction study' \
  python3 -B diagnostic/nginx_prediction_study.py campaign
