# Execution-state feasibility pilot

Prepared protocol, 2026-10-06. Performance must run from a normal-user external
terminal after ChatGPT/Codex closes. This experiment replaces the cancelled
idle-app comparison. Historical preparations/results remain untouched.

## Question

Does constraining requested CPU performance change the 20-versus-100 ms quota
period contrast for the exact minimal SHA work? Generic slower speed lowering
throughput is not the target and is not a novelty finding.

Retain the exact existing minimal image/binary, Go1.26.1, 44,000 SHA iterations,
GOMAXPROCS=1, GOGC=100, CPUs2/4, 0.5 CPU and zero quota burst. Every performance
cell has 20 seconds warmup and **60 seconds measurement**. New containers,
original accounting/ownership/cleanup checks, digest conservation and raw replay
remain mandatory. There is no HTTP traffic or application queue in this pilot.

## Intervention and qualification

Automatic condition retains original CPU settings. Constrained condition changes
only scaling_min_freq/scaling_max_freq for logical CPUs2/3/4/5 (worker cores
plus their SMT siblings). Other CPUs, governor, EPP, boost and platform profile
are unchanged. The center is 80% of the smallest supported nominal frequency,
rounded down to 1 MHz, with requested bounds +/-1%. On this host the center is
2.640 GHz and bounds are 2.6136–2.6664 GHz. Requested bounds do not guarantee a
fixed physical clock, nor is cycles/user CPU second a direct clock measurement.
The intervention affects any other activity on these shared cores as well.

A fixed privileged helper briefly applies and restores the bounds before idle
settling to check write/readback/restoration support. No workload runs in this
control selftest. Existing fixed-work hardware fixtures then verify instructions,
cycles, known sleep separation, coverage and detach. No new tools are installed.

Two independent condition-specific initial baselines each require at least
20 minutes, at most 30. Every trial then uses the existing stable 60-second
window: <=2 C range, <=1 C/min absolute slope and +/-3 C from that condition's
baseline, with a 10-minute ceiling. Allowing condition-specific temperatures
makes this a performance-control bundle, not an isolated frequency mechanism.
Host records continue through initial idle, settling and workload. Policies and
CPU bounds are checked at every workload observation, and the helper checks
bounds and parent identity about once per second while waiting. Startup/end
profile and external-power comparisons also remain mandatory.

## Fixed sequence and early stop

Each block has eight cells: both quota periods, both execution conditions, and
matched counting enabled/disabled. Disabled cells retain the same helper and
null-perf setup. Block1: A B C D E F G H. Block2 reverses this order.

| Arm | Condition | Period | Counters |
|---|---|---:|---|
| A | Automatic | 100 ms | Off |
| B | Automatic | 100 ms | On |
| C | Automatic | 20 ms | Off |
| D | Automatic | 20 ms | On |
| E | Constrained | 20 ms | Off |
| F | Constrained | 20 ms | On |
| G | Constrained | 100 ms | Off |
| H | Constrained | 100 ms | On |

First-block gate requires all four matched observer comparisons within 1% for
CPU/job, capacity and delivered CPU, plus >=5% lower effective cycles/user CPU
second in constrained versus automatic mode at **each** period. Counter-native
CPU alignment <=0.5% and event coverage >=99.5% remain required. These are
practical pilot thresholds, not statistical equivalence or causal proof.

If the gate fails, stop after eight cells, restore original bounds and report
why. Only a passing gate permits the reverse block. This is not a post hoc
search for a direction of effect. After the second block, all observer and
execution-separation checks must still pass before interpretation.

Primary interaction is (20/100 CPU/job ratio constrained)/(20/100 CPU/job ratio
automatic) - 1. A supported practical signal requires >=2% magnitude, the same
sign in both blocks, and agreement between counted/uncounted contrasts. Report
all blocks, both observer states, instructions/job, CPI, effective cycle rate,
actual CPU delivery and capacity. No additional block or full V20 run launches
automatically. The protocol cannot establish the historical reversal's cause.

## Restoration and timing

The root helper accepts fixed operation names only; target CPUs/values come from
the sealed manifest. It restores original bounds on completion, normal exceptions,
Ctrl-C/TERM/HUP, parent death or IPC disconnect. Restoration attempts every policy
even if another fails, saves readback and refuses a successful report if settings
differ. A forcibly killed privileged helper or power loss cannot execute cleanup;
if needed, use the fixed `restore-controls` command with this sealed generation,
then confirm its restoration receipt. The command restores only the saved
frequency bounds; it does not reset unrelated profile/EPP changes.

First-block stop typically takes **60–90 minutes**; a full passing pilot typically
**80–120 minutes**, depending on settling. The whole pilot has a three-hour
ceiling and retains partial evidence on failure. Never rerun into an attempted
generation or silently relax a failed gate. Functional preparation runs only
two short container controls and makes no CPU-setting change.

References: [proposal](runtime_io_execution_state_next_step.md),
[AMD pstate controls](https://docs.kernel.org/admin-guide/pm/amd-pstate.html),
[prior closing findings](runtime_io_period_reversal_closing_findings.md).
