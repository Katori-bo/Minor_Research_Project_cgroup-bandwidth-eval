# Fresh confirmation: policy-matched forecasting under the configured CPU quota

10 October 2026. New prospective contract chosen after inspecting the stopped
power-policy pilot. This follow-up changes the target population from the
pilot's intended zero-throttling/low-overlap domain to **all offered requests
under the same configured quota**. It is a disclosed scope change, not a resume
or reinterpretation of the pilot's original acceptance criterion.

The [stopped pilot review](../analysis/runtime_io_nginx_power_policy_review/20261010-generation01/report.md)
remains exploratory. None of its responses, its qualification responses or its
calibration estimates become new confirmation calibration or validation data.
Ordinary policy-matched calibration is the method being tested; no new estimator
or reliability diagnostic is claimed.

## Fixed scientific question

Does knowing and matching the assigned server energy/performance preference
during calibration improve all-offer complete-response deadline forecasts
across the declared offered rates, with quota-induced waiting included?

This is a single-host follow-up with fresh calibration and future validation.
Six consecutive blocks are not automatically independent episodes, and observing
an EPP effect does not isolate a physical frequency mechanism or explain the
original unobserved NGINX excursion.

## Resources, endpoint and assignments

Use the exact preserved stock NGINX/client binaries, fixed 1 MiB input, gzip
level 6, one worker on CPU 2, quota 25,000 us per 100,000 us, original memory/PID
limits and original client/controller placement on CPUs 0/1. P0 is `powersave`
with EPP `balance_performance`; P1 is the same governor with EPP `performance`.
Keep min/max, boost, idle states, quota and period unchanged. CPU 3 is the SMT
sibling; retain that shared-resource limitation and boundary context snapshots.
Setting readbacks do not establish fixed frequency or CPU isolation.

Primary deadline stays **20,565,395 ns**. The timed endpoint is
`BodyDoneNs - ScheduledNs`, before client decode/hash verification. A successful
response misses if strictly greater than the deadline. Every unsuccessful offer,
including a transport error, non-200 HTTP response or recorded client-cap drop,
is a miss. Integrity failures invalidate trustworthy collection; retain their
raw offers rather than deleting them.

Draw a fresh seed before any new fixture/smoke collection and seal it with the
source, baseline and full schedule. Four calibration cohorts, each 400 measured
offers after 25 warmup offers at 5/s, contain two P0 and two P1 assignments in
a uniformly chosen balanced order. Six validation blocks each contain P0-4/s,
P0-8/s, P1-4/s and P1-8/s once in a fresh uniform random permutation. Each
validation cohort has 25 warmup plus 300 measurement offers. Apply the setting
before ten-second settling and hold it through measurement. Fresh service/client
instances are used in every cohort. Retain the complete six-block schedule;
no favorable early stopping.

## Inclusion, observations and technical stops

**Throttling is allowed at every stage**, including smoke qualification,
calibration, warmup and validation. Keep its recorded period/time counters and
include its timing effects in the response reference and all-offer scores.
There is no hidden throttle-fraction cutoff or criterion excluding it afterward.
Measurement-counter deltas cannot become inputs to advance forecasts.

Client response overlap, dispatch delay and recorded client-cap drops are also
retained and annotated. Do not silently censor these outcomes to recreate the
pilot's earlier domain. All-offer forecasting is the broader target, while the
offered rates and measurement endpoint remain fixed. Service-queue intervals
are unobserved; client overlap is not an internal server queue measurement.

Technical stops include foreign source/runtime/process/resource/policy identity,
corrupt complete HTTP-200 output, invalid timing/counter/accounting records,
failure of bounded startup/drain/cleanup or restoration, loss of the independent
watchdog, quiet-host refusal, or exhaustion of the declared lifetime budget.
Transport errors and non-200 responses by themselves are scientific misses,
not integrity failures. A partial transport body is not mislabeled corrupt
complete output simply because subsequent decoding failed.

If a technical stop occurs, preserve every completed/partial cohort, report the
stop and leave the planned six-block result unavailable. No retries, replacement
cohorts, automatic new generation or policy/deadline adjustment.

## Fresh references and forecast barriers

All references use ordinary empirical all-offer outcomes, with unsuccessful
offers represented as failure mass beyond every finite deadline. Reference
probability is `(failed offers + successful responses exceeding D) / offers`.
This retains a consistent denominator in calibration, warmup and validation,
including the case in which a reference has no successful responses.

Freeze before validation:

1. Pooled reference: all 1,600 new calibration offers.
2. Policy-matched references: 800 new offers for each known policy.
3. Baseline-only reference: the 800 new P0 offers, used for both target policies.

For each validation cohort freeze before its measurement:

4. Its full 25-offer target-rate warmup reference.
5. Sample-weighted policy-matched plus warmup update.
6. Sample-weighted pooled plus warmup update.

Warmup-based methods have a later decision time than global calibration methods.
No weights or thresholds are fitted. Total pooled/matched calibration acquisition
budget is equal, though their per-policy effective sample counts differ. Report
sample counts and acquisition time; warmup comparisons do not have equal budgets.
The pooled reference deliberately mixes both assigned policies; superiority
over it is not superiority over an established state-aware model.

## Frozen evaluation

Primary comparison and numeric criteria remain the pilot's declared values:
equal-weight cohort absolute error in all-offer miss fraction; average the four
cells within each of six blocks. Policy-matched minus pooled improvement must
average at least **2 pp**, with its conditional two-sided 95% block interval
excluding zero improvement. The matched mean-error conditional 95% upper bound
must be **<=5 pp**. Report maximum error, every error >5 pp, per-cell errors
and calibration-cohort sensitivity alongside the aggregate result. An interval
excluding zero does not establish a 2 pp lower confidence bound.

Use six block means, df=5 and multiplier 2.571. These intervals condition on the
fresh reference and assume adequate block independence; they do not propagate
calibration uncertainty or certify every future cohort. Secondary fixed deadlines
are 10, 25 and 50 ms, with no alternative primary success declaration.

Report policy contrasts and the secondary policy-by-rate interaction. An exact
4,096-assignment sharp-null test conditions on rate positions and flips the
within-rate policy assignments. Its no-interference/carryover assumptions remain
explicit; ten-second settling does not verify thermal reset.

Report all-offer scores across the **entire** validation population irrespective
of observed throttling. Also annotate each cohort's throttle counters, overlap,
dispatch, drops, transport/HTTP failures, response stages and CPU/offer. A split
by observed throttling is descriptive post-outcome grouping, not a replacement
population or new causal predictor. Do not retune after seeing any confirmation
outcome or combine pilot and confirmation for the acceptance test.

## Qualification, preservation and budget

New files and outputs use `nginx_power_confirmation_*` and
`analysis/runtime_io_nginx_power_confirmation/generation-01/`. Preserve the
old power-policy source, seals, stopped campaign and its review byte-for-byte.

Before scientific collection, verify the inherited application/source chain,
capture a fresh boot and complete policy baseline, and qualify the new wrapper
using the reversible policy fixture (two P0/P1 cycles, including an owned child
exit/restoration test) and four new 25-warmup/20-measurement smoke cohorts.
Smoke has 180 offers and a ten-minute ceiling. All-offer observations, including
throttling, do not themselves cause smoke failure; integrity/accounting and
restoration must verify. Smoke outcomes cannot select parameters or contribute
to the scientific references. This requalifies the changed classification and
wrapper; original binaries are not rebuilt.

Scientific budget: four calibration plus 24 validation cohorts, 8,800 measured
and 700 warmup offers, **9,500 total**. Campaign ceiling 45 minutes including
120-second cleanup reserve; each service retains its 120-second watchdog and
each policy lease its <=150-second restoration watchdog. Freeze all sources,
criteria and the fresh randomized schedule before executing the fixture.

The normal-user external-terminal launcher requests sudo credentials locally,
inhibits sleep and executes qualification then scientific collection only after
replay passes. The inherited `desktop_absent` guard requires Codex/ChatGPT fully
closed during collection; preparation in this chat does not collect performance
data. No periodic sysfs polling, perf, BPF, new client recorder or other observer
is introduced. The independent policy helper restores on owner exit, EOF,
timeout, rejected commands and handled signals; it cannot survive its own
SIGKILL, kernel failure or loss of power. Record restoration failures explicitly.

If confirmation supports the numeric criteria, report a scoped ordinary
calibration-control finding. If it fails or is inconclusive, retain the full
negative/partial outcome and finish the empirical account. No further collection
or new diagnostic development is automatically authorized by this protocol.

## Commands

After preparation, run in an external terminal as the normal user:

```bash
bash /home/Aditya/Desktop/Research_project/cpu-quota-tail-latency/diagnostic/start_nginx_power_confirmation.sh
```

Verification and schedule preview do not change host settings:

```bash
python3 -B diagnostic/nginx_power_confirmation_study.py verify
python3 -B diagnostic/nginx_power_confirmation_study.py dry-run
# After complete collection:
python3 -B diagnostic/nginx_power_confirmation_study.py replay
```

Hardware qualification and scientific results remain pending until the launcher
actually completes those stages. Unit tests and a preparation seal establish
software readiness, not scientific accuracy or novelty.
