#!/usr/bin/env bash
set -euo pipefail
if [[ $EUID -eq 0 || ! -t 0 ]]; then
  echo 'Run as your normal user in an external interactive terminal.' >&2
  exit 1
fi
if [[ $# -ne 0 ]]; then
  echo 'Usage: bash diagnostic/start_v29.sh' >&2
  exit 2
fi
TASK_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd -- "$TASK_ROOT"
python3 -B -c 'import sys;sys.path.insert(0,"diagnostic");import v29_common as c;c.require_desktop_absent()'
for TASK_CONTEXT in q050_small q025_small q050_large q025_large; do
  RESEARCH_V29_CONTEXT="$TASK_CONTEXT" python3 -B diagnostic/v29_study.py verify-bundle --directory "analysis/runtime_io_v29/$TASK_CONTEXT/generation-03"
done
echo 'Stay at the terminal through runtime checks; sudo may prompt immediately before the observer inventory.'
TASK_CAMPAIGN="$TASK_ROOT/analysis/runtime_io_v29_campaign/generation-03"
mkdir -p -- "$TASK_ROOT/analysis/runtime_io_v29_campaign"
exec systemd-inhibit --what=sleep --mode=block --why='V29 seven-hour bounded robustness collection' \
  python3 -B diagnostic/v29_campaign.py run --directory "$TASK_CAMPAIGN"
