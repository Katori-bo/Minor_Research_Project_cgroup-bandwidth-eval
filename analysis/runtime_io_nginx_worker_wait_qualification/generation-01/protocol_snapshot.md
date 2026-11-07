# Worker counter boundary and observer overhead qualification

10 October 2026. Frozen qualification-only design, selected after the known
historical results. No predictive fitting, discovery or confirmation collection
is included. Original sources, records, manuscript and friend-owned V31 remain
separate. This package must run from a normal-user external interactive terminal
with Codex/ChatGPT closed and the existing quiet-desktop checks satisfied.

## Apparatus and boundary phase

Reuse the sealed stock NGINX/client, one worker on CPU2, Q25 ms/P100 ms, existing
process/cgroup/source/watchdog/cleanup guards and 1 MiB gzip workload. P0 and the
prepared full policy baseline remain unchanged; sched_schedstats stays 0. Per-task
CONFIG_SCHED_INFO accounting is a distinct facility. No root policy lease or
perf/BPF observer is added. Sudo serves only the read-only observer inventory.

Two fresh services at 4/s and 8/s each acquire 25 warmup plus 20 target offers:
90 offers total, <=600 seconds including collection and cleanup reserve. Settle
10 seconds before service startup. Obtain initial stock status, ensure drain,
then wait 100 ms before the worker counter baseline. Every request in the
warmup window is the declared /compress request; the next status request occurs
after both counter snapshots (and the boundary phase's idle check).

Select the unique guarded single-thread child of the master by parent/start ticks,
executable digest and CPU2 affinity. Each snapshot records worker stat before,
schedstat and stat after, with monotonic timestamps. Require unchanged PID/start
ticks/parent, CPU2 and sleeping state at both identity reads. Sleeping here is
an operational quiescence check, not proof that every kernel counter is flushed.

The snapshots enclose the complete warmup client call, including launch, drain,
decode completion and polling. Increment CPU and runnable-wait counters; retain
scheduling count. Snapshot and provisional-feature serialization occur before
target collection. A later replay bundle merely copies these saved values and
does not provide future inputs. Two snapshots plus provisional calculation/write
are the live observer being qualified.

Fixed operational tolerances, chosen for engineering qualification rather than
fit from outcomes:

* Each identity/counter read bracket <=2 ms; total two-read, snapshot-write and
  provisional-feature calculation/write wall time <=20 ms.
* Positive worker CPU and scheduling-count increments; no reversals. At least
  one of the two boundary probes must witness a positive runnable-wait increment.
  Zero waiting alone is not interpreted as trustworthy transfer or inactive accounting.
* Isolated cgroup CPU duration and worker CPU duration differ by <=100 us per
  offered request (2.5 ms over the whole warmup). They have different scopes and
  slightly wider cgroup boundaries; this is an operational cross-check, not an
  independent wait-time oracle or exact per-request attribution.
* After warmup, wait 100 ms with no status request and take one extra diagnostic
  snapshot. Additional CPU and runnable-wait increments each <=10 us per original
  offered request (250 us total). No such third read or quiet delay is included
  in the overhead arms or proposed eventual two-snapshot observer.
* Stock request accounting verifies exactly 25 warmup offers plus one subsequent
  control request; exact source/process/response integrity and owned cleanup hold.

These checks can establish a bounded usable interval under this apparatus. They
do not validate absolute wait accuracy, every form of off-CPU delay, hidden
server queueing, scheduling exclusivity or prediction. If counters or boundaries
fail, stop; preserve the attempted cohort and do not relax margins or retry.

## Observer overhead phase

Only after both boundary services pass, acquire six fresh paired blocks. Each
block includes both rates, and an off/on pair per rate on separate fresh services.
Randomize rate order within block and arm order within pair once from a sealed
seed; do not redraw an unfavorable schedule. Each service acquires 25 warmup
and 300 subsequent target offers. All 24 services total 7,800 offers, <=2,700
seconds with a 120-second cleanup reserve. Per-service watchdog remains 120 s;
scheduled-span and phase reserves are checked before collection. Combined
qualification is 7,890 offers, <=10+45 minutes, plus preflight/inventory latency.

Both arms retain identical client/cgroup/process/policy/status controls, startup
and settling. On adds the two worker snapshots, their saved raw records and
provisional feature calculation/write around warmup. Off performs none of those
operations. Common worker-selection and process guards remain in both arms.
This compares the full proposed incremental observer, including its effect on
the following window, rather than just timing a read syscall.

Both arms also share the initial status, 100 ms quiet interval and selection
guard required by this newly specified boundary contract; their elapsed cost is
recorded separately. Equivalence assesses adding the two-snapshot observer to
that shared contract, not the absolute cost of all new boundary controls relative
to an older campaign. Future discovery must use and charge this same contract.

Deadline D remains 20.565395 ms. Retain throttling, overlaps and dispatch
observations. Failed offers remain all-offer misses, but any unsuccessful offer
also makes this operational mean-latency qualification technically incomplete:
there is no finite all-offer mean to substitute. Preserve failure records and
stop rather than compute a success-only equivalence claim. Complete corrupt
responses, identity changes, budget failures and unavailable counters likewise
stop without replacement. Do not remove a noisy paired block.

## Frozen overhead decision

For each rate, compute the six paired on-minus-off differences in:

1. All-offer target deadline-miss percentage: equivalence margin +/-2 pp.
2. Target mean complete-response time: equivalence margin +/-100 us.
3. Warmup mean complete-response time: equivalence margin +/-100 us.

The mean-time tests require all offered responses complete successfully. Margins
are declared engineering allowances: 2 pp reserves 3 pp of the earlier 5 pp
practical forecast-error tolerance; 100 us is about 0.5% of this deadline. This
allocation is not a theorem translating mean delay into miss-probability error,
so both quantities are checked separately.

Each conditional interval is mean +/-4.774*s/sqrt(6), df5. The multiplier is the
rounded-up 99.5% two-sided Student t critical value; six such intervals give
Bonferroni joint coverage >=97% only under approximately independent normal
paired block differences. One chronological host run does not establish those
assumptions. Require every interval entirely inside its specified margin.
Nonsignificance, equal means or an interval overlapping zero is insufficient.
Also require pooled target miss fractions at each rate within 10–90% so a
saturated deadline does not qualify the probability comparison trivially.

Status is observer_overhead_qualification_supported if all gates hold. Otherwise
a completed screen is observer_overhead_qualification_inconclusive. A technical
or boundary failure is qualification_stopped. Inconclusive is not proof the
observer is harmful, and supported is not proof it is harmless in other states.
Neither result licenses an automatic larger repeat, margin change, model fitting
or predictive experiment. The launcher always ends after qualification.

## Record, replay and next gate

Preparation seals source/protocol/tests, unchanged policy/switch baseline, boot/
topology and randomized schedule. Raw records include acquisition events,
decision receipt before target start, all client outcomes, identity-bracketed
counter text, boundary/cgroup checks, every observation and cleanup. Exact
all-offer and paired summaries replay from raw sealed records. Partial attempts
remain preserved with no overwrite/resume. Earlier boot qualification is not
counted as qualification of this observer.

A passing result permits considering a separately frozen discovery design for
worker CPU/wait changes versus subsequent transfer error. It does not establish
a reliability signal or novelty. Grant the ordinary state-conditioned comparator
the same measurements, probe budget and decision time in that future study.

Run once, after closing Codex and other task applications:

```bash
cd /home/Aditya/Desktop/Research_project/cpu-quota-tail-latency
bash diagnostic/start_nginx_worker_wait_qualification.sh
```

Read-only complete-result replay:

```bash
python3 -B diagnostic/nginx_worker_wait_study.py replay
```

Primary accounting sources: [scheduler counter definitions](https://docs.kernel.org/scheduler/sched-stats.html#proc-pid-schedstat),
[procfs exporter](https://raw.githubusercontent.com/torvalds/linux/master/fs/proc/base.c),
[CONFIG_SCHED_INFO availability](https://raw.githubusercontent.com/torvalds/linux/master/include/linux/sched/stat.h).
These upstream sources inform the contract; the hardware phase qualifies the
actual local workload behavior. The earlier capability correction remains in
the [candidate note](runtime_io_worker_wait_candidate_20261010.md).
