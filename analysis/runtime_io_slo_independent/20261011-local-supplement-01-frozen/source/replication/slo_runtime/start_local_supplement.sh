#!/usr/bin/env bash
# External human launcher. Never invoked by package preparation or offline tests.
set -euo pipefail

supplement_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$supplement_dir"
application="${1:-}"
if [[ "$application" != Go && "$application" != NGINX ]]; then
  echo 'Usage: bash start_local_supplement.sh Go|NGINX --amendment-accepted --allocation-confirmed' >&2
  exit 2
fi
shift
python3 -B runtime/prelaunch_local_supplement.py --application "$application" "$@"

TASK_APPS='ChatGPT|Codex|chrome|chromium|firefox|brave|msedge|Discord|discord|slack|steam'
pkill -TERM -u "$UID" -x "$TASK_APPS" || [ "$?" -eq 1 ]
sleep 5
if [[ "$application" == Go ]]; then
  python3 -B runtime/setup.py setup --amendment-accepted
fi
exec systemd-inhibit --what=sleep:idle --mode=block \
  python3 -B runtime/supervisor.py run --application "$application" \
  --amendment-accepted --allocation-confirmed
