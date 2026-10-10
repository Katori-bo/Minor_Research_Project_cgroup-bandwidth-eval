# Final bounded instruction/cycle comparison

Authorized by the user on 2026-10-06 as one final closing test of the V20/V21
period reversal. No automatic repetitions, additional blocks or follow-up study.
After this attempt, document the strongest supported explanation and its limits,
then close this diagnostic branch even if the answer remains unresolved.

The preceding minimal screen completed seven of eight cells before its 45-minute
alarm stopped final settling. All seven raw replays verified. Minimal CPU/job
increased 14.19% and 11.58% with the 20 ms period in opposite orders; CPU delivery
stayed near 0.5 core. The first full-service pair increased CPU/job 4.80%; its
reverse pair is missing. HTTP/application queues are unnecessary for the minimal
penalty observed in that session. Its historical cause remains unknown.

This final comparison reuses the exact prepared minimal binary and image, Go
1.26.1, 44,000 SHA iterations/job, normal GOGC=100, GOMAXPROCS=1, CPUs2/4, 0.5 CPU,
zero quota burst and the original memory/PID defaults. It installs nothing and
does not change CPU policy, desktop settings, tracefs controls or BPF objects.

| Arm | Period/quota | User instructions and cycles counted |
|---|---|---|
| A | 100/50 ms | Disabled |
| B | 20/10 ms | Disabled |
| C | 100/50 ms | Enabled |
| D | 20/10 ms | Enabled |

Orders ABCD / DCBA, eight fresh containers. Each has 20 seconds warmup and
30 seconds measured computation, rather than the earlier 60 seconds. This is
a large-effect closing screen, not a precision/equivalence study. A null perf
process and the same bounded helper are present in disabled cells. The observer
contrast qualifies active hardware counting relative to this matched baseline;
it does not prove that all helper overhead is absent compared with old sessions.
Both disabled pairs must show a >=2% same-direction CPU/job change, and enabled
pairs must show a >=2% change with matching direction, before decomposition.

Before interpreting counters, every enabled/disabled comparison within each
period and block must differ by <=1% in CPU/job, capacity and delivered CPU.
This preserves the earlier observer margin: do not relax it if qualification
fails. Four bounded known-work fixtures must pass the existing 1% instruction
span and known-sleep separation checks. Both CPUs need both counters, >=99.5%
reported running coverage, successful detach and <=0.5% counter/native CPU
alignment. User-mode counts cover all Go threads. Native process/cgroup CPU
agreement remains <=1%, work digests and actual executable identities are checked.

Interpretation if all gates pass:

- >=2% more instructions/job in both pairs supports extra user-mode work,
  without locating which runtime instructions increased.
- Instructions/job within ±1% in both pairs supports similar instruction counts
  with changed execution cost; it is a practical screen, not proven equivalence.
- >=2% increased cycles/instruction in both pairs points toward more cycles per
  instruction, without uniquely identifying cache, migration or preemption.
- >=2% lower cycles/user CPU second in both pairs points toward lower effective
  execution rate. This is not a direct clock-frequency measurement or proof of
  thermal throttling. Factors can coexist; report every block, not only a mean.
- Failed observer qualification, incomplete collection, unstable period effects
  or mixed/small counter changes close the branch with cause unresolved.

[perf stat](https://man7.org/linux/man-pages/man1/perf-stat.1.html) supports
cgroup-scoped counting and controlled start/stop. The
[perf event API](https://man7.org/linux/man-pages/man2/perf_event_open.2.html)
defines retired-instruction and CPU-cycle events and warns about frequency
scaling and hardware-dependent interpretation. Cycles are user-mode counts;
normalize their rate with the aligned user CPU time, not wall time or off-CPU waits.

Host sampling runs once throughout initial idle, settling and computation on
CPUs0/1. It records interval process CPU as well as power and temperature, so a
warm settling failure has attribution evidence unavailable in the prior attempt.
This common sampler does not turn instantaneous frequency readings into causal
evidence. Same-boot reviewed root audit, AC and Balanced settings remain required.
Use a normal-user external terminal after fully closing ChatGPT/Codex; do not
restart or change settings as part of this test. A root helper is needed for
protected cgroup counters and known-work fixture cgroups; the workload controller
remains unprivileged. IPC accepts only fixed operations, never paths or commands.
Owner death/EOF stops owned counters; service ownership watchdogs remain active.

Initial settling retains the ten-minute minimum and all original thermal criteria.
Each subsequent settling wait has a three-minute ceiling with unchanged thermal
thresholds; a warmer baseline is not accepted to force completion. The whole
attempt has a 35-minute ceiling. Expect roughly 25–32 minutes when settling is
prompt. Interruptions retain partial evidence and do not count as complete tests.
Do not fill missing cells afterward or rerun this generation.

Preparation checks source seals, unit decision gates, known-work fixture selftest
and two short, counter-free functional containers only. Protected live-counter
fixtures and all eight performance cells remain unrun until the external launch.
