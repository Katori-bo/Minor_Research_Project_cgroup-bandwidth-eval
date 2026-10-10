#!/usr/bin/env bash
# Foreground collection; source/build are verified before starting or resuming.
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ $# != 3 || "$2" != "--session" ]]; then
  echo 'Usage: bash diagnostic/run_yield_study.sh {new|resume|analyze} --session results/diagnostic/NEW_SESSION' >&2
  exit 2
fi
action="$1"
session="$3"
case "$action" in
  new|resume|analyze) ;;
  *) echo "Unknown action: $action" >&2; exit 2 ;;
esac
# Keep the shared experiment lock through collection AND trace analysis.
exec 9>>.experiment.lock
if ! flock -n 9; then
  echo 'Another experiment is running.' >&2
  exit 1
fi
export CPU_QUOTA_EXPERIMENT_LOCK_FD=9
export PYTHONUNBUFFERED=1
if [[ "$action" != "analyze" ]]; then
  python3 diagnostic/run.py "$action" --yield-study --session "$session"
fi
python3 diagnostic/yield_analysis.py "$session"
