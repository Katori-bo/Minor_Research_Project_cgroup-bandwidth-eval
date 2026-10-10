#!/usr/bin/env bash
set -euo pipefail
if [[ $EUID -eq 0 || ! -t 0 || $# -ne 0 ]]; then
  echo 'Run as your normal user in an external interactive terminal, without arguments.' >&2
  exit 1
fi
TASK_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd -- "$TASK_ROOT"
python3 -B diagnostic/gzip_qualify.py verify
if [[ -e analysis/runtime_io_gzip_qualification/generation-01/pilot ]]; then
  echo 'Preserve attempted data; this qualification cannot resume or overwrite.' >&2
  exit 1
fi
python3 -B -c 'import sys;sys.path.insert(0,"diagnostic");import imgproxy_qualify as q;q.desktop_absent()'
echo 'Gzip qualification: six pairs, twelve bounded service trials.'
echo 'About 12 minutes; total limit 20 minutes. Stay for the sudo prompt.'
echo 'This checks the new apparatus; scientific replication and novelty remain untested.'
sudo -v
exec systemd-inhibit --what=sleep --mode=block --why='Bounded native gzip qualification' \
  python3 -B diagnostic/gzip_qualify.py pilot
