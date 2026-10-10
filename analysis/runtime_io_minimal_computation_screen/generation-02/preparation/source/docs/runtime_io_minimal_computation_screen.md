# Bounded leftover audit and minimal-computation comparison

The user authorized this final bounded diagnostic branch on 2026-10-06. First
complete the read-only protected observer audit. Then, if its findings permit
performance collection, run eight same-session cells. If this does not narrow
the cause, stop this branch and report both observed directions with the original
cause unresolved. Do not automatically launch a longer study or another sweep.

## Audit

`diagnostic/leftover_observer_audit.py` inventories processes, perf-event file
descriptors, root and instance tracefs controls/events/probe definitions, and BPF
program/link/map metadata. It reads package history, settings and running service
names. It never reads trace buffers, attaches/detaches an observer, stops a process,
changes a setting, uninstalls tools or dumps BPF map contents. General command
arguments/environment are omitted from the process evidence.

The app's noninteractive sudo attempt requires a password. A readable host audit
is retained as explicitly incomplete; it found no candidates in accessible
sections but cannot clear protected evidence. Run the root audit in your external
terminal. BPF objects can be legitimate system-service objects: findings require
ownership review, not automatic removal. The screen refuses incomplete or
unexplained audits. A saved ownership review can classify known system-service
and bpftool objects; it is bound to the exact raw audit hash and is recomputed
before launch. Unknown programs, links or maps still stop the screen. Neither
a clear snapshot nor ownership classification establishes historical absence.
Generation-02 adds this evidence-bound review; generation-01 and its original
preparation remain preserved.

```bash
cd /home/Aditya/Desktop/Research_project/cpu-quota-tail-latency
sudo /usr/bin/python3 diagnostic/leftover_observer_audit.py \
  --output /home/Aditya/Desktop/Research_project/cpu-quota-tail-latency/analysis/runtime_io_leftover_observer_audit/audit-20261006-root-01.json
```

Review that output before launching performance. If it is flagged or incomplete,
share the report and stop; do not remove arbitrary BPF objects or tracing state.

## Comparison

| Cell | Workload | CPU period / quota |
|---|---|---|
| A | Retained full service, normal cleanup, yield off | 100 / 50 ms |
| B | Retained full service, normal cleanup, yield off | 20 / 10 ms |
| C | Continuously backlogged minimal SHA loop | 100 / 50 ms |
| D | Continuously backlogged minimal SHA loop | 20 / 10 ms |

Two opposite-order blocks: ABCD / DCBA. Legacy block labels 1/4 preserve the
unchanged full-service raw replay. Each cell has a fresh container, 20 seconds
warmup and 60 seconds measured computation/arrivals. Full-service arrivals retain
all 6,793 offers, the queue, instrumentation and HTTP/client configuration.
One worker, GOMAXPROCS=1, CPUs2/4, 0.5 CPU and zero bandwidth burst remain fixed.
The original memory/PID defaults remain in force, with the existing sampled
768 MiB memory safety guard. Normal cleanup is explicit GOGC=100 in both modes.
No hardware counters, profile setter, kernel tracing or race detector runs during
performance. Controller/client/host sampler stay on CPUs0/1.

The minimal executable uses Go1.26.1 from the retained compiler, CGO disabled,
amd64 v1 and trimpath, like the retained build. Its work function is verified
byte-for-byte against the original: initialize bytes0..31 and perform44,000
SHA256 iterations per job. Independent Python digest vectors test1/10/44,000.
It retains the resulting digest, so work is used. The image derives locally from
the retained service image and replaces only `/server`; no package install or
network download occurs. It emits only boundary records, measures process CPU
at phase boundaries and stays idle/alive for final cgroup checks.

This is a continuously-busy control, not an HTTP service with identical arrivals.
It removes request handling, channels, per-request recording and most allocation,
but also changes workload shape and power behavior. Presence of an effect in it
shows that HTTP/request machinery is unnecessary for that effect under those
conditions. Absence cannot exclude a burst-specific mechanism in the full service.

Minimal primary cost is whole-container CPU delta per completed computation,
checked against internally aligned process CPU (1% performance agreement margin,
5% for short functional controls). Throughput and delivered CPU use native measured
wall time. Full-service costs and certainly-backlogged capacity/delivery reuse the
qualified saved raw replay; absolute capacity estimators differ between modes.
Compare period ratios within each mode, not absolute cost as an overhead subtraction.
Native output, cgroup records, source/binary/image identities, environment, ownership
and cleanup are saved and checked; all attempts are retained without retry.

Each mode needs a CPU/job period change of at least2% in the same direction in
both blocks to pass the prioritization screen. Report individual block effects,
capacity, CPU delivery, failures and full-service deadlines. Two blocks do not
establish equivalence or a historical cause. If a service effect is absent, a
negative control cannot diagnose the old state. Rejected offers add whole-service
work and must be disclosed if present. Counter qualification remains a separate
requirement before any future causal decomposition; no automatic extension is
authorized even when a signal appears.

## Preparation and launch

Preparation runs correctness tests and short functional controls only, not the
performance comparison. It preserves all existing source/result seals. The
prepared generation contains source snapshots, binary hashes, digest vectors,
functional output and cleanup evidence. Boot/topology/source changes stop it.

After a clear root audit and completed preparation:

```bash
(
  set -e
  cd /home/Aditya/Desktop/Research_project/cpu-quota-tail-latency
  python3 diagnostic/minimal_computation_screen.py verify-preparation
  python3 diagnostic/minimal_computation_screen.py verify-audit \
    --audit analysis/runtime_io_leftover_observer_audit/audit-20261006-root-01.json
  pkill -TERM -u "$(id -u)" -x '(ChatGPT|Codex|codex)' || true
  sleep 5
  if pgrep -u "$(id -u)" -x '(ChatGPT|Codex|codex)' >/dev/null; then
    echo 'Fully quit ChatGPT/Codex before launching.'
    exit 1
  fi
  bash diagnostic/start_minimal_computation_screen.sh \
    analysis/runtime_io_leftover_observer_audit/audit-20261006-root-01.json
)
```

Expected elapsed time is about30-40 minutes with prompt thermal acceptance:
10-minute initial idle, eight60-second minimum settling windows, about11 minutes
of workload, plus startup/drain/checks. A45-minute whole-screen ceiling aborts
and preserves partial evidence instead of extending indefinitely. Each active
container retains the independent360-second ownership watchdog. No automatic
reruns, additions of blocks, reboot or power-profile changes occur.

If no narrowing results, document original V20's verified penalty and the later
verified improvement as conditional observations. The
[Linux latency guidance](https://www.kernel.org/doc/html/latest/scheduler/sched-bwc.html)
and [SBAC-PAD throughput-loss study](https://rakeshk.folk.ntnu.no/pubs/SBACPAD22.pdf)
provide context; neither proves our mechanism. The
[SoCC2025 CPU-limits study](https://sarthak-chakraborty.github.io/publications/YAAS_SoCC25.pdf)
also supports the queueing context. Do not treat agreement with these sources
as novelty or a reason to declare one retained session faulty.
