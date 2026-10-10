#!/usr/bin/env bash
set -euo pipefail
if [[ $EUID -eq 0 || ! -t 0 || $# -ne 0 ]]; then
  echo 'Run as your normal user in an external interactive terminal, without arguments.' >&2
  exit 1
fi
TASK_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd -- "$TASK_ROOT"
python3 -B diagnostic/nginx_prepare.py verify
if [[ -e analysis/runtime_io_nginx_feasibility/generation-01/pilot ]]; then
  echo 'Preserve the attempted data; NGINX qualification cannot resume or overwrite.' >&2
  exit 1
fi
python3 -B -c 'import sys;sys.path.insert(0,"diagnostic");import imgproxy_qualify as q;q.desktop_absent()'
echo 'Stock NGINX suitability: three bounded cohorts, about 3 minutes; total limit 10 minutes.'
echo 'Stay for the sudo prompt. This qualifies full-response measurements, not predictions.'
echo 'No original FIFO queue or independent-host replication claim is made.'
sudo -v
exec systemd-inhibit --what=sleep --mode=block --why='Bounded stock NGINX suitability' \
  python3 -B diagnostic/nginx_qualify.py pilot
