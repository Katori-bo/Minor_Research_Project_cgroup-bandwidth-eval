#!/usr/bin/env bash
# One external terminal command; one unused amendment package, no retries.
set -euo pipefail
completion_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$completion_dir"
python3 -B runtime/prelaunch_local_supplement.py --application NGINX "$@"
if [[ ! -t 0 ]]; then
  echo 'Use your external interactive terminal so sudo can authenticate.' >&2
  exit 2
fi
TASK_APPS='ChatGPT|Codex|chrome|chromium|firefox|brave|msedge|Discord|discord|slack|steam'
pkill -TERM -u "$UID" -x "$TASK_APPS" || [ "$?" -eq 1 ]
sleep 5
exec systemd-inhibit --what=sleep:idle --mode=block bash -c '
set -euo pipefail
python3 -B runtime/setup.py setup --amendment-accepted
echo "Authenticate now for the privileged inventory. No NGINX campaign has started."
python3 -B runtime/nginx_completion.py precheck --amendment-accepted --allocation-confirmed
status=0
python3 -B runtime/supervisor.py run --application NGINX --amendment-accepted --allocation-confirmed || status=$?
if [[ -f runs/host01/NGINX/return_seal.json ]]; then
  python3 -B runtime/assemble_returns.py --host-package "$PWD" --output "$PWD/runs/host01/final_report.json"
  echo "Closed campaign report: $PWD/runs/host01/final_report.json"
fi
exit "$status"
'
