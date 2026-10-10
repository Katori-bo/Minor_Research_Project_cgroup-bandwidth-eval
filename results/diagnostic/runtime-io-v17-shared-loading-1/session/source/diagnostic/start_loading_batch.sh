#!/usr/bin/env bash
set -euo pipefail
study_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$study_root"
python3 diagnostic/loading_study.py verify-build
printf 'Closing ChatGPT/Codex before the separate 16-trial V17 shared-loading batch...\n'
pkill -TERM -x ChatGPT || true
for attempt in {1..30}; do
    if ! pgrep -x ChatGPT >/dev/null; then break; fi
    sleep 1
done
if pgrep -x ChatGPT >/dev/null; then
    printf 'ChatGPT is still running. Fully quit it and rerun this script.\n' >&2
    exit 1
fi
python3 diagnostic/loading_study.py start
python3 diagnostic/loading_study.py watch
study_directory="results/diagnostic/runtime-io-v17-shared-loading-1"
if [[ -f "$study_directory/completion.json" ]]; then
    printf '\nCompleted result report:\n'
    cat "$study_directory/session/analysis/report.md"
else
    printf '\nCheck saved state with: python3 diagnostic/loading_study.py status\n'
fi
