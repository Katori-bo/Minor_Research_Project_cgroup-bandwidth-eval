#!/usr/bin/env bash
set -euo pipefail
TASK_PACKAGE_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd -- "$TASK_PACKAGE_ROOT"
if [[ $EUID -eq 0 || $# -ne 0 ]]; then
  echo 'Usage: bash setup_v31_host02.sh (normal user; no arguments)' >&2
  exit 1
fi
exec python3 -B scripts/host02_cli.py setup
