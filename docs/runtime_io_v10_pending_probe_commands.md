# Next focused experiment: does the tested fairness path execute?

Prepared 2026-10-03 after the offline timestamp investigation. This experiment
does not introduce another scheduling correction. Both arms use the tested
pending-preemption-fairness-v1 policy. The sole treatment is enabling its
diagnostic counters; the control compiles the counter updates out.

## Question and prediction before collection

The current saved traces cannot record whether `pp.preempt` was set when
`schedule` entered, whether the forced fairness point was reached, or whether
that turn selected global work, regular local work, or a sole `runnext` entry.

If the proposed path is exercised, the observed arm should report nonzero
`pending_seen`, `ordinary_fairness_reached`, and at least one forced-selection
counter. If pending requests are absent or rare relative to completed jobs,
the candidate is seldom activated under this workload. If the path executes
frequently while delays remain, executing this intervention is insufficient.
Aggregate counts do not identify the selected request or prove queue placement
for a particular slow HTTP goroutine.

The source also allows a trace-reader or GC-worker selection before ordinary
fairness; counters retain these cases. This particular probe keeps runtime
tracing OFF, so it does not test trace-reader preemption diversion. Its purpose
is the original untraced behavior, where the longest successful delays remain.

## Design and interpretation

Eight new trials: four paired blocks, counter control/observed order AB, BA,
BA, AB. Runtime tracing OFF, custom recording ON, and worker yielding OFF.
Keep the same 44,000 hash iterations, four workers, GOMAXPROCS=2,
50,000/100,000 µs quota, 128-entry queue, burst schedule, affinity, 10-second
warmup, 20-second workload and environmental acceptance rules. No recalibration.

Report all failures, successful latency, throughput and CPU cost. Compare
observed/control CPU/job, client CPU/request and successful p99 ratios to the
original ≤1.10 screens, maximum rejection-plus-timeout difference to ≤0.001,
and usable client-trace coverage to ≥99%. If observation fails those screens,
its timings cannot replace the control. Four pairs remain descriptive.

Counters cover reset through the final snapshot, including control requests
and drain. They are cumulative atomic samples, not synchronized per-request
events. Preserve those limitations when interpreting nonzero counts. No pilot
qualification or larger collection is created.

## Prepared and verified

- Separate image identities in
  `analysis/runtime_io_v10_pending_probe_verified_build/build.json`.
- Both arms passed eight targeted runtime tests and all 18 service tests.
- Real local API fixtures confirm the counter modes and original SHA response.
- The launcher checks frozen source/build, image identities, counter schema,
  quiet host, CPU placement, power, temperature and request accounting.
- Existing v8/v9 attempts, decoders and workflow records remain unchanged.

## Start in an external terminal

Save work, fully quit ChatGPT/Codex, close other CPU-heavy applications, and
keep the laptop plugged in on Balanced with the lid open. The existing
[measurement protocol](diagnostic_protocol.md) requires quiet-host process
accounting and settling; the launcher refuses collection with the app running.

```bash
cd /home/Aditya/Desktop/Research_project/cpu-quota-tail-latency
python3 diagnostic/pending_probe.py start
```

Wait for **Started in background with sleep inhibition** before closing the
terminal. There is a ten-minute initial settling interval and at least one
minute before each trial. Allow roughly 30–60 minutes, longer if cooling needs it.

Check afterward:

```bash
cd /home/Aditya/Desktop/Research_project/cpu-quota-tail-latency
python3 diagnostic/pending_probe.py status
```

The output directory is
`results/diagnostic/runtime-io-v10-pending-probe-1`. A complete run writes
`session/analysis/report.md`, `trials.csv`, `observer_screens.json` and
`validation.json`. Completion means collection/analysis validated; the report
determines whether observation perturbed outcomes and how often the path ran.

After an interruption, preserve the logs and use the same `start` command with
the app closed. Valid attempts are skipped; changed frozen sources/builds or
leftover owned containers cause refusal. No new measurement has been launched
while preparing this experiment.
