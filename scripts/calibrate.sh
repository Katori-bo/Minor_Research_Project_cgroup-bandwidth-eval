#!/usr/bin/env bash
set -euo pipefail

echo "Legacy calibration is retired. Use: bash scripts/start_fresh.sh" >&2
exit 2

WORKSPACE="/home/Aditya/Desktop/Research_project/cpu-quota-tail-latency"
PORT=8080
TARGET="http://127.0.0.1:$PORT"

echo "=========================================================="
echo "  Calibrating Workload Iterations and 0.5-CPU Capacity"
echo "=========================================================="

# Ensure previous container is cleaned up
docker rm -f research-service 2>/dev/null || true

# 1. Start reference container: 1 worker, UNLIMITED quota, pinned to CPUs 2,4
echo "[1/4] Starting baseline container on CPUs 2,4 (1 worker, unlimited CPU)..."
docker run -d --rm --name research-service \
  --cpuset-cpus="2,4" \
  -e WORKERS=1 \
  -e QUEUE_SIZE=128 \
  -e DEFAULT_ITERATIONS=50000 \
  -p $PORT:8080 \
  research-service:latest

# Wait for health
echo "Waiting for service to be healthy..."
for i in {1..30}; do
  if curl -s -f "$TARGET/health" >/dev/null; then
    echo "Service is ready!"
    break
  fi
  sleep 0.5
done

# 2. Measure wall-clock latency across iterations
echo "[2/4] Testing iteration counts to achieve ~5 ms per request..."
BEST_ITER=50000
TARGET_MS=5.0
MIN_DIFF=9999.0

for iter in 20000 35000 50000 70000 85000 100000; do
  # Warm up 5 requests
  for _ in {1..5}; do
    curl -s "$TARGET/work?iterations=$iter" >/dev/null
  done

  # Measure 20 consecutive requests
  TOTAL_TIME=0
  for _ in {1..20}; do
    T_START=$(date +%s%N)
    curl -s "$TARGET/work?iterations=$iter" >/dev/null
    T_END=$(date +%s%N)
    DIFF=$(( (T_END - T_START) / 1000000 )) # in ms
    TOTAL_TIME=$(( TOTAL_TIME + (T_END - T_START) ))
  done
  AVG_MS=$(python3 -c "print(round($TOTAL_TIME / 20.0 / 1e6, 2))")
  echo "  iterations=$iter -> avg_latency=${AVG_MS}ms"

  DIFF_FROM_TARGET=$(python3 -c "print(abs($AVG_MS - $TARGET_MS))")
  IS_BETTER=$(python3 -c "print(1 if $DIFF_FROM_TARGET < $MIN_DIFF else 0)")
  if [ "$IS_BETTER" -eq 1 ]; then
    MIN_DIFF=$DIFF_FROM_TARGET
    BEST_ITER=$iter
  fi
done

echo "Selected calibrated iterations: $BEST_ITER (~5 ms per request)"

# Clean up baseline container
docker rm -f research-service >/dev/null 2>&1

# 3. Start 0.5-CPU throttled container to find sustainable capacity
echo ""
echo "[3/4] Testing capacity under 0.5-CPU quota (period=100ms, quota=50ms, 1 worker)..."
docker run -d --rm --name research-service \
  --cpuset-cpus="2,4" \
  --cpu-period=100000 \
  --cpu-quota=50000 \
  -e WORKERS=1 \
  -e QUEUE_SIZE=128 \
  -e DEFAULT_ITERATIONS=$BEST_ITER \
  -p $PORT:8080 \
  research-service:latest

sleep 3

# Test rates from 50 to 110 req/s using loadgen pinned to CPUs 0,1
echo "Ramping load with open-loop loadgen to identify 0.5-CPU saturation..."
LOADGEN="$WORKSPACE/tools/loadgen/bin/loadgen"
MAX_SUSTAINABLE_RPS=0

for rate in 50 70 85 95 105; do
  echo "Testing rate: $rate req/s (10 seconds)..."
  OUTPUT_JSON="/tmp/calib_rate_${rate}.json"
  taskset -c 0,1 $LOADGEN \
    -url "$TARGET/work?iterations=$BEST_ITER" \
    -rate "$rate" \
    -duration 10s \
    -pattern steady \
    -output "$OUTPUT_JSON" >/dev/null 2>&1

  SUCCESS=$(python3 -c "import json; d=json.load(open('$OUTPUT_JSON')); print(d['total_success'])")
  TOTAL=$(python3 -c "import json; d=json.load(open('$OUTPUT_JSON')); print(d['total_scheduled'])")
  DROPS=$(python3 -c "import json; d=json.load(open('$OUTPUT_JSON')); print(d['total_503'] + d['total_errors'] + d['client_dropped'])")
  P50=$(python3 -c "import json; d=json.load(open('$OUTPUT_JSON')); print(d['service_latency_summary']['p50_ms'])")
  P99=$(python3 -c "import json; d=json.load(open('$OUTPUT_JSON')); print(d['service_latency_summary']['p99_ms'])")
  ACHIEVED=$(python3 -c "import json; d=json.load(open('$OUTPUT_JSON')); print(round(d['achieved_throughput_rps'], 1))")

  echo "  Target=$rate rps: Achieved=$ACHIEVED rps, Success=$SUCCESS/$TOTAL, Drops/503=$DROPS, p50=${P50}ms, p99=${P99}ms"
  if [ "$DROPS" -eq 0 ]; then
    MAX_SUSTAINABLE_RPS=$rate
  fi
  rm -f "$OUTPUT_JSON"
done

docker rm -f research-service >/dev/null 2>&1

echo ""
echo "[4/4] Calibration summary:"
echo "  Calibrated iterations: $BEST_ITER"
echo "  Maximum clean sustainable rate under 0.5 CPU: ~$MAX_SUSTAINABLE_RPS rps"

# Calculate Moderate (~50%) and High (~80%) loads
MOD_RATE=$(python3 -c "print(int(round($MAX_SUSTAINABLE_RPS * 0.50 / 5.0) * 5))")
HIGH_RATE=$(python3 -c "print(int(round($MAX_SUSTAINABLE_RPS * 0.80 / 5.0) * 5))")

# Ensure sensible defaults if capacity is ~90-100 rps
if [ "$MOD_RATE" -lt 30 ]; then MOD_RATE=45; fi
if [ "$HIGH_RATE" -lt 60 ]; then HIGH_RATE=75; fi

# Matched burst rates with equal arithmetic mean
# Moderate: e.g. 50 -> low=30, high=70 (mean=50)
MOD_BURST_LOW=$(python3 -c "print($MOD_RATE - 20)")
MOD_BURST_HIGH=$(python3 -c "print($MOD_RATE + 20)")

# High: e.g. 75 -> low=50, high=100 (mean=75)
HIGH_BURST_LOW=$(python3 -c "print($HIGH_RATE - 25)")
HIGH_BURST_HIGH=$(python3 -c "print($HIGH_RATE + 25)")

CALIB_FILE="$WORKSPACE/configs/calibration_params.env"
cat << EOF > "$CALIB_FILE"
CALIBRATED_ITERATIONS=$BEST_ITER
MOD_RATE=$MOD_RATE
MOD_BURST_LOW=$MOD_BURST_LOW
MOD_BURST_HIGH=$MOD_BURST_HIGH
HIGH_RATE=$HIGH_RATE
HIGH_BURST_LOW=$HIGH_BURST_LOW
HIGH_BURST_HIGH=$HIGH_BURST_HIGH
EOF

echo "Saved calibration to $CALIB_FILE:"
cat "$CALIB_FILE"
