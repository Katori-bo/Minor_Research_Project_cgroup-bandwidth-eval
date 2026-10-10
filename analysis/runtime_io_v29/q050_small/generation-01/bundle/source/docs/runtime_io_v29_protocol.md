# V29 overnight same-service robustness campaign

Frozen preparation date: 9 October 2026. User selected the existing service
across controlled conditions for a bounded overnight collection. This is a
separate extension dataset; V1's sources, outcomes and paper remain preserved.

## Question and scope

Do independently calibrated capacity inputs forecast fresh deadline outcomes
across two CPU budgets, two uniform SHA request sizes and two burst timescales?
The prospective primary endpoint remains all-offer 500 ms misses. The complete
25/50/100/200/500/1000 ms grid is prespecified secondary evidence for the next
model-boundary investigation. No new phase model, causal attribution or short-
deadline superiority criterion is tested by this overnight campaign.

One Go HTTP service, one host and one night support within-service robustness.
They do not establish multi-application or multi-host generality. Period selection
remains held: period is 100 ms everywhere and burst credit is zero.

## Design

| Sequential context | CPU budget | SHA iterations/request | Offered-rate multiplier |
|---|---:|---:|---:|
| q050_small | 50 ms / 100 ms | 44,000 | 1 |
| q025_small | 25 ms / 100 ms | 44,000 | 0.5 |
| q050_large | 50 ms / 100 ms | 88,000 | 0.5 |
| q025_large | 25 ms / 100 ms | 88,000 | 0.25 |

Rates are scaled by `(quota / 50000) * (44000 / iterations)` before any new
outcome. This is a declared relative-load test design, not an assumption that
actual capacity scales exactly. Calibrate each context independently; never
pool capacities or use another context's validation outcomes to fit a method.
Sequential context order is confounded with elapsed time and host state.
Do not interpret cross-context differences as an isolated causal quota/size effect.

Each context retains V28's 16 calibration slots and 16 fresh validation slots.
Calibration has two reverse-order blocks of idle, steady reference rates
15/30/60/90/120, and mixed reference lows 15/30 with high 169.8, multiplied
by the context's declared rate scale. Steady/idle measurements last 30 s;
mixed measurements last 60 s with 10 s low and 5 s high cycles. Each run has
20 s low-rate warm-up, full drain, reset, measurement and full drain.

Validation contains four balanced blocks of reference lows 15/30 crossed with
6/12 s burst cycles; high reference rate is 180. Low occupies two-thirds of
each cycle. Exact vectors and their compiled-client exports must agree before
runtime collection. There are 64 calibration and 64 validation slots in total,
plus 24 separately marked functional preflights. No parameter is selected from
V29 validation. Forecasts for all five methods and all six deadlines seal before
the first validation attempt in their context.

## Recorded evidence

Preserve scheduled offer, dispatch lag, client completion/status/error/timeout,
HTTP timing, server entry/admission, queue wait, computation interval, handler
resume/write/exit, clock intersections, warm-up/reset/full-drain receipts,
CPU usage/user/system/throttle endpoints, live thread/affinity/limit identities,
owned cleanup, and host-monitor temperature/frequency/power/process records.
Records cover all offers, including failures. Computation wall time is not
per-request CPU demand. Frequency snapshots are not execution-weighted worker
frequency. Aggregate throttle counters do not reveal per-request quota phase.

Use the existing qualified sampler-off request recorder and host monitor.
No native 20 ms sampler, kernel tracer, custom instrumentation, new build,
controller, host power change or unrelated application is added.

## Qualification, analysis and failures

Retain V28's independently defined fixed steady and backlogged windows, clock
bounds, positive-queue eligibility and 5% calibration repeatability screen.
Steady low-state rules use the reference load category before rate scaling.
CPU/memory/PID/affinity and executable identities are checked against each
context's explicit configuration, with the historical resource baseline retained.

The five capacity inputs are whole-run, idle-corrected, busy, linear CPU fit
and quadratic CPU fit. The original 500 ms accuracy checks are inherited:
3 pp miss error and 5% capacity error in every validation trial. Four-block
advantage intervals remain scoped per context; no pooled request-level inference.
The primary question is robustness, not a promise of estimator superiority.
Alternative deadlines are reported for every method/trial without selecting a
winning endpoint or transferring the 3 pp primary tolerance to them.

Calibration scientific failure stops validation for that context and remains a
recorded result; the supervisor may proceed to the next prespecified context.
Validation state/outcome failure remains in the completed dataset. Technical,
observer, cleanup or runtime failure stops the campaign; data remain intact.
One total technical retry per context is inherited, only after verified owned
cleanup and unchanged preparation/environment. No scientific retry or automatic
resume of an attempted context/campaign is allowed.

## Bounds and launch

Target approximately 6–7 hours based on four previous approximately 100-minute
context runs. This is not a completion guarantee. A seven-hour supervisor bound
includes runtime preparation, settling, collection and analysis, with the last
120 s reserved for cleanup. Per-context preparation/collection/analysis bounds
remain 600/7200/600 s, and each active container has a 360 s watchdog. If time or
host qualification prevents completion, preserve an incomplete dataset rather
than relaxing criteria or extending the night.

One campaign lock and owned-container labels protect concurrent execution and
cleanup. A separate supervisor watchdog handles owner exit and the time bound.
Fresh read-only root observer inventory is obtained after all functional
preparations, then bound to every context. A single initial sudo authentication
is requested; the later inventory uses noninteractive sudo and fails cleanly if
credentials expired. No privileged background collector is left running.

Fully quit Codex/ChatGPT and launch from a normal-user interactive external
terminal. The inherited quiet-host collector explicitly rejects these desktop
processes. External power, stable retained power settings and available storage
are checked. The launcher inhibits sleep for its lifetime and releases that
inhibitor on exit. Read the [launch instructions](runtime_io_v29_execution.md).
