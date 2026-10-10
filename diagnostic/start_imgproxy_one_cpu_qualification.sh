#!/usr/bin/env bash
set -euo pipefail
if [[ $EUID -eq 0 || ! -t 0 || $# -ne 0 ]]; then
  echo 'Run as your normal user in an external interactive terminal, without arguments.' >&2
  exit 1
fi
TASK_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd -- "$TASK_ROOT"
python3 -B diagnostic/imgproxy_one_cpu_qualify.py verify
if [[ -e analysis/runtime_io_imgproxy_one_cpu_qualification/generation-01/pilot ]]; then
  echo 'Preserve attempted data; this new qualification cannot resume or overwrite.' >&2
  exit 1
fi
python3 -B -c 'import sys;sys.path.insert(0,"diagnostic");import imgproxy_qualify as q;q.desktop_absent()'
echo 'New one-CPU imgproxy qualification: six pairs, twelve bounded services.'
echo 'About 12 minutes; total limit 20 minutes. The original failed pilot remains unchanged.'
echo 'This checks engineering readiness; it does not establish replication or novelty. Stay for the sudo prompt.'
sudo -v
exec systemd-inhibit --what=sleep --mode=block --why='Bounded one-CPU imgproxy qualification' \
  python3 -B diagnostic/imgproxy_one_cpu_qualify.py pilot
