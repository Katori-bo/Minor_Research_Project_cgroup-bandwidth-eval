#!/usr/bin/env bash
set -euo pipefail
if [[ $EUID -eq 0 || ! -t 0 || $# -ne 0 ]]; then
  echo 'Run as your normal user in an external interactive terminal, without arguments.' >&2
  exit 1
fi
TASK_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd -- "$TASK_ROOT"
python3 -B diagnostic/nginx_worker_wait_study.py verify
if [[ -e analysis/runtime_io_nginx_worker_wait_qualification/generation-01/qualification ]]; then
  echo 'Preserve the attempted qualification. No retries, resumes or overwrites.' >&2
  exit 1
fi
python3 -B -c 'import sys;sys.path.insert(0,"diagnostic");import imgproxy_qualify as h;h.desktop_absent()'
echo 'Worker-wait qualification: two boundary checks, then six randomized paired blocks at 4/s and 8/s.'
echo '7,890 offered requests; at most 10 minutes boundary phase plus 45 minutes overhead phase.'
echo 'Power and scheduler settings remain unchanged. Sudo is for the read-only observer inventory.'
echo 'The launcher ends after qualification; predictive discovery is a separate study.'
sudo -v
exec systemd-inhibit --what=sleep --mode=block --why='Bounded NGINX worker counter qualification' \
  python3 -B diagnostic/nginx_worker_wait_study.py all
