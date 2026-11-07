# Frozen study: rate-matched NGINX calibration transfer under fixed P0

10 October 2026. Prospective follow-up chosen after the known power-policy
confirmation. That confirmation and its stopped precursor remain immutable;
none of their responses or fitted probabilities enter this study's references.
The user authorized this separate question after reviewing the candidate design.

## Question and limits

Does a full empirical response reference calibrated at the known target offered
rate predict later fresh instances accurately, and materially improve over a
5/s reference, when both references and validation use the same assigned P0?
Accuracy and incremental advantage are separate reported outcomes. This is an
ordinary calibration comparison, not a new estimator or reliability diagnostic.

Retain the exact stock NGINX and client binaries, 1 MiB input, gzip level 6,
one worker on CPU 2, client/controller on CPUs 0/1, 25,000 us quota per
100,000 us period, and inherited memory/PID/resource limits. Keep P0:
amd-pstate-epp, powersave governor, balance_performance EPP. Require the
prepared complete policy snapshot at boundaries, including other CPU policies,
min/max and scope fields. Do not write EPP, governor, boost or idle-state
settings. A readback is not fixed frequency, thermal stability or isolation
from SMT/shared-package effects. CPU 3 context remains boundary-only.

Primary deadline is fixed at 20,565,395 ns. Endpoint is complete response
BodyDoneNs minus ScheduledNs before decoding/hash verification. Equality is
timely. Every unsuccessful offered request is a miss at every finite deadline,
including transport errors, non-200 responses and client-cap drops. Complete
HTTP-200 output corruption or invalid timing/accounting makes collection
technically invalid, with every partial/raw file retained.

## Fresh schedule and barriers

Before qualification, draw and seal a fresh seed, all sources, this protocol,
host/boot baseline, complete policy snapshot, lineage and full randomized order.
Six calibration cohorts use two assignments each at 4, 5 and 8 requests/s in a
uniformly chosen balanced order (90 possible orders). Each fresh service has
ten-second settling before startup, 25 warmup and 400 measured offers.

Freeze all global references before any validation. Six validation blocks each
contain 4/s and 8/s once, in a fresh uniform random order. Each of twelve fresh
services has 25 warmup and 300 measurement offers. Warmup-based predictions
freeze after warmup and before measurement. No future timing, counters or
observed error selects a reference or issues an advance assurance.

Collect all six blocks regardless of numeric accuracy. No favorable stopping,
automatic retries, replacement cohorts, resume or new generation. Changes to
the deadline, rate, workload, policy or forecasting rule require a separate design.

## Ordinary references and acquisition accounting

Represent each unsuccessful calibration/warmup offer as failure mass beyond
every finite deadline. Forecast probability is
`(failed offers + successful durations > D) / all offers`, including all-failed
references. Fit no thresholds, weights or parameters from validation.

Global methods:

1. Rate-matched CDF: the 800 fresh offers at the target rate.
2. Baseline 5/s CDF: the 800 fresh offers at 5/s for both target rates.
3. Pooled CDF: all 2,400 fresh calibration offers; descriptive comparator.

Later-decision methods, frozen separately after the full 25-offer target-rate
warmup: warmup only, sample-weighted matched plus warmup, 5/s plus warmup,
and pooled plus warmup. Updates have 825, 825 and 2,425 offers respectively.
Do not select the winning method retrospectively.

Matched and baseline references have equal effective sample counts but all
methods share a 2,400-offer acquisition procedure. Disclose all unused acquired
offers and actual collection time, rather than claiming equal standalone
procedural costs. Pooling has a larger effective sample count; warmup methods
have a later decision time and additional measurement acquisition.

## Frozen assessment

For each method compute absolute error in the observed all-offer miss fraction,
in percentage points. Average the two rate cells equally within each of six
blocks. Use conditional two-sided block t intervals with df=5, multiplier 2.571.
These condition on calibration and assume sufficient independence of consecutive
blocks; calibration uncertainty and broader future-episode coverage are not
certified.

- Primary absolute accuracy: matched mean-error interval upper bound <=5 pp.
- Incremental advantage: baseline-minus-matched mean block error >=2 pp and
  its paired interval lower bound >0. This does not require a >=2 pp lower
  confidence bound.
- The combined claim requires both. If both predictors are accurate and the
  improvement gate fails, report matched accuracy without a supported advantage,
  rather than calling accurate transfer inaccurate.

Report each block, per-rate error, signed error, maximum error, number >5 pp,
all acquired offers, calibration-cohort sensitivity, warmup/update comparisons,
and the within-block observed 8/s-minus-4/s miss-probability contrast. This
rate contrast does not isolate a physical cause; durations and traffic cadence
also differ. No causal randomization claim is required for forecast accuracy.

Secondary deadlines remain 10, 25 and 50 ms. Never promote them to primary
after outcomes. Flag primary saturation if all twelve validation fractions
equal zero or all equal one; accurate saturated forecasts do not demonstrate
a discriminating model advantage. Retain the numeric result either way.

## Inclusion, technical stops and lifetime

Retain recorded throttling, response overlap, dispatch lag and unsuccessful
offers at qualification, calibration, warmup and validation. They are
annotations, not a zero-throttling gate or future forecast input. Preserve the
inherited response-integrity, source/runtime/resource/process/ownership,
request-conservation and bounded startup/drain/cleanup/watchdog checks.
Policy snapshot differences, corrupt raw records, quiet-host refusal and
exhausted lifetime budgets stop collection technically. No attempt is replaced.

Use the unchanged 120-second service watchdog. The slowest nominal scientific
offer schedule is 105.75 seconds from warmup and measurement first-to-last
offer spans at 4/s. Startup, client finishing, checks and cleanup are additional.
Check remaining lifetime after startup and before measurement, reserving eight
seconds beyond nominal scheduled spans. This is a feasibility guard, not a
worst-case completion guarantee. The native HTTP timeout stays ten seconds;
a late/hung response or slow startup may exhaust the service watchdog and
produce a preserved technical stop. Do not extend the watchdog or shorten
calibration after observing that outcome.

Qualification is separate: one 25-warmup/20-measurement smoke cohort at each
of 4, 5 and 8/s, plus one full 25-warmup/400-measurement lifetime cohort at
4/s. Its 560 offers validate the changed rate schedules, accounting, policy
readbacks and longest lifecycle. They cannot enter calibration, choose the
deadline, tune a predictor or select continuation based on numeric accuracy.
All integrity and lifecycle replays must pass. Ten-minute qualification ceiling.

Scientific campaign: six calibration and twelve validation cohorts, 6,000
measurement plus 450 warmup offers, 6,450 total. Forty-five-minute ceiling
including a 120-second cleanup reserve. Before each cohort reserve 150 seconds
for startup/settling/active lifecycle and 120 seconds for cleanup. Seal summaries
and every partial case on any stop. Separate qualification plus campaign ceiling
is at most 55 minutes; this is a bound, not an expected runtime.

The external-terminal normal-user launcher inhibits sleep and asks for sudo
only for the inherited read-only leftover-observer inventory. No privileged
power-policy helper or new perf/BPF/sysfs polling observer runs. Codex/ChatGPT
must be closed under the inherited quiet-desktop guard. Preparation and unit
tests here do not collect performance data. New artifact root:
`analysis/runtime_io_nginx_rate_transfer/generation-01/`.

## Interpretation and terminal commands

Success supports an ordinary rate-matched calibration condition in these
fresh single-host episodes. Failure shows assigned rate and policy matching
were insufficient under this design; it does not identify the cause or refute
the full published state-aware methods. Neither outcome automatically establishes
method novelty or authorizes further collection. The friend's independent Go
V31 study remains separate and pending.

After preparation, run `bash diagnostic/start_nginx_rate_transfer.sh` from a
normal-user external terminal. Read-only preparation verification and schedule
preview: `python3 -B diagnostic/nginx_rate_transfer_study.py verify` and
`python3 -B diagnostic/nginx_rate_transfer_study.py dry-run`.
After full collection: `python3 -B diagnostic/nginx_rate_transfer_study.py replay`.
Software readiness does not establish hardware qualification or scientific accuracy.
