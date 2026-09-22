#!/usr/bin/env bash
set -euo pipefail

WORKSPACE="/home/Aditya/Desktop/Research_project/cpu-quota-tail-latency"
LOADGEN="$WORKSPACE/tools/loadgen/bin/loadgen"
MONITOR="$WORKSPACE/scripts/monitor_host.py"
PORT=8080
TARGET_URL="http://127.0.0.1:$PORT/work?iterations=40000"

# Default arguments
RUN_ID="test_$(date +%s)"
PERIOD_US=0
QUOTA_US=0
WORKERS=1
PATTERN="steady"
RATE=50
BURST_LOW=30
BURST_HIGH=70
BURST_PERIOD="10s"
WARMUP_SEC=10
DURATION_SEC=30
OUTPUT_JSON=""
TRIAL=1
SEED=42

while [[ $# -gt 0 ]]; do
  case "$1" in
    --run-id) RUN_ID="$2"; shift 2 ;;
    --period-us) PERIOD_US="$2"; shift 2 ;;
    --quota-us) QUOTA_US="$2"; shift 2 ;;
    --workers) WORKERS="$2"; shift 2 ;;
    --pattern) PATTERN="$2"; shift 2 ;;
    --rate) RATE="$2"; shift 2 ;;
    --burst-low) BURST_LOW="$2"; shift 2 ;;
    --burst-high) BURST_HIGH="$2"; shift 2 ;;
    --burst-period) BURST_PERIOD="$2"; shift 2 ;;
    --warmup-sec) WARMUP_SEC="$2"; shift 2 ;;
    --duration-sec) DURATION_SEC="$2"; shift 2 ;;
    --output-json) OUTPUT_JSON="$2"; shift 2 ;;
    --trial) TRIAL="$2"; shift 2 ;;
    --seed) SEED="$2"; shift 2 ;;
    *) echo "Unknown option $1"; exit 1 ;;
  esac
done

if [[ -z "$OUTPUT_JSON" ]]; then
  OUTPUT_JSON="$WORKSPACE/results/raw/${RUN_ID}.json"
fi

mkdir -p "$(dirname "$OUTPUT_JSON")"
TMP_DIR=$(mktemp -d /tmp/trial_run_XXXXXX)
trap 'rm -rf "$TMP_DIR"; docker rm -f research-service >/dev/null 2>&1 || true' EXIT

# Clean up any lingering container
docker rm -f research-service >/dev/null 2>&1 || true

DOCKER_ARGS=(
  -d --rm
  --name research-service
  --cpuset-cpus="2,4"
  -e WORKERS="$WORKERS"
  -e QUEUE_SIZE=128
  -e DEFAULT_ITERATIONS=40000
  -p "$PORT:8080"
)

if [[ "$PERIOD_US" -gt 0 && "$QUOTA_US" -gt 0 ]]; then
  DOCKER_ARGS+=(--cpu-period="$PERIOD_US" --cpu-quota="$QUOTA_US")
fi

# 1. Start Container
docker run "${DOCKER_ARGS[@]}" research-service:latest >/dev/null

# 2. Wait for health check readiness
READY=0
for i in {1..30}; do
  if curl -s -f "http://127.0.0.1:$PORT/health" >/dev/null 2>&1; then
    READY=1
    break
  fi
  sleep 0.2
done

if [[ "$READY" -ne 1 ]]; then
  echo "ERROR: Service failed to reach healthy state" >&2
  exit 1
fi

# 3. Discover host PID and relative cgroup path
CONTAINER_PID=$(docker inspect --format '{{.State.Pid}}' research-service)
CG_REL=$(cat /proc/"$CONTAINER_PID"/cgroup | cut -d: -f3)
CG_DIR="/sys/fs/cgroup$CG_REL"

if [[ ! -f "$CG_DIR/cpu.stat" ]]; then
  echo "ERROR: cgroup cpu.stat not found at $CG_DIR/cpu.stat" >&2
  exit 1
fi

# 4. Warm-up Phase
if [[ "$WARMUP_SEC" -gt 0 ]]; then
  WARMUP_ARGS=(
    -url "$TARGET_URL"
    -duration "${WARMUP_SEC}s"
    -pattern "$PATTERN"
    -concurrency 64
  )
  if [[ "$PATTERN" == "bursty" ]]; then
    WARMUP_ARGS+=(-burst-low "$BURST_LOW" -burst-high "$BURST_HIGH" -burst-period "$BURST_PERIOD")
  else
    WARMUP_ARGS+=(-rate "$RATE")
  fi

  taskset -c 0,1 "$LOADGEN" "${WARMUP_ARGS[@]}" >/dev/null 2>&1 || true
fi

# 5. Snapshot Initial Cgroup Counters (Immediately after warm-up)
INIT_STAT_FILE="$TMP_DIR/cgroup_init.stat"
cat "$CG_DIR/cpu.stat" > "$INIT_STAT_FILE"
T_START_EPOCH=$(date +%s%N)

# 6. Start Background Host Monitor
MONITOR_LOG="$TMP_DIR/monitor.json"
python3 "$MONITOR" --cgroup-path "$CG_REL" --interval 1.0 --output "$MONITOR_LOG" &
MON_PID=$!

# 7. Measurement Phase
LOADGEN_RAW="$TMP_DIR/loadgen_raw.json"
MEASURE_ARGS=(
  -url "$TARGET_URL"
  -duration "${DURATION_SEC}s"
  -pattern "$PATTERN"
  -concurrency 128
  -output "$LOADGEN_RAW"
)
if [[ "$PATTERN" == "bursty" ]]; then
  MEASURE_ARGS+=(-burst-low "$BURST_LOW" -burst-high "$BURST_HIGH" -burst-period "$BURST_PERIOD")
else
  MEASURE_ARGS+=(-rate "$RATE")
fi

taskset -c 0,1 "$LOADGEN" "${MEASURE_ARGS[@]}" > "$TMP_DIR/loadgen_stdout.txt" 2>&1

# 8. Snapshot Final Cgroup Counters (Immediately after measurement)
T_END_EPOCH=$(date +%s%N)
FINAL_STAT_FILE="$TMP_DIR/cgroup_final.stat"
cat "$CG_DIR/cpu.stat" > "$FINAL_STAT_FILE"

# Stop background monitor
kill -INT "$MON_PID" 2>/dev/null || true
wait "$MON_PID" 2>/dev/null || true

# 9. Stop and Remove Container
docker rm -f research-service >/dev/null 2>&1 || true

# 10. Process and Aggregate Run Data via Python
python3 - << EOF
import json
import os

def parse_stat(path):
    d = {}
    with open(path, 'r') as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) == 2:
                d[parts[0]] = int(parts[1])
    return d

init_stat = parse_stat("$INIT_STAT_FILE")
final_stat = parse_stat("$FINAL_STAT_FILE")

delta_usage_usec = final_stat.get('usage_usec', 0) - init_stat.get('usage_usec', 0)
delta_nr_periods = final_stat.get('nr_periods', 0) - init_stat.get('nr_periods', 0)
delta_nr_throttled = final_stat.get('nr_throttled', 0) - init_stat.get('nr_throttled', 0)
delta_throttled_usec = final_stat.get('throttled_usec', 0) - init_stat.get('throttled_usec', 0)

throttling_fraction = (delta_nr_throttled / float(delta_nr_periods)) if delta_nr_periods > 0 else 0.0
actual_duration_sec = ($T_END_EPOCH - $T_START_EPOCH) / 1e9
cpu_usage_cores = (delta_usage_usec / 1e6) / actual_duration_sec if actual_duration_sec > 0 else 0.0

with open("$LOADGEN_RAW", 'r') as f:
    loadgen_data = json.load(f)

monitor_data = []
if os.path.exists("$MONITOR_LOG"):
    try:
        with open("$MONITOR_LOG", 'r') as f:
            monitor_data = json.load(f)
    except Exception:
        pass

# Compute average temperatures and core utilizations
temps = []
core01_utils = []
core24_utils = []

for m in monitor_data:
    t_vals = list(m.get('temps_c', {}).values())
    if t_vals:
        temps.append(sum(t_vals) / len(t_vals))
    u = m.get('cpu_util_pct', {})
    c0 = u.get('cpu0', 0) + u.get('cpu1', 0)
    c1 = u.get('cpu2', 0) + u.get('cpu4', 0)
    core01_utils.append(c0 / 2.0)
    core24_utils.append(c1 / 2.0)

mean_temp = sum(temps)/len(temps) if temps else 0.0
max_temp = max(temps) if temps else 0.0
mean_util_core01 = sum(core01_utils)/len(core01_utils) if core01_utils else 0.0
mean_util_core24 = sum(core24_utils)/len(core24_utils) if core24_utils else 0.0

full_record = {
    "run_id": "$RUN_ID",
    "trial": int("$TRIAL"),
    "seed": int("$SEED"),
    "timestamp_start": $T_START_EPOCH / 1e9,
    "timestamp_end": $T_END_EPOCH / 1e9,
    "config": {
        "period_us": int("$PERIOD_US"),
        "quota_us": int("$QUOTA_US"),
        "is_unlimited": (int("$PERIOD_US") == 0),
        "workers": int("$WORKERS"),
        "pattern": "$PATTERN",
        "rate": float("$RATE"),
        "burst_low": float("$BURST_LOW"),
        "burst_high": float("$BURST_HIGH"),
        "burst_period_sec": float("$BURST_PERIOD".rstrip('s')),
        "warmup_sec": int("$WARMUP_SEC"),
        "duration_sec": int("$DURATION_SEC")
    },
    "cgroup_metrics": {
        "delta_usage_usec": delta_usage_usec,
        "delta_nr_periods": delta_nr_periods,
        "delta_nr_throttled": delta_nr_throttled,
        "delta_throttled_usec": delta_throttled_usec,
        "throttling_fraction": throttling_fraction,
        "cpu_usage_cores": cpu_usage_cores
    },
    "loadgen_metrics": loadgen_data,
    "environment_metrics": {
        "mean_temp_c": round(mean_temp, 2),
        "max_temp_c": round(max_temp, 2),
        "mean_util_core01_pct": round(mean_util_core01, 2),
        "mean_util_core24_pct": round(mean_util_core24, 2)
    }
}

with open("$OUTPUT_JSON", 'w') as f:
    json.dump(full_record, f, indent=2)

print(f"Run {full_record['run_id']} finished cleanly:")
print(f"  Throughput: {loadgen_data['achieved_throughput_rps']:.1f} rps | Success: {loadgen_data['total_success']} | 503: {loadgen_data['total_503']}")
print(f"  Latency E2E: p50={loadgen_data['end_to_end_latency_summary']['p50_ms']:.2f}ms p95={loadgen_data['end_to_end_latency_summary']['p95_ms']:.2f}ms p99={loadgen_data['end_to_end_latency_summary']['p99_ms']:.2f}ms")
print(f"  Cgroup: CPU={cpu_usage_cores:.3f} cores | Throttled={delta_nr_throttled}/{delta_nr_periods} ({throttling_fraction*100:.1f}%) | ThrottledTime={delta_throttled_usec/1e3:.1f}ms")
print(f"  Env: Temp={mean_temp:.1f}C (max {max_temp:.1f}C) | Core0-1 util={mean_util_core01:.1f}% | Core2-4 util={mean_util_core24:.1f}%")
EOF

# Thermal Cooldown Check
TEMP_RAW=$(cat /sys/class/thermal/thermal_zone0/temp 2>/dev/null || echo "50000")
TEMP_C=$(( TEMP_RAW / 1000 ))
if [[ "$TEMP_C" -gt 65 ]]; then
  echo "Thermal guard: current temp is ${TEMP_C}°C (>65°C), cooling down 10s..."
  sleep 10
else
  sleep 3
fi

