# Short GC screen: verified findings

Reviewed 2026-10-06. The eight-trial screen completed successfully. Its frozen
decision is `short_screen_inconclusive`: it found no large, consistent CPU
period-ratio response to disabling automatic cleanup. This is not a failed
collection and does not exclude GC from the historical session.

The [offline reviewer](../analysis/review_gc_screen.py) verifies preparation and
report seals, replays all eight trials, checks saved derivations and independently
recalculates CPU/job from raw cgroup deltas, deadlines from client records, and
the two CPU interactions. All 54,344 measured offers completed, none failed, and
all met 1,000 ms. All eight warmups completed their 2,265 offers without rejection.
The [review data](../analysis/runtime_io_gc_screen_review/20261006/report.json)
preserves these checks and host summaries. No new performance run was launched.

```bash
cd /home/Aditya/Desktop/Research_project/cpu-quota-tail-latency
python3 analysis/review_gc_screen.py
```

## Measured outcomes

Means of two trials per cell, with identical offers per trial. Capacity is the
screen's certainly-backlogged-window estimator; it is not whole-minute average
throughput. Memory is the mean of each trial's peak cgroup usage and includes
more than Go heap memory.

| Period | Automatic cleanup | CPU/job | Busy capacity | Within 500 ms | Peak memory |
|---|---|---:|---:|---:|---:|
| 100 ms | Default | 3.664 ms | 147.95 jobs/s | 72.02% | 32.4 MiB |
| 100 ms | Off | 3.659 ms | 147.85 jobs/s | 72.78% | 64.1 MiB |
| 20 ms | Default | 3.607 ms | 151.51 jobs/s | 84.09% | 28.6 MiB |
| 20 ms | Off | 3.592 ms | 152.11 jobs/s | 86.39% | 65.0 MiB |

With default cleanup, the paired 20-versus-100 CPU ratio decreases by about
1.56% on average; with cleanup off it decreases by about 1.82%. Busy capacity
increases by about 2.40% and 2.88%, respectively. Each individual block has the
same shorter-period CPU/capacity direction under both policies. The original
shorter-period CPU penalty is absent again.

The primary CPU interaction is **-0.58% in the first block and +0.04% in the
second**. Neither reaches the declared 2% screen magnitude; their signs differ.
The average interaction is about -0.27%, with a very wide exploratory two-block
95% interval [-4.10%, +3.71%]. Do not interpret the small point estimate as an
equivalence result or the interval as four-block precision.

Disabling cleanup changes CPU/job as follows:

| Period | First block | Reverse-order block |
|---|---:|---:|
| 100 ms | -0.29% | +0.004% |
| 20 ms | -0.86% | +0.041% |

Thus the small first-block CPU saving is not repeated in the second. The average
deadline improvements, especially +2.30 percentage points at 20 ms, are descriptive
supporting outcomes and do not rescue the prespecified CPU explanation. Their
two-block uncertainty is large. The sign of the 100 ms deadline change also reverses.

## Did the intervention matter at all?

The complete runtime environment was verified per trial. The earlier sealed
functional controls demonstrated collection with GOGC=100 and no cycles with
GOGC=off. The actual screen's peak memory roughly doubles with cleanup off,
consistent with changed object retention. This is evidence that the policy
change has a measurable consequence, rather than an ignored flag. Performance
GC cycle counts and CPU inside GC were deliberately not recorded, so the screen
does not quantify collector work during the measured arrivals.

CPU delivered during certainly-backlogged intervals is about 0.5 cores in every
cell (cell means 0.4997-0.5003). There is no large shortfall from the nominal
allowance in those windows in this session. This does not establish exact quota
phase, explain individual pauses or exclude delivery problems in original V20.

Both capacity estimates (148-152 jobs/s) remain below the 169.815 jobs/s burst
rate. Queue waiting remains substantial: about 265/262 ms at 100 ms and
227/215 ms at 20 ms, default/off respectively. A held-out queue-model prediction
was not performed here; the burst-demand/capacity comparison is descriptive.

## Recorded host context

All 640 saved warmup/arrival samples report ChatGPT absent. Mean temperature is
70.0 C; combined Plasma/KWin activity is about 18.93% of one CPU core. The accepted
idle baseline is 57.3 C. This resembles the other later sessions more than
original V20's roughly 0.7% desktop activity and 61.6 C monitored mean.
The association is not randomized evidence that desktop activity or temperature
causes the period result. Baloo contributes zero recorded interval CPU in this
screen; no inference about every historical background process follows.

## Decision

The screen provides no promising large, consistent GC CPU-interaction signal
under the current conditions. Do not automatically launch the longer GC study.
GC remains possible in other conditions, including an earlier state in which
the penalty actually occurs, but is a lower-priority explanation from this screen.
Neither the historical cause nor a programming-language defect is established.

A next useful comparison would target persistent state while holding normal GC,
the executable and both quota periods fixed. A controlled fresh-boot comparison
can ask whether resetting that state changes the period contrast and measured
desktop activity. It cannot isolate elapsed uptime itself or name which reboot
side effect matters. Such a run needs a new preparation for the new boot and a
separate frozen protocol; none is prepared or launched by this review. The current
default-GC cells can serve as descriptive pre-reboot evidence, with explicit
cross-session limitations. Avoid changing GC, power settings and boot state
together and attributing a result to any one of them.
