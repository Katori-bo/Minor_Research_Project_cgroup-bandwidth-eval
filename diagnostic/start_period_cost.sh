#!/usr/bin/env bash
set -euo pipefail
if [[ $EUID -eq 0 || ! -t 0 ]]; then
  echo 'Run as your normal user in an external interactive terminal.' >&2
  exit 1
fi
if [[ $# -gt 1 ]]; then
  echo 'Usage: start_period_cost.sh [GENERATION_DIRECTORY]' >&2
  exit 2
fi
TASK_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
TASK_SESSION="${1:-$TASK_ROOT/analysis/runtime_io_period_cost_pilot/generation-02}"
python3 "$TASK_ROOT/diagnostic/period_cost.py" verify-preparation --directory "$TASK_SESSION"
python3 -c "import sys; sys.path.insert(0, sys.argv[1]); import run; run.require_quiet_host()" "$TASK_ROOT/diagnostic"
echo 'One capped pilot: four counter fixtures, then at most 16 service trials.'
echo 'Sudo is needed only for the bounded counter helper; authenticate here.'
echo "Evidence: $TASK_SESSION"
sudo -v
exec systemd-inhibit --what=sleep --mode=block --why='CPU-period cost feasibility pilot' \
  python3 "$TASK_ROOT/diagnostic/period_cost.py" run --directory "$TASK_SESSION"
