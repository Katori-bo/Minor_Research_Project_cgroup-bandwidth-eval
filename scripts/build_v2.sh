#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$ROOT"
docker build -t research-service:study-v2 service
mkdir -p tools/loadgen/bin
docker run --rm --user "$(id -u):$(id -g)" \
  -e GOCACHE=/tmp/go-cache -e GOPATH=/tmp/go-path \
  -v "$ROOT/tools/loadgen:/src" -w /src golang:1.26.1-alpine \
  sh -c 'gofmt -w main.go main_test.go && go test ./... && go vet ./... && CGO_ENABLED=0 go build -o bin/loadgen .'
docker run --rm --user "$(id -u):$(id -g)" \
  -e GOCACHE=/tmp/go-cache -e GOPATH=/tmp/go-path \
  -v "$ROOT/service/source:/src" -w /src golang:1.26.1-alpine \
  sh -c 'go test ./... && go vet ./...'
"$ROOT/venv/bin/python" -m unittest discover -s "$ROOT/tests" -p test_experiment.py -v
"$ROOT/venv/bin/python" -m unittest discover -s "$ROOT/tests" -p test_environment.py -v
"$ROOT/venv/bin/python" -m unittest discover -s "$ROOT/tests" -p test_analysis.py -v
"$ROOT/venv/bin/python" "$ROOT/tests/test_loadgen_integration.py" -v
