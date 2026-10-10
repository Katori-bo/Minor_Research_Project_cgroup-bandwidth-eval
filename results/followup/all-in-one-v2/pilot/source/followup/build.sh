#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
# Go unit tests run inside each build before a binary can be produced.
docker build -t quota-followup-service:1 -f followup/service/Dockerfile followup/service
docker build -t quota-followup-loadgen:1 -f followup/loadgen/Dockerfile followup/loadgen
mkdir -p followup/bin
id=$(docker create quota-followup-loadgen:1 /loadgen)
trap 'docker rm "$id" >/dev/null 2>&1 || true' EXIT
docker cp "$id:/loadgen" followup/bin/loadgen
chmod +x followup/bin/loadgen
python3 followup/run.py seal-build
