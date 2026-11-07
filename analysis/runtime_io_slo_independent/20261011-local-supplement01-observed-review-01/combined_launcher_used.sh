#!/usr/bin/env bash
# Human external launch only. The sealed per-service launchers enforce all guards.
set -euo pipefail

project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
package_dir="$project_dir/handoff/slo-host01-20261011-local-supplement-03"

# Go includes fresh setup. Its nonzero exit stops this wrapper, preserving evidence.
bash "$package_dir/start_local_supplement.sh" Go "$@"
# Successful Go closes before NGINX; the NGINX launcher never repeats setup.
bash "$package_dir/start_local_supplement.sh" NGINX "$@"
