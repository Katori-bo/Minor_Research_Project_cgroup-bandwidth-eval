#!/usr/bin/env bash
set -euo pipefail
if [[ $EUID -eq 0 || ! -t 0 ]]; then
  echo 'Use your normal-user external interactive terminal.' >&2
  exit 1
fi
TASK_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TASK_AUDIT="${1:?Pass the reviewed root observer-audit JSON.}"
TASK_SESSION="${2:-$TASK_ROOT/analysis/runtime_io_v20_background_app/generation-01}"
if pgrep -u "$(id -u)" -x '(ChatGPT|Codex|codex)' >/dev/null; then
  echo 'Fully quit ChatGPT/Codex before launch; this runner will open its own idle app during the open cells.' >&2
  exit 1
fi
python3 "$TASK_ROOT/diagnostic/v20_background_app.py" verify-preparation --directory "$TASK_SESSION"
python3 "$TASK_ROOT/diagnostic/v20_background_app.py" verify-audit --audit "$TASK_AUDIT"
export QUOTA_BACKGROUND_EXTERNAL=1
echo 'During this run, leave the desktop/app untouched. Do not send messages or start agent work.'
exec systemd-inhibit --what=sleep --mode=block --why='Retained V20 idle-app background comparison' \
  python3 "$TASK_ROOT/diagnostic/v20_background_app.py" run --directory "$TASK_SESSION" --audit "$TASK_AUDIT"
