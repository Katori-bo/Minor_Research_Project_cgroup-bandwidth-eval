#!/usr/bin/env bash
set -euo pipefail

WORKSPACE="/home/Aditya/Desktop/Research_project/cpu-quota-tail-latency"
RUN_SINGLE="$WORKSPACE/scripts/run_single.sh"
PILOT_RESULTS="$WORKSPACE/results/pilot"
mkdir -p "$PILOT_RESULTS"

echo "=========================================================="
echo "  Starting Pilot Milestone Experiment Suite"
echo "=========================================================="

# Configurations: 10ms, 100ms, and Unlimited
# Workers: 1 and 4
# Traffic: Steady (50, 80 rps) and Bursty (50 rps mean: 30/70, 80 rps mean: 60/100)
# Duration: 20s (two complete 10s burst cycles), 5s warmup

configs=(
  # Period Quota Workers Pattern Rate Low High Name
  "100000 50000 1 steady 50 0 0 p100_w1_steady_mod"
  "100000 50000 1 bursty 50 30 70 p100_w1_bursty_mod"
  "100000 50000 1 steady 80 0 0 p100_w1_steady_high"
  "100000 50000 1 bursty 80 60 100 p100_w1_bursty_high"

  "100000 50000 4 steady 80 0 0 p100_w4_steady_high"
  "100000 50000 4 bursty 80 60 100 p100_w4_bursty_high"

  "10000 5000 1 steady 80 0 0 p10_w1_steady_high"
  "10000 5000 1 bursty 80 60 100 p10_w1_bursty_high"
  "10000 5000 4 steady 80 0 0 p10_w4_steady_high"
  "10000 5000 4 bursty 80 60 100 p10_w4_bursty_high"

  "0 0 1 steady 80 0 0 unlim_w1_steady_high"
  "0 0 4 steady 80 0 0 unlim_w4_steady_high"
)

TOTAL=${#configs[@]}
IDX=1

for cfg in "${configs[@]}"; do
  read -r period quota workers pattern rate low high name <<< "$cfg"
  echo ""
  echo ">>> [Pilot $IDX/$TOTAL] Running: $name (period=${period}us, quota=${quota}us, workers=$workers, pattern=$pattern, rate=$rate)"
  
  OUT="$PILOT_RESULTS/${name}.json"
  $RUN_SINGLE \
    --run-id "$name" \
    --period-us "$period" \
    --quota-us "$quota" \
    --workers "$workers" \
    --pattern "$pattern" \
    --rate "$rate" \
    --burst-low "$low" \
    --burst-high "$high" \
    --burst-period "10s" \
    --warmup-sec 5 \
    --duration-sec 20 \
    --output-json "$OUT"

  IDX=$((IDX + 1))
done

echo ""
echo "=========================================================="
echo "  Pilot Suite Complete! Results in $PILOT_RESULTS"
echo "=========================================================="

