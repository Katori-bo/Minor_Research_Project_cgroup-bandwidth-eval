#!/usr/bin/env bash
set -euo pipefail
if [[ $EUID -eq 0 || ! -t 0 ]]; then
  echo 'Run as your normal user in an external interactive terminal.' >&2
  exit 1
fi
if [[ $# -ne 0 ]]; then
  echo 'Usage: bash diagnostic/start_imgproxy_qualification.sh' >&2
  exit 2
fi
TASK_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd -- "$TASK_ROOT"
python3 -B diagnostic/imgproxy_qualify.py verify
if [[ -e analysis/runtime_io_imgproxy_feasibility/generation-01/pilot ]]; then
  echo 'Preserve attempted data; this qualification cannot resume or overwrite.' >&2
  exit 1
fi
python3 -B -c 'import sys; sys.path.insert(0,"diagnostic"); import imgproxy_qualify as q; q.desktop_absent()'
echo 'Imgproxy: twelve bounded engineering trials; no scientific validation collection.'
echo 'Expected duration around 12 minutes; total limit 20 minutes. Stay for the sudo prompt.'
sudo -v
exec systemd-inhibit --what=sleep --mode=block --why='Bounded imgproxy qualification' \
  python3 -B diagnostic/imgproxy_qualify.py pilot
