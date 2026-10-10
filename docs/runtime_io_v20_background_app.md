# Retained V20 workload: idle app open versus closed

User authorized a background-app experiment on 2026-10-06. The default is the
installed `/usr/bin/chatgpt` desktop launcher, open with no active conversation
generation, agent/tool work or user interaction. This tests an instructed idle
app-present condition, not active Codex work or every kind of background process.
Preparation never launches that app; it remains an external performance action.

## What historical reconstruction establishes

Original V20 generation-03 and its faithful generation-04 repeat each contain
1,280 saved host samples across sixteen trials. Rechecking full process delta
records found zero ChatGPT presence flags and zero exact ChatGPT/Codex/codex
names in either session. This is evidence against an app-left-open historical
explanation, not continuous proof about unsampled times or differently named
helpers. Earlier audits already replayed original client/server/CPU records,
checked source and binary identity, arrivals, resource limits, power settings,
reset/drain and collection arithmetic. The faithful original-runner repeat
restored those recorded benchmark contracts but did not restore the old penalty.

Original yield-off V20's 20 ms period increased CPU/job about 5.60%, lowered fixed
busy capacity from 151.04 to 138.67 jobs/s and reduced 500 ms success from 82.14%
to 54.86%. The original yielding response mostly eliminated completion-to-handler
waiting, while most deadline losses remained before computation. That explains
why the original result was a research problem rather than a collection failure.

We have not reconstructed original active-worker clock/frequency, user instruction
counts, fan/package/GPU state or detailed runtime maintenance; these were absent
from original measurement. Original desktop CPU activity was about 0.7% of one
core, versus about 19.8% in the faithful repeat. Presence of the same processes
does not recreate their activity. Opening the app now therefore tests a candidate
intervention; it cannot by itself reproduce or prove the historical cause.

## Frozen comparison

| Cell | Idle desktop app | CPU period/quota |
|---|---|---|
| A | Closed | 100/50 ms |
| B | Closed | 20/10 ms |
| C | Open | 100/50 ms |
| D | Open | 20/10 ms |

Eight trials in opposite orders ABCD/DCBA, with legacy blocks1/4 for original
raw replay. Yield stays off throughout to isolate the period/background
interaction. This retains V20's binary/image/client, 44,000 iterations/job,
one worker, GOMAXPROCS1, queue128, CPUs2/4, nominal0.5 CPU, zero quota burst,
20-second warmup, sixty-second burst arrivals and all6,793 offers. Original
request instrumentation, host sampler, reset/drain, cgroup observations and
client/server joining remain intact. No hardware counters or profilers are added.
It is a faithful workload/collector comparison, not a rerun of the complete
four-factor yielding matrix or an exact recreation of historical host state.

The original quiet-app guard is intentionally replaced only in this new adapter
by a required app-present/app-absent condition. Raw monitor files and their
ChatGPT presence flags are never rewritten. Every saved sample must match the
declared intervention before the original arithmetic replay is allowed to
replace its quiet-app assumption in memory. Original source files and all prior
seals are preserved. Power, resource, conservation, cleanup and coverage checks
remain active. No unrelated application is closed; the runner stops only its
newly launched app process group, after first requiring all named apps absent.

App CPU affinity is the external launcher's original unrestricted affinity,
frozen during preparation, rather than inheriting the controller's CPUs0/1.
App launcher/executable/config-flag hashes are checked. The app may display a
window during open cells. Leave it untouched, without an active response or
agent task. GUI/desktop/GPU and thermal effects are part of this intervention;
the test does not identify a pure CPU-contention mechanism. Named app CPU can
omit helpers with other names. No UI inspection proves that the app stayed idle.

Each condition gets its own initial20-minute minimum/30-minute maximum reference
once per session. This avoids requiring the open condition to have the closed
condition's temperature. Within each condition, the original60-second window,
±3°C reference band,2°C range and1°C/min slope criteria remain unchanged;
per-trial settling is capped at ten minutes. Record and disclose the temperature
difference between conditions. Do not call this a thermally matched comparison.
Whole attempt ceiling is three hours; expected time is about60–90 minutes with
prompt settling. No automatic reruns or additions if a condition fails.

Primary contrast: the 20/100 CPU-per-job ratio with the app open divided by the
same ratio with it closed. A relative interaction of at least2% in the same
direction in both blocks is a prioritization signal, not statistical confirmation.
Report both blocks, all cells, observed app/Plasma/KWin activity, fixed busy
capacity, deadline success and failures. A general slowdown at both periods is
not sufficient to explain the reversal. No large interaction is not equivalence.
An app effect here still does not show it was present historically.

## Execution speed is a separate intervention

CPU quota changes available execution time; physical frequency/power policy
changes how much computation can be performed while executing. Linux exposes
frequency bounds, governors and AMD EPP/boost controls, but a selected profile
does not establish an effective fixed worker speed. Any such intervention needs
verified measured execution rate and restoration of original settings.
This background comparison changes none of those settings.

Primary references:

- [Linux CPU frequency controls](https://www.kernel.org/doc/html/latest/admin-guide/pm/cpufreq.html)
- [AMD active-mode performance control](https://www.kernel.org/doc/html/latest/admin-guide/pm/amd-pstate.html)
- [Original-runner repeat findings](runtime_io_v20_repeat_findings.md)
- [Queue reconstruction and original problem](runtime_io_v20_backlog_findings.md)
