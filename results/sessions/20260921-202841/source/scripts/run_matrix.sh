#!/usr/bin/env bash
set -euo pipefail

# The original implementation is retained below for historical reference only.
echo "The legacy matrix runner is retired. Use: bash scripts/start_fresh.sh" >&2
exit 2

WORKSPACE="/home/Aditya/Desktop/Research_project/cpu-quota-tail-latency"
CONFIG_FILE="$WORKSPACE/configs/experiment_matrix.csv"
RUN_SINGLE="$WORKSPACE/scripts/run_single.sh"
RAW_RESULTS_DIR="$WORKSPACE/results/raw"
SEED=42

mkdir -p "$WORKSPACE/configs" "$RAW_RESULTS_DIR" "$WORKSPACE/results/processed"

echo "=========================================================="
echo "  Generating Full 300-Run Factorial Experiment Matrix"
echo "=========================================================="

python3 - << EOF
import csv
import random

seed = $SEED
random.seed(seed)

periods_quotas = [
    (10000, 5000),      # 10ms
    (50000, 25000),     # 50ms
    (100000, 50000),    # 100ms
    (250000, 125000),   # 250ms
]
baseline = [(0, 0)]     # Unlimited

workers_list = [1, 2, 4]
loads = [
    ("mod", 50.0, 30.0, 70.0),
    ("high", 80.0, 60.0, 100.0)
]
patterns = ["steady", "bursty"]
repetitions = 5

rows = []

# 1. Quota configurations (240 runs)
for period, quota in periods_quotas:
    for workers in workers_list:
        for load_name, rate, b_low, b_high in loads:
            for pattern in patterns:
                for rep in range(1, repetitions + 1):
                    p_ms = period // 1000
                    run_id = f"p{p_ms}_w{workers}_{load_name}_{pattern}_rep{rep}"
                    rows.append({
                        "run_id": run_id,
                        "trial": rep,
                        "period_us": period,
                        "quota_us": quota,
                        "workers": workers,
                        "pattern": pattern,
                        "rate": rate,
                        "burst_low": b_low,
                        "burst_high": b_high,
                        "burst_period_sec": 10
                    })

# 2. Baseline configurations (60 runs)
for period, quota in baseline:
    for workers in workers_list:
        for load_name, rate, b_low, b_high in loads:
            for pattern in patterns:
                for rep in range(1, repetitions + 1):
                    run_id = f"unlim_w{workers}_{load_name}_{pattern}_rep{rep}"
                    rows.append({
                        "run_id": run_id,
                        "trial": rep,
                        "period_us": period,
                        "quota_us": quota,
                        "workers": workers,
                        "pattern": pattern,
                        "rate": rate,
                        "burst_low": b_low,
                        "burst_high": b_high,
                        "burst_period_sec": 10
                    })

print(f"Generated {len(rows)} total experiment configurations.")
random.shuffle(rows)

fieldnames = ["run_id", "trial", "period_us", "quota_us", "workers", "pattern", "rate", "burst_low", "burst_high", "burst_period_sec"]
with open("$CONFIG_FILE", 'w', newline='\n') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)

print(f"Matrix written to $CONFIG_FILE with randomization seed {seed}.")
EOF

# Parse optional arguments
MAX_RUNS=${1:-0}
START_INDEX=${2:-1}

TOTAL_PLANNED=$(wc -l < "$CONFIG_FILE")
TOTAL_PLANNED=$((TOTAL_PLANNED - 1))

echo ""
echo "Experiment matrix ready: $TOTAL_PLANNED trials planned."
if [[ "$MAX_RUNS" -gt 0 ]]; then
  echo "Executing batch of up to $MAX_RUNS trials starting from index $START_INDEX..."
fi

CURRENT_INDEX=0
EXECUTED_COUNT=0

# Read CSV skipping header, stripping any carriage return
tail -n +2 "$CONFIG_FILE" | tr -d '\r' | while IFS=, read -r run_id trial period_us quota_us workers pattern rate burst_low burst_high burst_period_sec; do
  CURRENT_INDEX=$((CURRENT_INDEX + 1))

  if [[ "$CURRENT_INDEX" -lt "$START_INDEX" ]]; then
    continue
  fi

  if [[ "$MAX_RUNS" -gt 0 && "$EXECUTED_COUNT" -ge "$MAX_RUNS" ]]; then
    echo "Reached target batch size ($MAX_RUNS runs). Stopping."
    break
  fi

  OUT_JSON="$RAW_RESULTS_DIR/${run_id}.json"
  if [[ -f "$OUT_JSON" ]]; then
    echo "[$CURRENT_INDEX/$TOTAL_PLANNED] Skipping already completed run: $run_id"
    continue
  fi

  echo ""
  echo ">>> [$CURRENT_INDEX/$TOTAL_PLANNED] Executing $run_id: period=${period_us}us quota=${quota_us}us workers=$workers pattern=$pattern rate=$rate"
  
  $RUN_SINGLE \
    --run-id "$run_id" \
    --period-us "$period_us" \
    --quota-us "$quota_us" \
    --workers "$workers" \
    --pattern "$pattern" \
    --rate "$rate" \
    --burst-low "$burst_low" \
    --burst-high "$burst_high" \
    --burst-period "${burst_period_sec}s" \
    --warmup-sec 5 \
    --duration-sec 20 \
    --trial "$trial" \
    --seed "$SEED" \
    --output-json "$OUT_JSON"

  EXECUTED_COUNT=$((EXECUTED_COUNT + 1))
done

echo ""
echo "Updating analysis and publication figures..."
$WORKSPACE/venv/bin/python $WORKSPACE/analysis/analyze.py \
  "$RAW_RESULTS_DIR" \
  "$WORKSPACE/analysis/figures" \
  "$WORKSPACE/results/processed/summary.csv"

echo "Batch execution complete!"
