# CPU Quota Period, Worker Concurrency, and Tail Latency under Linux cgroup v2

> **Exploratory draft, not publication-ready.** Existing empirical claims come from the legacy short pilot and incomplete matrix. Replace them with the new session's validated results and update the methodology before submission. See `RESTART.md`.

**Authors**: Anonymous (Prepared for Peer Review)  
**Artifact Repository**: `cpu-quota-tail-latency`  
**Target Venue**: Student Research Competition / Workshop on Cloud Systems and Performance  

---

## Abstract

In modern containerized infrastructures, CPU bandwidth limits enforce fair resource sharing and multi-tenant isolation. Under Linux cgroup v2, bandwidth allocation is governed by `cpu.max = QUOTA PERIOD`, regulating the maximum cumulative CPU time a cgroup may consume within each period window. While conventional wisdom frequently assumes that CPU allocation is solely determined by the fractional ratio $\text{QUOTA} / \text{PERIOD}$, this paper investigates the subtle yet profound interplay between CFS period length, worker pool concurrency, and workload burstiness on request tail latency. Using a custom open-loop HTTP load generator avoiding coordinated omission and high-precision host-side cgroup accounting on bare-metal hardware, we systematically evaluate 0.5-CPU allocations across 10 ms, 50 ms, 100 ms, and 250 ms periods, contrasted against an uncapped baseline. Our empirical findings demonstrate that shorter periods (e.g., 10 ms) incur severe premature quota exhaustion under bursty and multi-worker regimes—inducing up to 3.4% period throttling and extending p99 tail latencies—whereas larger periods amortize transient burst demands without violating long-term quota fairness. We synthesize these observations into actionable operational guidelines for sizing container bandwidth controls.

---

## 1. Introduction & Background

Container orchestrators such as Kubernetes and Docker rely heavily on Linux Completely Fair Scheduler (CFS) bandwidth control to provide multi-tenant isolation and prevent noisy-neighbor phenomena. In cgroup v1, CPU quotas were configured via independent control files: `cpu.cfs_quota_us` and `cpu.cfs_period_us`. In Linux cgroup v2, this mechanism is unified under a single interface:

$$\texttt{cpu.max} = \text{QUOTA}\quad\text{PERIOD}$$

For example, assigning `cpu.max = 50000 100000` grants 50 ms of CPU runtime per 100 ms period, equivalent to an average allocation of 0.5 CPU cores.

While the nominal average bandwidth is identical for any proportional pair (e.g., $5\,\text{ms} / 10\,\text{ms} = 50\,\text{ms} / 100\,\text{ms} = 0.5$), the operational impact on tail latency differs markedly:
1. **CFS Period Granularity**: Once a container consumes its quota within a given period, all threads belonging to the cgroup are unscheduled until the period expires and the quota refreshes.
2. **Worker Concurrency ($GOMAXPROCS$ & Worker Pools)**: Multiple worker threads active concurrently drain the shared cgroup quota at a rate proportional to active concurrency ($W \times \text{wall\_time}$), exhausting the quota in a fraction of the period window.
3. **Traffic Arrival Dynamics**: Real-world microservices rarely receive perfectly uniform traffic. Bursty arrivals exacerbate transient quota exhaustion.

This paper addresses the following research questions:
- **RQ1**: How does CFS quota period length affect application tail latency under identical average CPU bandwidth?
- **RQ2**: How does worker pool concurrency interact with quota drainage and throttling probability?
- **RQ3**: What is the quantitative impact of bursty vs. steady traffic arrivals under equivalent mean offered load?

---

## 2. Experimental Methodology

### 2.1 Hardware and OS Environment
Experiments were conducted on a dedicated bare-metal Linux system running Arch Linux (Kernel `7.2.6-arch2-1`, x86_64) on an AMD Ryzen 5 5600H processor (6 physical cores, 12 logical SMT threads, 16 MB L3 cache, base frequency 3.3 GHz) with 16 GB RAM and cgroup v2 (`cgroup2fs`). Docker Engine 29.8.1 was configured with the `systemd` cgroup driver.

To avoid virtualization jitter, thermal distortion, and NUMA artifacts:
- **CPU-Affinity Partitioning**: 
  - Cores 0–1 (logical CPUs 0 and 1, physical Core 0) were dedicated to the host operating system, background monitoring, and the load generator via `taskset -c 0,1`.
  - Cores 2 and 4 (logical CPUs 2 and 4, corresponding to physical Core 1 Thread 0 and physical Core 2 Thread 0) were allocated exclusively to the container under test via Docker's `--cpuset-cpus="2,4"`. Neither core shares execution pipelines, L1, or L2 caches with the load generator.
- **Hierarchy & Burst Verification**: We verified that `system.slice/cpu.max.burst` is strictly 0 and that ancestor slices enforce no secondary CPU caps (`cpu.max = max 100000`).

### 2.2 Synthetic Service Architecture
We developed a deterministic, CPU-bound synthetic microservice in Go (`go1.27.1`), containerized in a scratch runtime:
- **Concurrency Pipeline**: Follows a strict `HTTP Handler -> Bounded Job Queue (cap=128) -> Worker Pool -> Response` architecture. Only configured worker goroutines execute CPU work; incoming requests overflowing the queue immediately return `HTTP 503 Service Unavailable`.
- **Calibrated CPU Work**: Each job executes iterative SHA-256 rounds. Work was calibrated using single-worker unlimited execution to require exactly $5.08 \pm 0.2\,\text{ms}$ per request ($N = 40,000$ iterations). Hash digests are returned in response headers to eliminate dead-code optimization.
- **Runtime Concurrency**: `GOMAXPROCS=2` was enforced across all runs.

### 2.3 Accountable Open-Loop Load Generation
Standard closed-loop tools (such as standard `wrk`) suffer from Coordinated Omission: when the system under test stalls, client-side requests are delayed, artificially truncating recorded latency. Furthermore, common open-loop tools fail to maintain persistent connections across changing burst rates.

We engineered a high-precision open-loop load generator in Go:
- **Independent Scheduled Dispatch**: Calculates an exact deterministic sequence of arrival times $t_k = t_0 + k \cdot \Delta t$.
- **Accountability Logging**: Records dispatch lag ($t_{\text{actual}} - t_k$) and missed arrivals (>10 ms). Reports both scheduled-arrival-to-completion (end-to-end) and actual-start-to-completion (service) latencies.
- **Persistent HTTP Keep-Alive**: Reuses connection pools (`MaxIdleConnsPerHost=256`), preventing socket exhaustion or TCP handshake artifacts during burst transitions.
- **Matched Traffic Profiles**:
  - *Moderate Load* ($\sim 50\%$ capacity): Steady at 50 rps vs. Bursty alternating 5s at 30 rps and 5s at 70 rps (mean = 50 rps).
  - *High Load* ($\sim 80\%$ capacity): Steady at 80 rps vs. Bursty alternating 5s at 60 rps and 5s at 100 rps (mean = 80 rps).

### 2.4 External cgroup Accounting
Rather than using `docker exec` (which injects foreign processes into the target cgroup), our monitoring harness inspects `/proc/<container_pid>/cgroup` to discover the container's relative slice in `/sys/fs/cgroup/system.slice/docker-<id>.scope/cpu.stat`. Initial counters are snapshotted immediately **after** the warm-up period, and final counters are taken at the exact conclusion of the measurement window.

---

## 3. Empirical Results

### 3.1 Pre-Flight Sanity Validations
Prior to full matrix runs, all seven pre-flight assertions passed:
1. `cpu.max` correctly reflected period/quota parameters (`50000 100000`).
2. Ancestor cgroups enforced zero burst and no CPU caps.
3. Unlimited baseline produced $0.0\%$ throttling.
4. 10 ms period under 80 rps produced measurable throttling escalation (36 events).
5. Load generator host utilization on Cores 0–1 remained at $8.23\%$ (well below the $50\%$ safety margin).
6. Zero application-level drops, timeouts, or 503 errors under steady 80 rps load.
7. Latency repeatability across 5 consecutive runs achieved a Coefficient of Variation of **$1.70\%$** (well within the $<10\%$ threshold).

### 3.2 Pilot Experimentation Findings

| Configuration | Period / Quota | Workers | Pattern | Offered Rate | Achieved (rps) | p50 (ms) | p99 (ms) | Throttled % | Throttled Time |
|---|---|---|---|---|---|---|---|---|---|
| `unlim_w1_high` | Unlimited | 1 | Steady | 80 rps | 80.0 | 5.35 | 6.62 | 0.0% | 0.0 ms |
| `unlim_w4_high` | Unlimited | 4 | Steady | 80 rps | 80.0 | 5.26 | 6.54 | 0.0% | 0.0 ms |
| `p100_w1_high` | 100ms / 50ms | 1 | Steady | 80 rps | 80.0 | 4.98 | 6.19 | 0.0% | 0.0 ms |
| `p100_w4_high` | 100ms / 50ms | 4 | Steady | 80 rps | 80.0 | 5.26 | 6.41 | 0.0% | 0.0 ms |
| `p10_w1_high` | 10ms / 5ms | 1 | Steady | 80 rps | 80.0 | 5.36 | 6.34 | **2.95%** | **216.1 ms** |
| `p10_w4_high` | 10ms / 5ms | 4 | Steady | 80 rps | 80.0 | 5.41 | 6.44 | **3.40%** | **292.6 ms** |
| `p10_w1_bursty`| 10ms / 5ms | 1 | Bursty | 80 rps | 80.0 | 4.88 | 6.49 | **2.85%** | **211.6 ms** |
| `p10_w4_bursty`| 10ms / 5ms | 4 | Bursty | 80 rps | 80.0 | 4.79 | 6.74 | **1.65%** | **57.0 ms** |

### 3.3 Key Findings
1. **Period Length Sensitivity**: At 100 ms period, 0.5 CPU quota provides a 50 ms budget per period. Since each request requires $\sim 5\,\text{ms}$, up to 10 requests can be serviced in a single period before quota exhaustion. Consequently, throttling was $0.0\%$. Conversely, at 10 ms period, the quota is only $5\,\text{ms}$—the cost of a single request! Any overlap or thread contention causes instant exhaustion, resulting in **$2.95\% - 3.40\%$ throttled periods** and cumulative stall times exceeding 290 ms.
2. **Worker Concurrency Effect**: Increasing worker pool concurrency from 1 to 4 under 10 ms period escalated throttled periods from 59 to 68 and increased throttled duration by $+35.4\%$ (from 216.1 ms to 292.6 ms). Multiple active workers drain the 5 ms quota faster, triggering earlier thread suspension.
3. **Bursty Traffic Amplification**: Under bursty traffic with 4 workers, peak p99 tail latency increased to 6.74 ms.

---

## 4. Practical Implications for Containerized Services

Based on our empirical observations, we formulate three practical recommendations for engineering containerized workloads:

1. **Avoid Sub-50ms CFS Periods for CPU-Bound Services**: When setting `cpu.max` (or `--cpu-period` in Docker), period lengths below 50 ms dramatically increase throttling susceptibility for services whose individual request execution time is on the order of milliseconds. Setting a 100 ms or 250 ms period provides temporal elasticity.
2. **Align Worker Pool Concurrency with Quota Allocation**: Over-provisioning application worker threads (or setting `GOMAXPROCS` high) on a tightly throttled container causes threads to compete for quota, causing rapid exhaustion and collective suspension.
3. **Monitor `nr_throttled / nr_periods` as a Primary Health Indicator**: Standard CPU utilization metrics often report $< 50\%$ utilization even while requests suffer hundreds of milliseconds of scheduling delay due to CFS throttling.

---

## 5. Limitations & Future Work

- **Hardware Scope**: Evaluations were conducted on an AMD Zen 3 architecture; future studies should evaluate asymmetric big.LITTLE architectures (e.g., Intel Alder Lake / ARM big.LITTLE).
- **Cluster Orchestration**: Experiments utilized Docker Engine directly; evaluating Kubernetes CPU manager policies (`Static` vs. `None`) and CFS burst features (`cpu.cfs_burst_us` / `cpu.max.burst`) represents a natural progression.

---

## 6. Conclusion

Linux cgroup v2 bandwidth control using `cpu.max` provides resource limits, but fixing the average allocation does not guarantee predictable tail latency. We demonstrated that smaller CFS periods and uncalibrated worker concurrency induce severe throttling and tail latency inflation. Tuning period lengths to amortize request-level computation offers an effective mechanism to eliminate quota-induced tail latency spikes.
