#!/usr/bin/env bash
set -euo pipefail
if [[ $EUID -eq 0 || ! -t 0 ]]; then
  echo 'Run under your normal user identity in an external interactive terminal.' >&2
  exit 1
fi
if [[ $# -ne 2 || ! "$1" =~ ^(qualify|start|resume)$ ]]; then
  echo 'Usage: start_kernel_observer_cost.sh qualify|start|resume DIRECTORY' >&2
  exit 2
fi
TASK_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
python3 "$TASK_ROOT/diagnostic/kernel_observer_cost.py" verify-preparation --directory "$2"
python3 "$TASK_ROOT/diagnostic/kernel_observer_cost.py" "$1" --directory "$2"
echo "Evidence and progress: $2"
echo 'Fully quit Codex/ChatGPT. Authenticate sudo here; the bounded supervisor drops benchmark privileges.'
sudo -v
exec systemd-inhibit --what=sleep --mode=block --why='V18 kernel observer cost study' \
  sudo -n /usr/bin/python3 "$TASK_ROOT/diagnostic/kernel_observer_cost.py" _supervise --mode "$1" --directory "$2"
