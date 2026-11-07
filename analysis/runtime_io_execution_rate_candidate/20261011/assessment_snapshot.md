# Execution-rate drift: capability and contribution decision

11 October 2026. Read-only candidate audit following the user-confirmed hold on
longer warmups. No hardware counters were opened, service started, policy changed,
predictor fitted or manuscript edited. This is a candidate definition, not a frozen
qualification or predictive protocol.

**Decision: retain measured execution-rate drift alongside CPU demand as a
conditional measurement candidate. No predictive campaign is justified yet.**
Prepare a scope/precision/cost qualification design before deciding whether to
implement an observer. Counter visibility is supported; worker attribution,
usable access, precision, overhead and advance predictive usefulness are pending.

## Concrete question and signal

Can a change in worker execution speed already present during the existing
25-offer warmup distinguish later inaccurate deadline forecasts from accurate
ones, beyond equally acquired ordinary response and state checks?

The proposed measurements for an identity-bracketed, completed and drained window
are F = delta_APERF / delta_MPERF and C = worker CPU seconds / all offered
requests. Compare warmup with an appropriately matched calibration reference:

- x_F = log(F_warm / F_reference), measured execution-rate drift;
- x_C = log(C_warm / C_reference), CPU-demand drift.

F is a dimensionless busy-execution clock ratio, not completed work per second,
IPC, instructions per request, or end-to-end latency. Do not report GHz until
the reference-frequency definition is verified for this processor. The kernel
uses APERF/MPERF differences for busy-frequency accounting; its implementation
also illustrates why a recent sysfs frequency value is not our aligned window
measurement. [Kernel APERF/MPERF implementation](https://raw.githubusercontent.com/torvalds/linux/master/arch/x86/kernel/cpu/aperfmperf.c).

The motivation is a potentially persistent execution condition hidden by equal
EPP labels: lower F with increased C could accompany slower CPU service.
Unchanged clocks cannot rule out stalls, extra work, runnable waiting or downstream
delay. C times F is at most a relative cycle-demand proxy under aligned accounting,
not proof of identical instructions. No inverse-frequency scaling of the complete
HTTP response is justified. Reference and warmup scope, observer condition,
offer count and rate must be controlled or explicitly modelled; pooled policies
or a 5/s reference against 4/8/s warmups cannot silently be called matched.

**The required temporal relation remains a hypothesis:** the state observed before
validation must predict the subsequent response window. Better measurement of
warmup alone does not establish persistence. A clock change beginning only after
warmup has no advance warning in these features. Existing records have no aligned
worker APERF/MPERF windows, so none receives an invented retrospective score or
frequency explanation. No acceptance threshold is selected from known failures.

## Host capability, observed without opening events

The saved metadata identifies AMD Ryzen 5 5600H, family 25/model 80/stepping 0,
kernel 7.2.8-arch1-2. CPU2 shares a physical core with CPU3. CPU2 uses
amd-pstate-epp, powersave and balance_performance; allowed frequency bounds are
1,108,930--4,280,985 kHz. These are policy metadata, not worker clock samples.
EPP is a hardware preference hint. [AMD driver documentation](https://docs.kernel.org/admin-guide/pm/amd-pstate.html).

The msr PMU exposes type 13 with aperf event=0x01 and mperf event=0x02;
/usr/bin/perf exists. cpuinfo_cur_freq and /dev/cpu/2/msr are absent. Absence of
the latter does not disprove perf-mediated access. perf_event_paranoid=2;
the audit process has zero effective capabilities and NoNewPrivs=1. A future
bounded external qualification would need suitable counter access; this audit
does not change paranoia, assign capabilities, load modules or try privileged
events. [Perf security documentation](https://docs.kernel.org/admin-guide/perf-security.html).

scaling_cur_freq may reflect a requested state, or an architecture-specific
recent estimate, rather than exact current hardware frequency. It is not an
aligned worker warmup statistic. [CPUFreq documentation](https://docs.kernel.org/admin-guide/pm/cpufreq.html).

## Attribution and cost contract to resolve first

Upstream msr.c uses a task-capable perf context, rejects sampling periods and
advertises no-exclude support. It does **not** establish that these events are
CPU-wide only. Local headers expose APERF/MPERF register and feature definitions,
but the installed driver source was not available in the header tree inspected;
upstream source is a design reference, not verification of this installed binary.
[Upstream MSR PMU implementation](https://raw.githubusercontent.com/torvalds/linux/master/arch/x86/events/msr.c).

Two alternatives must not be conflated:

| Scope | What it would count | Qualification concern |
|---|---|---|
| Task-attached, identity-checked worker pinned to CPU2 | Register differences over task-scheduled intervals, if installed driver and API support this configuration | Scheduling-boundary updates may add repeated observer work; interrupts and kernel execution are not excluded automatically. It is not user-instruction-only counting. |
| CPU-wide on CPU2 | Logical-CPU busy activity during the window | Includes other tasks, kernel and interrupt activity; cannot be labelled worker frequency without an independently justified attribution bound. |

Prefer investigating task attribution first, without automatically falling back
to the CPU-wide interpretation. Even a count-only observer with two application
boundary reads may incur event installation, removal, remote reads and scheduling
updates. A small read duration does not establish behavioral equivalence. Do not
reuse the earlier worker-wait qualification as proof for this observer.

The next design must specify: supported attachment and stable PID/starttime/CPU
identity; simultaneous group/window coverage and read skew; positive MPERF
increments and handling of unavailable/multiplexed counts; request drain and
startup exclusion; bounded worker CPU alignment; and interference/SMT scope.
Invalid counts or failed offers remain visible and cause refusal rather than
dropping inconvenient cohorts. Idle/sleep boundaries must not masquerade as low
execution speed. Validation-time counters, if later acquired for mechanism
diagnosis, are inaccessible to the advance decision.

Before collection, derive useful precision from the response sensitivity and a
justified CPU-service mapping rather than assuming large counter values supply
many independent samples. Preserve the earlier observer-cost result: short
warmup variability made worker-wait equivalence inconclusive. Declare practical
behavioral margins, sample/time cost, per-service lifetime, stopping rules and
cleanup before any new randomized on/off qualification. Do not relax margins
after seeing results. A cost projection that does not fit the bounded campaign
or service lifetime stops the proposal before implementation.

## Fair comparator and possible contribution

The ordinary comparator must receive the same calibration, warmup offers,
decision time, counter information and acquisition budget. At minimum retain
policy/rate-matched empirical CDF, direct warmup CDF and ordinary response/CPU
drift checks. A state-conditioned ordinary model or selector must also receive
F and C; a counter-informed proposal cannot claim novelty by withholding them.
Specify its model and development budget before a discovery collection. Frozen
development decisions then need separate fresh confirmation. Generic clock
drift is an ordinary diagnostic, not a new method.

[ReTail (HPCA 2022)](https://people.csail.mit.edu/delimitrou/papers/2022.hpca.retail.pdf)
predicts service time using request/application features and frequency, and
adapts using prediction-error feedback. That feedback uses completed requests;
our proposed decision precedes the target window. This difference motivates a
question, not a superiority or novelty finding. Its richer method has not been
executed on our task. Frequency-sensitive end-to-end modelling also predates it:
the [2010 frequency-gradient work](https://experts.illinois.edu/en/publications/blackbox-prediction-of-the-impact-of-dvfs-on-end-to-end-performan/)
predicts transaction-time effects of DVFS. The limited search does not establish
absence of an existing advance reliability method.

APERF/MPERF also already appeared in our 6 October minimal-SHA execution-state
proposal. This note changes the application and endpoint to NGINX advance
transfer reliability; it does not reopen the closed quota-period mechanism route.
[Earlier proposal](runtime_io_execution_state_next_step.md).

A surviving contribution would require fewer inaccurate forecasts accepted at
useful answer coverage, against an equal-information/equal-cost ordinary
comparator on fresh evidence. Report coverage, accepted forecast error, bad
acceptances, false warnings, acquisition/runtime cost and unavailable cases.
Keep policy, rate and chronological blocks visible; do not treat requests or
five shared deadline labels as independent reliability episodes. There is no
selected risk guarantee, fitted guard or confirmation design in this audit.

## Next deliverable and stopping point

The next concrete deliverable is an **offline measurement qualification design**
for task-attributed F and C, including precision and overhead cost estimates.
It ends at a go/no-go decision for observer implementation and external
qualification, not at a full forecast campaign. If attribution, useful precision
or affordable behavioral qualification cannot be justified, close this candidate
and carry the complete empirical findings into the manuscript. Even a successful
measurement qualification would leave predictive usefulness untested.

Longer warmups and worker-wait remain held; friend-owned independent V31 remains
pending. The live manuscript and all previous scientific decisions are unchanged.
Evidence: `analysis/runtime_io_execution_rate_candidate/20261011/`, including
read-only capability capture, source ledger, preserved-input hashes and seal.
