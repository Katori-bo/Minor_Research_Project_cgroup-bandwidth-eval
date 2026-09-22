# CPU Quota Period, Worker Concurrency, and Tail Latency under Linux cgroup v2

> **Restart protocol:** use [RESTART.md](RESTART.md) and `bash scripts/start_fresh.sh` for new measurements. The instructions below describe the legacy exploratory pipeline; its calibration and plots have known limitations. New v2 sessions preserve raw monitoring and request data, calibrate rates automatically, and exclude legacy results.

An experimental research framework evaluating how Linux cgroup v2 CPU bandwidth control (`cpu.max`) interacts with CFS period length, worker pool concurrency, and workload burstiness to affect request tail latency and throttling dynamics.

---

## 1. Repository Structure

```text
cpu-quota-tail-latency/
├── service/
│   ├── Dockerfile                  # Pinned multi-stage Docker build
│   └── source/
│       ├── main.go                 # Synthetic Go HTTP service (bounded queue, worker pool)
│       └── go.mod
├── tools/
│   ├── loadgen/                    # Accountable open-loop Go load generator
│   │   ├── main.go                 # Persistent HTTP keep-alive, independent arrival schedule
│   │   └── bin/loadgen             # Statically compiled binary
│   └── wrk2/                       # Compiled wrk2 binary for cross-validation
├── scripts/
│   ├── check_environment.sh        # Captures host hardware, cgroups, topology, governor
│   ├── calibrate.sh                # Calibrates CPU iterations (~5ms) and 0.5-CPU capacity
│   ├── validate_preflight.sh       # Executes 7 pre-flight sanity checks
│   ├── run_single.sh               # Single trial execution protocol (warmup, snapshot, cooldown)
│   ├── run_pilot.sh                # Runs the 12-run pilot milestone suite
│   ├── run_matrix.sh               # Orchestrates randomized 300-run factorial matrix
│   └── monitor_host.py             # Background CPU utilization, frequency, and thermal sampler
├── configs/
│   ├── calibration_params.env      # Stored calibrated parameters (40,000 iterations, 50 & 80 rps)
│   └── experiment_matrix.csv       # Randomized 300-run experiment matrix (seed=42)
├── results/
│   ├── pilot/                      # Raw JSON trial results from pilot study
│   ├── raw/                        # Raw JSON trial results from matrix runs
│   ├── preflight/                  # Output logs from Section 11 preflight checks
│   ├── pilot_summary.csv           # Aggregated summary table of pilot results
│   └── processed/
│       └── summary.csv             # Aggregated summary table of matrix runs
├── analysis/
│   ├── analyze.py                  # Statistical aggregation, ANOVA, and plot generator
│   └── figures/                    # Generated publication figures (PNG/PDF)
│       ├── fig1_tail_latency_vs_period.png
│       ├── fig2_throttling_vs_period.png
│       └── fig3_worker_concurrency.png
├── metadata/
│   └── system-info.txt             # Comprehensive hardware and OS inventory
├── paper/
│   └── paper_draft.md              # Research manuscript with empirical findings
└── README.md
```

---

## 2. Hardware and Environment Partitioning

- **Host**: AMD Ryzen 5 5600H (6 cores / 12 threads), Arch Linux, Kernel 7.2.6-arch2-1, cgroup v2.
- **CPU Partitioning**:
  - **Cores 0–1 (`taskset -c 0,1`)**: Dedicated to operating system, background monitoring, and load generator.
  - **Cores 2 & 4 (`--cpuset-cpus="2,4"`)**: Allocated exclusively to the container under test (`research-service`). Logical CPUs 2 and 4 represent physical Core 1 and Core 2 (primary SMT threads), preventing L1/L2 cache and hyperthread contention.
- **cgroup v2 Verification**:
  - Root: `cgroup2fs`
  - Container slice: `system.slice/docker-<id>.scope/cpu.max`
  - Ancestor constraints: `system.slice/cpu.max.burst` is 0 and `cpu.max` is uncapped.

---

## 3. Step-by-Step Reproduction Guide

### Step 1: Check Environment and Record Topology
```bash
./scripts/check_environment.sh
cat metadata/system-info.txt
```

### Step 2: Calibrate Workload Iterations and Quota Capacity
```bash
./scripts/calibrate.sh
```
*Result*: Selected 40,000 iterations ($5.08\,\text{ms}$ unconstrained service latency). Calibrated 0.5-CPU sustainable capacity:
- Moderate load: **50 rps** (Steady: 50 rps; Bursty: 5s at 30 rps, 5s at 70 rps).
- High load: **80 rps** (Steady: 80 rps; Bursty: 5s at 60 rps, 5s at 100 rps).

### Step 3: Execute Section 11 Pre-Flight Assertions
```bash
./scripts/validate_preflight.sh
```
*Result*: **7 / 7 checks passed**, verifying:
1. Exact mapping to `cpu.max`.
2. Uncapped ancestor cgroups with zero burst.
3. Zero throttling on unlimited baseline.
4. Throttling escalation under 10 ms period.
5. Load generator overhead $<11\%$ on Cores 0–1.
6. Zero application-level drops or errors.
7. Repeatability of p99 across 5 runs with Coefficient of Variation = **$1.70\%$** ($<10\%$).

### Step 4: Run Pilot Study Milestone
```bash
./scripts/run_pilot.sh
```
Executes 12 targeted trials comparing 10 ms, 100 ms, and unlimited baseline across 1 and 4 workers under steady and bursty profiles.

### Step 5: Run Full 300-Run Factorial Matrix
```bash
# Execute a batch (e.g. first 20 runs)
./scripts/run_matrix.sh 20

# Or execute all 300 trials
./scripts/run_matrix.sh 0
```

### Step 6: Generate Analysis and Publication Figures
```bash
./venv/bin/python analysis/analyze.py results/pilot analysis/figures results/pilot_summary.csv
```

---

## 4. Key Empirical Findings

1. **CFS Period Sensitivity**:
   - Under an identical 0.5 CPU average allocation, a **100 ms period** experienced **0.0% throttling** at 80 rps, as the 50 ms quota budget comfortably accommodated consecutive 5 ms requests.
   - A **10 ms period** (5 ms quota) experienced **$2.95\% - 3.40\%$ throttled periods** and up to **292.6 ms** of cumulative throttle time, because a single request consumed the entire quota window.
2. **Worker Concurrency Escalation**:
   - Increasing worker pool concurrency from 1 to 4 under 10 ms period increased throttled periods by $+15.2\%$ and throttle duration by $+35.4\%$, as concurrent threads drained the quota faster within the period.
3. **Bursty Arrivals**:
   - Bursty traffic intensified tail latency under small periods, elevating p99 latency to 6.74 ms.
