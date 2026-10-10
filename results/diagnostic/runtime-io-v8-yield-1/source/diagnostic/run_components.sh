#!/usr/bin/env bash
# Foreground by design: run from an external terminal after exiting ChatGPT.
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ $# != 3 || "$2" != "--session" ]]; then
  echo 'Usage: bash diagnostic/run_components.sh {new|resume|analyze} --session results/diagnostic/NEW_SESSION' >&2
  exit 2
fi
action="$1"
session="$3"
case "$action" in
  new) python3 diagnostic/run.py new --components --session "$session" ;;
  resume) python3 diagnostic/run.py resume --components --session "$session" ;;
  analyze) ;;
  *) echo "Unknown action: $action" >&2; exit 2 ;;
esac
python3 diagnostic/component_analysis.py "$session"
