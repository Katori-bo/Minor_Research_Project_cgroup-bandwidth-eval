# Runtime/I/O v5 delay review — 2026-10-02

Read-only review of both retained pilots; no instrumentation, workload, gate,
or pilot results were changed, and no measurement was launched.

## Evidence

Sources: each pilot's `analysis/trials.csv`, accepted `001/server_metrics.json`,
`loadgen.json`, `trace_requests.json`, `trace_scheduler.json`, and `monitor.json`.
The four-worker comparisons are overhead trials 1/4 (on) versus 2/3 (off).

Across both sessions:

- On rejected 88/99 and 90/83 requests; off rejected none. On reached queue
  capacity 128; off maxima were 127/90 and 94/105.
- On queue p99 was 983–989 ms versus 600–811 ms off. Processing p99 was
  184–188 ms on versus 92–97 ms off.
- On worker intervals spend 40.4–41.7% of their summed duration runnable.
  Nearly all summed worker-completion-to-handler-resume time is runnable wait;
  that interval's p99 is 187–196 ms. These are aggregate state-duration shares,
  not CPU utilization or a comparison against unrecorded off scheduler states.
- CPU microseconds per completed work are approximately 4021–4036 on versus
  3965–3980 off. The roughly 1–2% increase alone does not establish why queues
  and scheduler behavior change so substantially.
- Client dispatch-lag p99 is about 1.06–1.07 ms in every trial. Four-worker
  request-written offset p99 is below 0.33 ms. Large client dispatch delays
  are not apparent at these percentiles.
- On handler-exit-to-connection-done p99 is 295.6–297.0 ms. Approximately
  96.6–98.3% of its summed duration is synchronization/other wait. Intersecting
  the saved scheduler transitions with these intervals (midpoint clock offset)
  identifies `sync.(*Cond).Wait` as the dominant waiting reason. This does not
  identify the responsible call stack or prove an instrumentation mutex issue.
- One-worker on trials have no rejections and virtually no runnable time within
  worker intervals; post-work resume p99 is below 0.71 ms. Changing workers is
  therefore an informative separate comparison, not a fix to the four-worker
  experimental condition.
- Host-wide sampled CPU utilization ranges overlap (about 3–6%). The monitor
  uses `ps ... pcpu`, not interval process CPU deltas. Neither these averages
  nor process presence rule out contention on the service CPUs. ChatGPT's
  causal contribution remains unresolved.

Percentiles use the nearest-rank definition; interval state shares sum over all
available request intervals. Never add the separate p99 values. Go Running
can include OS descheduling and quota throttling. Off trials have no runtime
scheduler trace, so a scheduler-state on/off causal comparison is unavailable.

## Correction path

The immediate failure mechanism is queue saturation. The evidence favors
investigating scheduling under the CPU quota and instrumentation perturbation;
it does not yet identify a single defective tracing call to patch.

1. Preserve v5 and its failed gate. Do not enlarge the queue, lower the offered
   load, change the worker count, or loosen the gate to relabel this pilot a pass.
2. Prepare a separately versioned diagnostic comparison that isolates runtime
   capture from custom request/connection/I/O recording. Current on/off toggles
   combine these features. Compare baseline, runtime-only, custom-recording-only,
   and combined modes with otherwise identical workload and quota. Explicitly
   define validation for each mode; reduced-evidence modes cannot claim v5's
   full request-lifecycle coverage.
3. Before implementing a specific optimization, inspect stacks for the retained
   condition-variable waits and trace writer activity. Shared recorder locks,
   growing buffers, formatting/allocation, and trace file writes are candidates,
   not established causes. Preallocation or recorder changes require evidence
   and retained completeness/lifecycle checks.
4. Improve host observation to interval process CPU deltas and relevant per-core
   activity. Run any fresh measurement from an external terminal after exiting
   ChatGPT and verifying `pgrep -a -x ChatGPT` prints nothing. The earlier quiet
   session did not satisfy that condition.
5. After isolating and correcting the perturbing component, run a fresh pilot
   under a new revision/session. Require unchanged failure-rate and overhead
   gates plus applicable trace completeness checks before the full matrix.

If full tracing cannot meet the gate at the original workload, retain it only
as explicitly perturbative diagnostic evidence. Any lower-load or shorter-window
study needs its own documented protocol and cannot validate the original setup.

## Implemented follow-up

Revision 6 adds component isolation and interval host CPU monitoring. See
[running the component experiments](runtime_io_v6_commands.md) and
[functional verification and retained wait-stack findings](runtime_io_v6_verification.md).
No performance correction is claimed before those experiments.
