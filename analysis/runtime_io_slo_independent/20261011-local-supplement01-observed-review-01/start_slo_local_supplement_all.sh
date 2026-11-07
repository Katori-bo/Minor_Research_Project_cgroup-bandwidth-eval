#!/usr/bin/env bash
# Human external launch only. The sealed per-service launchers enforce all guards.
set -euo pipefail

project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
package_dir="$project_dir/handoff/slo-host01-20261011-local-supplement-03"

command -v timeout >/dev/null

launch_one() {
  local application="$1"
  shift
  # Refuse consumed allocations before prompting or creating new campaign state.
  python3 -B "$package_dir/runtime/prelaunch_local_supplement.py" \
    --application "$application" "$@"
  echo "Authenticate sudo for $application before its allocation starts. A later campaign may need another password."
  timeout --foreground 300s sudo -v
  bash "$package_dir/start_local_supplement.sh" "$application" "$@"
}

# Go includes setup once. Any nonzero exit stops the wrapper and preserves evidence.
launch_one Go "$@"
# Refresh authentication after the long Go campaign, before allocating NGINX.
launch_one NGINX "$@"
