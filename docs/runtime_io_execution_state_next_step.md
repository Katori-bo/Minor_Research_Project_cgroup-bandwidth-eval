# Proposed execution-state feasibility check

2026-10-06. User cancelled the idle ChatGPT comparison before performance
collection. Its generation-01 preparation remains retained, but should not be
launched. No host settings or historical preparations were changed here. This
document is a next-step proposal, not a prepared runner or causal finding.

## Question and priority

Does automatic CPU performance management interact with quota period and change
CPU time per unit of identical work? This is a leading candidate, not an
established explanation of the historical reversal.

The earlier minimal SHA screen found +14.19% and +11.58% CPU/job changes with
20 versus 100 ms at approximately 0.5 core delivery. HTTP and application queues
were absent. The later minimal counter closing screen found small improvements,
essentially identical user instructions/job and similar average delivery.
Its counters therefore describe a state without the large penalty. They cannot
diagnose the earlier state retrospectively.

The closing screen changed measurement from 60 to 30 seconds, initial idle from
10 to 20 minutes, and added helper/null-perf and whole-session host sampling.
These remain confounds in that particular cross-session comparison. They do not
explain the separate original/full-V20 faithful-repeat reversal by themselves.

Read-only inspection today found amd-pstate-epp, powersave governor,
balance_performance preference, boost enabled, and allowed frequencies around
1.109–4.281 GHz on CPUs2/4. These are bounds/preferences, not measured worker
frequencies. Worker CPU2 shares a physical core with logical CPU3; CPU4 shares
with CPU5. These relationships permit sibling activity as another candidate,
but do not establish historical interference.

## Bounded next protocol to prepare

Use the retained exact minimal SHA binary initially. Retain 44,000 iterations,
GOMAXPROCS=1, GOGC=100, 0.5 CPU, original CPU placement, zero bandwidth burst,
20-second warmup and a 60-second measurement. Keep settling, observers and
measurement durations identical across experimental cells; do not substitute
an old uncounted session for a new counted control.

First establish feasibility of two distinguishable execution conditions:
the current automatic-speed policy and a supported conservative narrow
frequency-request range. Use the same nominal target for both quota periods;
inspect supported bounds and restore all original settings on exit. Do not
assume setting equal requested bounds guarantees a constant physical clock.
Select the target from supported non-boost capability, not an arbitrary GHz
value. Include relevant sibling policies if hardware shares controls. Verify
power-policy daemons do not overwrite the intervention during collection.

Actual execution metrics must show whether the intervention separates or
stabilizes execution rate. The existing minimal cycles/instructions collector
is a starting point: its observer qualification must be repeated under the
new duration and both execution conditions. Cycles per user CPU second is an
effective metric, not direct clock measurement. If insufficient, establish
execution-weighted APERF/MPERF measurement feasibility and overhead before
launching a full comparison. Do not install or start a new observer merely
because it might help.

If feasibility passes, compare 100 and 20 ms periods in both execution
conditions, using two opposite-order four-cell blocks. Primary outcome is the
within-block interaction in CPU/job ratios, accompanied by instructions/job,
cycles/instruction, effective cycle rate, actual delivered CPU and capacity.
Predeclare practical margins and stopping limits in the prepared protocol.
Whole-window averages cannot identify changes confined to the second half;
time-resolved collection requires its own qualification. Do not infer such a
change merely from the old 30/60-second difference.

## Interpretation and stopping

- Stable instructions with lower effective cycle rate during a reproduced
  penalty supports slower execution as a component.
- Stable instructions with higher cycles/instruction points to stalls or
  interrupted execution; it does not uniquely establish caches or SMT.
- More instructions during the penalty supports extra software work, requiring
  a later work breakdown to locate it.
- Less delivered CPU explains part of lost wall-time capacity, but cannot alone
  explain increased user CPU/job.
- A changed period contrast under the speed-control intervention establishes
  sensitivity to that intervention bundle. Thermal and stall changes may
  mediate it; it does not prove historical frequency caused the reversal.
- If controls cannot produce distinguishable measured conditions, observer
  overhead is unqualified, or the bounded comparison remains uninformative,
  retain the unresolved mechanism and stop. No automatic sibling-load sweep.

Only after a reproducible minimal effect should the supported condition be
checked against the original full V20 workload and existing queue predictor.
Generic slower speed reducing throughput is already expected and is not a
novel contribution; the target is a predictive interaction with quota period.

Sources: [AMD pstate documentation](https://docs.kernel.org/admin-guide/pm/amd-pstate.html),
[closing findings](runtime_io_period_reversal_closing_findings.md),
[prior-work review](runtime_io_period_literature_synthesis.md).
