bash -c '
set -euo pipefail
cd /home/Aditya/Desktop/Research_project/cpu-quota-tail-latency
TASK_APPS="ChatGPT|Codex|chrome|chromium|firefox|brave|msedge|Discord|discord|slack|steam"
pkill -TERM -u "$UID" -x "$TASK_APPS" || [ "$?" -eq 1 ]
sleep 5
exec bash diagnostic/start_v29.sh
'
