#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
# Go unit tests run inside each build before a binary can be produced.
docker build -t quota-diagnostic-service:6 -f diagnostic/service/Dockerfile diagnostic/service
docker build -t quota-diagnostic-loadgen:1 -f diagnostic/loadgen/Dockerfile diagnostic/loadgen
mkdir -p diagnostic/bin
id=$(docker create quota-diagnostic-loadgen:1 /loadgen)
trap 'docker rm "$id" >/dev/null 2>&1 || true' EXIT
docker cp "$id:/loadgen" diagnostic/bin/loadgen
chmod +x diagnostic/bin/loadgen
python3 diagnostic/run.py seal-build
