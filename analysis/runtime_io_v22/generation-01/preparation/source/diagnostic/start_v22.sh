#!/usr/bin/env bash
set -euo pipefail
if [[ $EUID -eq 0 || ! -t 0 ]]; then
  echo 'Run as your normal user in an external interactive terminal.' >&2
  exit 1
fi
if [[ $# -ne 2 || ! "$1" =~ ^(run|resume)$ ]]; then
  echo 'Usage: start_v22.sh run|resume DIRECTORY' >&2
  exit 2
fi
TASK_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
python3 "$TASK_ROOT/diagnostic/v22_study.py" verify-preparation --directory "$2"
echo "Evidence and progress: $2"
echo 'Fully quit Codex/ChatGPT. Qualification, calibration, prediction freezing and validation run in that order.'
exec systemd-inhibit --what=sleep --mode=block --why='V22 prospective validation' \
  python3 "$TASK_ROOT/diagnostic/v22_study.py" _foreground --mode "$1" --directory "$2"
