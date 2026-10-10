# CPU-quota delay investigation: audited timeline and next experiment

2026-10-03. Steps 1–3 completed offline; step 4 is prepared and correctness-tested. No new quota performance measurement has been launched.

## 1. Resolve the decoding discrepancy

The exact retained Go 1.26.1 trace reader changes an event timestamp to the preceding output timestamp plus 1 ns when necessary to keep decoded output increasing. In two v9 stock/traced captures, this moved cleanup wakeups after service-local final connection boundaries. The raw wire wakeups precede those boundaries; relaxing an acceptance tolerance would conceal the problem.

A separately built audit decoder logs the original time before adjustment, while its ordinary parsed output must match the pinned decoder byte for byte (including matching wall-time formatting). The original times are restored into a separate dump, sorted chronologically; same-state census repeats are omitted because they do not describe new state transitions. All 16 audited trace streams (eight v9 and eight earlier v8) then pass goroutine transition-chain and start/stop clock-anchor checks. Request intervals are rebuilt from the retained service records. All eight v9 cleanup joins now pass.

All 16 v9 attempts remain sealed and pass the existing workload, environment and request-accounting validation. Their raw hashes were checked before and after the investigation. Original traces, decoders, frozen sources and failed workflow records are preserved. This derived reanalysis is validated; the original workflow status intentionally remains failed.

Largest decoder adjustment in v9: **2.292 seconds**. Do not use the ordinary decoded stream as an exact timing source across these adjusted regions.

### Earlier findings audit

All eight previously selected ready waits and their independent worker-completion counts survive. The non-yielded examples still wait 2.209–2.901 seconds while 298–384 jobs complete. The same-P handoff counts also survive.

One channel-admission p99 changes from 4.288 to 4.352 microseconds. More consequentially, the previously reported generation Sync events appearing shortly after worker preemption are affected by timestamp adjustment; that proximity is withdrawn as causal timing evidence. Trace-advancer starts still precede the 12 selected worker preemptions by 45–84 microseconds. That is an association, not identification of the preemption signal.

[Earlier waits](earlier_findings_audit.json), [recomputed wakeup cohorts, handoffs and maintenance context](earlier_cohorts_and_handoffs_audit.json), [timestamp audit](timestamp_audit_summary.json).

## 2. Locate the delay

The client’s slow requests spend most of their time after request writing and before the first response byte. Dispatch, connection acquisition, request writing and body consumption are short in the slowest successful cohort. Most of the untraced tail lies outside the measured server handler span.

The table reports the median across four trials of each trial’s mean over its slowest 1% of successful requests. Separate medians do not form an additive partition. The per-request server-local partition does reconcile exactly in request_stages.csv.

| Mode | Slowest 1% mean E2E ms | Queue ms | Processing ms | Post-work resume wait ms | Signed time outside handler ms | Client request-write to first-byte ms |
|---|---:|---:|---:|---:|---:|---:|
| stock_off | 4164.812 | 5.350 | 20.853 | 6.312 | 4119.956 | 4164.156 |
| stock_on | 2762.810 | 254.357 | 80.616 | 86.710 | 2203.205 | 2762.179 |
| patched_off | 4411.241 | 162.522 | 96.301 | 145.591 | 3892.129 | 4410.601 |
| patched_on | 2784.494 | 532.774 | 57.428 | 384.023 | 1835.036 | 2783.806 |

The signed outside-handler value is a difference of durations, not subtraction of client/server absolute clocks. It includes time before handler execution and transport/client activity and can be negative when client completion overlaps server exit. It does not, by itself, identify scheduling as the whole residual. Cleanup can occur after client receipt and can delay reuse of the same connection. Rejected requests and timeouts are retained separately; a successful-only p99 must not conceal failures.

[All request stages and outcomes](request_stages.csv), [trial stage summaries](stage_summaries.json).

## 3. Check the mechanism

The corrected scheduler evidence still contains network-ready HTTP goroutines waiting seconds while workers complete jobs. For example, in patched/traced block 1, G1769 waits **2.820776 seconds** while **380 jobs** complete. The preceding connection boundary was already finished; after its first run, request 467 enters the handler in **12.190–12.952 microseconds**. The patch therefore does not eliminate the observed pre-handler symptom.

| Traced runtime | Median trial network-ready p99 ms | Median trial cleanup wait p99 ms |
|---|---:|---:|
| stock_on | 2166.491 | 453.197 |
| patched_on | 2007.883 | 696.390 |

Network-ready summaries also include HTTP idle/close wakes; the explicitly matched example above is tied to subsequent handler entry. Scheduler states do not measure continuous on-CPU execution. No equivalent scheduler capture exists in trace-off trials.

The earlier source-level hypothesis about repeated handoff preference remains plausible, but queue slots, scheduler ticks and pending preemption flags are absent from the saved traces. We cannot infer that the patch’s forced-fairness branch ran from its image identity or from a preemption event alone. Source review also shows trace-reader and GC-worker return paths before the ordinary fairness point; the saved traces do not quantify whether these consumed pending requests.

Client/service request metrics are unchanged by the timestamp repair. Relative to stock/tracing-off, patched/tracing-off median successful p99 is 4.09% higher, throughput 0.63% lower and CPU/job 1.32% higher. The rejection-plus-timeout screen fails with tracing both off and on. Four blocks are descriptive: this intervention has not demonstrated an accepted solution, and this does not rule out a runtime contribution.

[Matched ready-wait examples](ready_wait_examples.json), [all trial metrics](trials.csv), [paired contrasts](contrasts.csv), [unchanged performance screens](screens.json).

## 4. One focused experiment prepared

The next question is whether the tested pending-preemption path actually executes in the untraced workload. Two separately built images use exactly the same candidate scheduling policy; only a compile-time observation constant differs. The observed arm counts pending requests seen, ordinary fairness reached, and actual global/local/fallback selections. The control compiles the counter updates out.

Eight trials in four paired blocks, AB/BA/BA/AB. Runtime tracing OFF, custom recording ON, worker yielding OFF. Work, quota, worker count, queue, client bursts, duration, affinity and acceptance rules stay fixed. Report observer/control CPU, latency, failures and throughput so instrumentation perturbation is measured. Aggregate counters cover reset through final snapshot, including control and drain; they are not per-request queue histories.

Prediction before collection: nonzero ordinary/selection counts demonstrate activation of those paths in the observed arm. Rare or absent pending signals would show that this workload scarcely activates the intervention. Activation with persistent delay would weaken the intervention’s sufficiency. A failed observer perturbation screen prevents replacing unobserved timing with observed timing. Neither result exonerates the runtime or qualifies full collection.

Both images passed eight targeted runtime tests and all 18 service tests, including direct tests of FIFO/fallback counter hooks. Local HTTP fixtures verify observation mode and the original SHA response. All 85 Python diagnostic tests pass. The new launcher preserves frozen sources, image identities, raw hashes, environmental checks and a shared experiment lock. It stops after the eight-trial report.

[Launch commands and predeclared interpretation](../../docs/runtime_io_v10_pending_probe_commands.md). The measurement protocol requires quitting ChatGPT/Codex and launching from an external terminal; the probe has not started.

## Audit artifacts

[Derived validation](validation.json). No qualification gate or language-independent conclusion is produced.
