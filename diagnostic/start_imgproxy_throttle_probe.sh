#!/usr/bin/env bash
set -euo pipefail
if [[ $EUID -eq 0 || ! -t 0 || $# -ne 0 ]]; then
  echo 'Run as your normal user in an external interactive terminal, without arguments.' >&2
  exit 1
fi
TASK_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd -- "$TASK_ROOT"
python3 -B diagnostic/imgproxy_throttle_probe.py verify
if [[ -e analysis/runtime_io_imgproxy_throttle_probe/generation-01/run ]]; then
  echo 'Preserve attempted data; the forensic probe cannot resume or overwrite.' >&2
  exit 1
fi
python3 -B -c 'import sys;sys.path.insert(0,"diagnostic");import imgproxy_qualify as q;q.desktop_absent()'
echo 'One forensic service: unchanged application, workload, rate and quota. About two minutes.'
echo 'This diagnoses the stopped pilot; it does not replace or pass that pilot.'
sudo -v
exec systemd-inhibit --what=sleep --mode=block --why='Bounded imgproxy throttle localization' \
  python3 -B diagnostic/imgproxy_throttle_probe.py run
