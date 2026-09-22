#!/usr/bin/env bash
set -euo pipefail

WORKSPACE="/home/Aditya/Desktop/Research_project/cpu-quota-tail-latency"
RUN_SINGLE="$WORKSPACE/scripts/run_single.sh"
OUT_DIR="$WORKSPACE/results/preflight"
mkdir -p "$OUT_DIR"

echo "=========================================================="
echo "  Executing Section 11 Pre-Flight Sanity Checks"
echo "=========================================================="

PASSED=0
TOTAL_CHECKS=7

# Check 1: Mapping to cpu.max
echo ""
echo "[Check 1/7] Verifying period/quota mapping to cgroup v2 cpu.max..."
docker run -d --rm --name pf_cgroup --cpuset-cpus="2,4" --cpu-period=100000 --cpu-quota=50000 research-service:latest >/dev/null
PID=$(docker inspect --format '{{.State.Pid}}' pf_cgroup)
CG_REL=$(cat /proc/"$PID"/cgroup | cut -d: -f3)
MAX_VAL=$(cat /sys/fs/cgroup"$CG_REL"/cpu.max)
docker rm -f pf_cgroup >/dev/null
if [[ "$MAX_VAL" == "50000 100000" ]]; then
  echo "  PASS: cpu.max is correctly set to '$MAX_VAL'"
  PASSED=$((PASSED + 1))
else
  echo "  FAIL: Expected '50000 100000', got '$MAX_VAL'"
fi

# Check 2: Ancestor cgroup constraints and cpu.max.burst
echo ""
echo "[Check 2/7] Verifying ancestor cgroup limits and cpu.max.burst..."
BURST=$(cat /sys/fs/cgroup/system.slice/cpu.max.burst 2>/dev/null || echo "N/A")
SLICE_MAX=$(cat /sys/fs/cgroup/system.slice/cpu.max 2>/dev/null || echo "N/A")
if [[ "$BURST" == "0" && "$SLICE_MAX" == "max 100000" ]]; then
  echo "  PASS: system.slice cpu.max.burst is 0 and cpu.max is uncapped ($SLICE_MAX)"
  PASSED=$((PASSED + 1))
else
  echo "  FAIL: Ancestor limit detected: max=$SLICE_MAX burst=$BURST"
fi

# Check 3: Unlimited baseline throttling
echo ""
echo "[Check 3/7] Verifying unlimited baseline produces 0% throttling..."
$RUN_SINGLE --run-id pf_unlim --period-us 0 --quota-us 0 --workers 1 --pattern steady --rate 80 --warmup-sec 3 --duration-sec 10 --output-json "$OUT_DIR/pf_unlim.json" >/dev/null
THROTTLED=$(python3 -c "import json; d=json.load(open('$OUT_DIR/pf_unlim.json')); print(d['cgroup_metrics']['delta_nr_throttled'])")
if [[ "$THROTTLED" -eq 0 ]]; then
  echo "  PASS: Unlimited baseline throttled periods = 0"
  PASSED=$((PASSED + 1))
else
  echo "  FAIL: Unlimited baseline had $THROTTLED throttled periods"
fi

# Check 4: Throttling escalation under 10ms period
echo ""
echo "[Check 4/7] Verifying throttling escalation under 10ms period (5ms quota)..."
$RUN_SINGLE --run-id pf_p10 --period-us 10000 --quota-us 5000 --workers 1 --pattern steady --rate 80 --warmup-sec 3 --duration-sec 10 --output-json "$OUT_DIR/pf_p10.json" >/dev/null
P10_THROTTLED=$(python3 -c "import json; d=json.load(open('$OUT_DIR/pf_p10.json')); print(d['cgroup_metrics']['delta_nr_throttled'])")
if [[ "$P10_THROTTLED" -gt 0 ]]; then
  echo "  PASS: 10ms period triggered $P10_THROTTLED throttling events"
  PASSED=$((PASSED + 1))
else
  echo "  FAIL: 10ms period had 0 throttling events"
fi

# Check 5: Load generator CPU utilization on Cores 0-1
echo ""
echo "[Check 5/7] Verifying load generator utilization on Cores 0-1 remains well below 100%..."
CORE01_UTIL=$(python3 -c "import json; d=json.load(open('$OUT_DIR/pf_p10.json')); print(d['environment_metrics']['mean_util_core01_pct'])")
echo "  Measured Core 0-1 average utilization: ${CORE01_UTIL}%"
IS_OK=$(python3 -c "print(1 if float('$CORE01_UTIL') < 50.0 else 0)")
if [[ "$IS_OK" -eq 1 ]]; then
  echo "  PASS: Load generator utilization on Cores 0-1 is safely below 50%"
  PASSED=$((PASSED + 1))
else
  echo "  FAIL: Core 0-1 utilization too high: ${CORE01_UTIL}%"
fi

# Check 6: Zero application errors or drops at test rates
echo ""
echo "[Check 6/7] Verifying zero dropped or failed requests under 80 rps..."
DROPS=$(python3 -c "import json; d=json.load(open('$OUT_DIR/pf_p10.json')); print(d['loadgen_metrics']['total_503'] + d['loadgen_metrics']['total_errors'] + d['loadgen_metrics']['client_dropped'])")
if [[ "$DROPS" -eq 0 ]]; then
  echo "  PASS: Zero errors, 503s, or socket drops"
  PASSED=$((PASSED + 1))
else
  echo "  FAIL: Detected $DROPS dropped or errored requests"
fi

# Check 7: Repeatability of p99 across 5 runs (Coefficient of Variation)
echo ""
echo "[Check 7/7] Verifying repeatability across 5 identical runs (CV of p99)..."
P99_VALS=()
for rep in {1..5}; do
  $RUN_SINGLE --run-id "pf_repeat_$rep" --period-us 100000 --quota-us 50000 --workers 1 --pattern steady --rate 80 --warmup-sec 2 --duration-sec 8 --output-json "$OUT_DIR/pf_rep_$rep.json" >/dev/null
  p99=$(python3 -c "import json; d=json.load(open('$OUT_DIR/pf_rep_$rep.json')); print(d['loadgen_metrics']['end_to_end_latency_summary']['p99_ms'])")
  P99_VALS+=("$p99")
done

CV_RESULT=$(python3 -c "
import math
vals = [float(x) for x in '${P99_VALS[*]}'.split()]
n = len(vals)
mean = sum(vals) / n
variance = sum((x - mean) ** 2 for x in vals) / (n - 1) if n > 1 else 0.0
std = math.sqrt(variance)
cv = (std / mean) * 100.0 if mean > 0 else 0.0
print(f'{mean:.2f} {std:.2f} {cv:.2f}')
")
read -r MEAN STD CV <<< "$CV_RESULT"
echo "  p99 runs: [${P99_VALS[*]}] ms"
echo "  Mean: ${MEAN} ms, Std: ${STD} ms, CV: ${CV}%"
IS_CV_OK=$(python3 -c "print(1 if float('$CV') < 10.0 else 0)")
if [[ "$IS_CV_OK" -eq 1 ]]; then
  echo "  PASS: Coefficient of variation is ${CV}% (< 10%)"
  PASSED=$((PASSED + 1))
else
  echo "  NOTE: CV is ${CV}% (exceeds 10% threshold; requires investigation/reporting)"
fi

echo ""
echo "=========================================================="
echo "  Pre-Flight Assertions Summary: $PASSED / $TOTAL_CHECKS Passed"
echo "=========================================================="

