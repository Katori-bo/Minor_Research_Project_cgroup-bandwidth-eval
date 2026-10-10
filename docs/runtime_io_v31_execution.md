# V31 fresh low-queue timing confirmation

The separate V31 runner implements the candidate protocol in
`docs/runtime_io_v31_candidate_protocol_20261009.md`. The execution design is
sealed in `analysis/runtime_io_v31_design/20261009`; immutable sources and
retained binaries are bundled in `analysis/runtime_io_v31/generation-01/bundle`.
Offline software qualification must pass before this launcher is used. Runtime
qualification remains a launcher gate, not a completed offline check.

Six functional cases cover idle, high calibration steady load, calibration
burst, new steady rates 5 and 19 requests/s, and cancellation. All three new
rates, including 11 requests/s, have compiled measurement and warmup schedules
checked against the independent rational oracle. An unreleased resource
preflight precedes the functional cases. At most 41 containers are released
and 42 are created. One ordinary technical retry is allowed across the 34
scientific slots; interruption, lifetime expiry and watchdog/cleanup failure
are terminal. Existing campaigns cannot resume or overwrite attempted data.

Sixteen fresh calibration trials must satisfy the retained resource, clock,
cohort, busy-state and <=5% capacity-range checks. Only successful requests with
queue <=100 us from the four fresh low-reference 15/30 calibration trials
(actual 3.75/7.5 requests/s) fit timing models. Each cohort must be nonempty.
Negative/nonfinite stages make timing calibration unavailable; there is no
clipping or substitute fit. Worker and non-queue residual remain paired for
the primary empirical CDF. Cohort counts, accepted requests, distributions
and separate cohort curves are preserved as descriptive sensitivity.

All per-offer forecasts at 9/9.5/10/10.5/11/12/20/25/50/100/500 ms are sealed
after calibration and before validation. The primary models are paired CDF and
uniform-phase periodic FIFO plus independent calibrated response delay. The
100 phases, 1 ms apart, and full initial credit are fixed. Secondary models are
fluid busy, fluid quadratic, empirical independent worker/residual convolution,
median worker plus residual, and fixed-zero-phase/full-credit replay. The
zero-phase replay retains the no-added-delay V30 diagnostic definition.
No phase, deadline, cohort, quantile or model-switch selection follows outcomes.
Sampled empty/full-credit and capacity-extreme envelopes have no added response
delay and are descriptive scenarios, not confidence intervals.

Validation has six blocks ABC/BCA/CAB/ACB/CBA/BAC at steady rates 5/11/19
requests/s, 20 s warmup and 60 s measurement, totaling 12600 offers. Every
offered failure, rejection, dropped or missing offer is a miss. A dropped offer
alone never triggers replacement. The retained client dispatch p99 <=2 ms and
zero >10 ms late-arrival requirements still qualify actual traffic timing.
A technically
qualified trial stays in the result even if it exits the scientific domain:
zero recorded measurement throttled periods and >=99% of all offered requests
with an observed worker queue interval <=100 us. Unobserved intervals do not
count as domain successes. A domain exit fails confirmation and is never
replaced or retried for scientific reasons.

Primary accuracy is the equal-profile mean trial absolute miss-fraction error
at 10 ms in each of six blocks. Confirmation requires all eighteen technically
qualified trials inside the domain, mean block CDF error <=3 pp, positive
periodic-minus-CDF improvement in every block, and a >=5 pp lower endpoint of
the declared six-block 95% t interval (df=5, multiplier 2.571). The CDF must
classify <=5%/>5% misses correctly in every trial at both 10 and 12 ms, and each
block must have an observed profile meeting the 12 ms target. Accuracy and
decisions are reported separately. A failed gate stays negative/inconclusive;
no extra blocks or moved endpoints are allowed. This is one service and host,
with engineering targets and a feasibility trial budget, not a power claim.

Bounds: preparation 600 s, terminal-authenticated read-only observer inventory
300 s, measurement including settling and forecast seal 9000 s, analysis 900 s,
active service 360 s, total campaign 12600 s with a 120 s cleanup reserve.
Expect about two hours; adverse settling can exhaust the bound.

Run the following only after the offline qualification report passes, in an
ordinary terminal outside Codex/ChatGPT. Save work and quit Codex/ChatGPT and
the applications listed by the retained quiet-host policy (browsers, Discord,
Slack and Steam). Keep the PC plugged in with its retained balanced profile.
The runner inhibits sleep without changing host settings. Stay at the terminal
until functional qualification finishes, the read-only observer sudo prompt
accepts authentication, and the first scientific calibration trial starts.

```bash
cd /home/Aditya/Desktop/Research_project/cpu-quota-tail-latency
bash diagnostic/start_v31.sh
```

Do not reopen desktop applications until collection finishes. On completion,
read `analysis/runtime_io_v31_campaign/generation-01/summary.json` and the sealed
report referenced by `analysis/runtime_io_v31/generation-01/latest_analysis.json`.
If it stops, preserve both generation directories and review the interruption
before any new design or generation. This command never automatically resumes.
