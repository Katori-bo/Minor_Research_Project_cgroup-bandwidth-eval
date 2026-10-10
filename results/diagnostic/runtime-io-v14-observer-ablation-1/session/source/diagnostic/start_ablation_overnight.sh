#!/usr/bin/env bash
# Invoke from an external terminal: closes the desktop app, then starts V14.
set -euo pipefail
study_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$study_root"
printf 'Closing ChatGPT/Codex before controlled collection...\n'
pkill -TERM -x ChatGPT || true
for attempt in {1..30}; do
    if ! pgrep -x ChatGPT >/dev/null; then break; fi
    sleep 1
done
if pgrep -x ChatGPT >/dev/null; then
    printf 'ChatGPT is still running. Fully quit it and rerun this script.\n' >&2
    exit 1
fi
python3 diagnostic/ablation_study.py start
python3 diagnostic/ablation_study.py watch
study_report="results/diagnostic/runtime-io-v14-observer-ablation-1/session/analysis/report.md"
if [[ -f results/diagnostic/runtime-io-v14-observer-ablation-1/completion.json ]]; then
    printf '\nCompleted result report:\n'
    cat "$study_report"
else
    printf '\nCollection may still be running or require attention. Check with:\npython3 diagnostic/ablation_study.py status\n'
fi
