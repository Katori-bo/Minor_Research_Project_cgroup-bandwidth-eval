# Link scheduler choices to delayed HTTP handlers

Prepared 2026-10-03 after the completed v10 observation probe. Its ordinary
fairness/global-selection counters were nonzero, and the original descriptive
observer screens passed. Aggregate counters cannot identify a selected G.

The separate [offline attribution](../analysis/runtime_io_v11_selected_ahead_verified/report.md)
uses the audited original-time v9 traces. It lists what was dispatched during
all 24 previously matched HTTP waits. For request 467, G1769 waited 2.820776 s
while 376 worker, 814 HTTP and 464 other/unclassified dispatches occurred;
349 direct worker-reply handoffs matched. Intervals overlap; do not sum them.
Those captures contain no pending flag or queue-selection source.

## Question and predeclared interpretation

During an observed network-ready HTTP wait, which goroutines does the tested
policy select and dispatch? How many selections captured a pending flag at
schedule entry, and which ordinary fairness selections choose other Gs?

Two new images preserve the retained pending-preemption-fairness-v1 policy.
Only a compile-time recorder constant differs. The observed image records
Waiting→Runnable observations, every findRunnable return, execute dispatches,
and valid HTTP/worker request markers (including ID zero). Selected sources
include fairness-global, global batches, local FIFO, runnext, sole runnext,
network polling, stealing/timers, trace reader and GC workers. Each event
retains the selected G, actor G, M, P, scheduler tick, time-slice inheritance,
captured pending-at-entry flag and current forceFair flag.

Capture uses one fixed 262,144-slot append-only memory buffer. Hooks acquire no
locks and allocate nothing; atomic slot reservation and release publication
support concurrent Ps. Stop disables the recorder and waits for active writers.
Generation checks exclude stale writers across functional test captures. The
launcher allows one measured capture per fresh process. Any overflow, missing
publication, marker mismatch or clock disagreement fails technical validation.
There is no wraparound or silent truncation. Function names resolve after stop.

Join a network wake to its first dispatch, then require a handler marker before
another recorded wake/dispatch. On connection reuse, prior cleanup must end
strictly before the wake using start/stop clock brackets; ambiguous cases stay
separate. Count other dispatched work strictly inside that wait, by role and
selection source. Retain selected G identities for all forceFair selections
and the delayed G's eventual source. Unmatched direct/locked-M dispatches have
no queue-source claim. Unlinked network wakes and unresolved wakes stay visible.

Prediction: if fairness turns still pass over a delayed HTTP G, their selected
identities and sources will be directly visible. If turns select that G promptly
but client delays remain, another stage needs attention. This does not prove
queue residence, exact instantaneous occupancy or preemption-signal origin.
Pending is the flag captured at schedule entry; findRunnable can retry, so it
does not prove a fresh flag was present at every eventual return. Running and
dispatch timestamps do not establish continuous CPU execution. Equal boundary
timestamps are ambiguous. Observation in one arm cannot retroactively identify
the scheduling of the other arm or of v10 requests.

## Fixed design

Eight trials: four control/observed pairs, order AB, BA, BA, AB. Both arms use
the same retained policy, runtime tracing OFF, custom recording ON, worker
yielding OFF, 44,000 hash iterations, four workers, GOMAXPROCS=2, 128-entry
queue, 50,000/100,000 µs CPU quota, original burst arrivals, CPU placement,
10-second warmup and 20-second measurement. No recalibration or correction.

The same quiet-host, power, settling and request-accounting checks apply.
Report throughput, CPU/job, client CPU/request, successful p99 and every
failure. Apply the original descriptive ≤1.10 CPU/client/p99 ratios, maximum
rejection-plus-timeout difference ≤0.001 and ≥99% client-trace coverage.
A failed observer screen prevents substituting observed timings for control.
Control scheduler waits are unavailable, not zero. Four pairs remain
descriptive; no qualification gate or full-collection eligibility is created.

The recorder starts with diagnostic capture after warmup/reset and stops after
work, handlers and final responses drain. It includes control requests and
drain, which are explicitly described in the report. Recorder initialization
is outside measurement, and both arms touch the same fixed buffer. Raw records
are exported in server_metrics.json after stop, after final CPU accounting;
JSON export cost is excluded, while hook and stop costs follow the existing
accounting boundaries.

## Preparation and verification

The separate build is `analysis/runtime_io_v11_decision_probe_final_build`.
The build verifies the retained compiler/source hashes and tests original queue
ordering/conservation, observer queue-source labels, runtime preemption, the
service, request ID zero, repeated capture generations, immutable stopped
snapshots and explicit overflow. Small real HTTP fixtures verify both image
APIs and request/worker joins. These are functional checks, not quota results.

Both images passed seven targeted runtime tests and all 20 service tests.
All 96 Python diagnostic tests passed. The final observed HTTP fixture retained
real wake/dispatch/request associations; its disabled control retained zero
scheduler events. See
[functional verification](../analysis/runtime_io_v11_decision_probe_final_build/functional_verification.json)
and the separate image IDs in
[build.json](../analysis/runtime_io_v11_decision_probe_final_build/build.json).

```bash
cd /home/Aditya/Desktop/Research_project/cpu-quota-tail-latency
python3 diagnostic/decision_probe.py verify-build
python3 -m unittest discover -s diagnostic -p 'test_*.py' -v
```

## Collect in an external terminal

Save work, fully quit ChatGPT/Codex, close other CPU-heavy applications and
keep the laptop plugged in on Balanced with the lid open. The existing quiet
host protocol refuses measurement with the app running.

```bash
cd /home/Aditya/Desktop/Research_project/cpu-quota-tail-latency
python3 diagnostic/decision_probe.py start
```

Wait for **Started in background with sleep inhibition** before closing the
terminal. Initial settling is at least ten minutes, and each trial has at least
one minute of settling. Allow roughly 30–60 minutes, longer if cooling requires.

```bash
cd /home/Aditya/Desktop/Research_project/cpu-quota-tail-latency
python3 diagnostic/decision_probe.py status
```

Outputs go to `results/diagnostic/runtime-io-v11-decision-probe-1/session/analysis/`:
`report.md`, `trials.csv`, `observer_screens.json`, `scheduler_attribution.json`
and `validation.json`. Raw arrays remain in each sealed server_metrics.json.
Completion means technical validation, not an accepted solution.

After interruption, preserve all attempts/logs and rerun the same start command
with the app closed. Changed frozen sources/builds, a leftover owned container,
or invalid recorder evidence causes refusal; nothing is silently overwritten.
The shared lock excludes overlapping experiments. The workflow stops after
eight trials and analysis. No quota measurement was launched during preparation.
