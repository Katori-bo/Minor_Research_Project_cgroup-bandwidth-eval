# V22: prospective validation of the capacity-to-deadline account

**Step 4 implementation/preparation passed — 2026-10-07:** Use the
[execution guide](runtime_io_v22_execution.md) for generation-02 and the
[verification record](runtime_io_v22_preparation_verification.md) for its 32 tests,
actual resource preflight and four short functional/cancellation checks. The
scientific design is unchanged. Research collection remains unrun. The external
launcher captures/reviews a fresh root inventory, then performs qualification,
calibration, prediction sealing and validation as the normal user with the app
fully quit. Preparation does not certify quiet-host qualification or novelty.

**Step 3 complete — 2026-10-07:** The authoritative scientific design is now
[V22 revision 1: frozen question and decisions](runtime_io_v22_frozen_question.md),
with exact vectors, calibration-only baselines, every-trial/paired primary
criteria, supporting checks and bounded technical retries. It supersedes the
proposed thresholds and unresolved design choices below. The service/client/gate
are retained; steady scheduling is already supported. Implementation/preparation
now passed as recorded above; new-boot qualification is pending. No performance run or
prediction based on new calibration has occurred.

2026-10-07. Current next-step design following the user's decision to close the
period-reversal search and move forward after restart. V22 is a proposed study
label; its implementation/preparation follow-up is recorded above. No benchmark or settings
change was launched. The earlier cost pilot was informally called V21; the
intervening GC/minimal/execution-state diagnostics keep their original names and
records rather than being retroactively renamed.

**Step 2 review — 2026-10-07:** The
[closest-work/contribution matrix](runtime_io_contribution_matrix.md) is complete.
Burst-aware modelling, container latency prediction and practical yielding
limitations have precedents. Before implementation, freeze the precise question,
constant-capacity FIFO and nominal CPU/job baselines, calibration separation and
prediction-error criteria. This yield-off study tests queue-account transfer; it
does not prospectively validate the yielding interaction or establish novelty
merely by finding that even arrivals help.

## Direction and scope

Question: at a fixed CPU contract and identical offered computation, how well
can independently measured busy service capacity predict the effect of arrival
timing on queue buildup, recovery and 500 ms deadline success?

In plain language: can we predict the waiting and deadline failures **before
running a new arrival pattern**, rather than merely explain the familiar burst
after seeing it? This extends the existing retrospective backlog analysis; it
does not reopen the unexplained CPU-period sign reversal.

The [boost screen](runtime_io_boost_screen_plan.md) is now shelved, unrun, in
accordance with the user's direction to close this branch. No boost toggle is a
post-restart default step. Keep normal recorded settings fixed. Preserve both
period directions and the failed/partial/negative diagnostics in the
[catalogue](runtime_io_investigation_catalogue.md), with historical cause unknown.

## After restart, in order

1. Run the [post-restart snapshot/comparison command](runtime_io_restart_snapshot_and_open_questions.md)
   before intentional settings/software changes. Review differences and coverage
   gaps. Snapshot comparison is not a performance baseline or a causal reboot test.
2. Refresh observer inventory/ownership evidence and boot-dependent preparation
   checks. Verify retained binary/image, client conservation, clock mapping,
   resource limits, exact schedule handling, drain/reset and quiet thermal
   readiness. Do not reuse an old same-boot qualification unchanged.
3. Use the completed [closest-work/contribution matrix](runtime_io_contribution_matrix.md)
   to finalize the prospective model, calibration procedure and acceptance criteria.
   If the claimed addition
   is already supplied by closest work, narrow to a transparent replication/case
   study rather than invent a novelty claim.
4. Implement and validate the two exact arrival vectors and independent prediction
   pipeline; prepare a new sealed generation. Provide external-terminal commands
   only after those checks pass. This step now passed; see the implementation
   and preparation update above. New-boot performance qualification is pending.
5. Collect the bounded first-stage comparison, review every prediction failure,
   and decide whether a specific boundary extension merits a further run.

## First-stage comparison

Retain the full original service/client/gate binary contract: Go1.26.1,
44,000 SHA iterations/job, one worker/GOMAXPROCS=1, queue128, yield off,
CPUs2/4, 50 ms quota per100 ms period, cpu.max.burst=0, matched resource
limits, warmup, observation and full cohort drain. Do not vary quota period,
parallelism, GC policy, boost permission or desktop activity in this stage.

- A: canonical 60-second burst vector, 6,793 offers, with alternating five-second
  low/high phases; nominal rates approximately56.605/169.815 offers/s.
- B: 6,793 offers at exact offsets `i * 60 / 6793` seconds, i=0..6792,
  approximately113.217 offers/s evenly spread.

Identical offered work does not promise identical completed work: retain all
rejections, timeouts, errors, late completions and drain outcomes. Validate actual
dispatch against the frozen vector. Successful-request p99 alone is insufficient.

Use two separately declared canonical-burst calibration trials in this new boot,
then four fresh validation pairs in balanced AB/BA/BA/AB order (eight validation
trials). Calibration is not validation and is not added to the replication count.
Freeze warmup/measurement, thermal policy and total-time ceiling in preparation;
retain the existing20-second warmup/60-second arrival duration. Ten such windows
contain about13 minutes20 seconds of workload, plus baseline/settling, setup and
drain. Establish the elapsed-time estimate with the executable protocol, rather
than promise a short total solely from these windows.

Estimate busy capacity using only the declared fixed high-phase busy windows in
the two calibration trials, retaining actual backlogged-window validity checks
and the estimator's uncertainty. Do not obtain it from validation trials, even-arm
CPU/job or the old session's approximately150 jobs/s. The restart may alter capacity.
Declare a fixed calibration-disagreement rule before collecting; a materially
unstable calibration makes transfer inconclusive rather than permitting repeated
selection until a desired capacity appears.

## Predictions and decision

Reuse the explicit FIFO/finite-buffer service model and exact offered vectors.
Seal timestamped model parameters, predicted queues/deadline/rejection outcomes
and an uncertainty/sensitivity envelope **before any validation trial**. The
prior V20 model's withheld-block check used retrospective tolerances and is not
a substitute for this prospective record.

Primary evaluation: all-offer500 ms deadline-failure prediction error; supporting
checks: logical queue peak/trajectory, ordinary recovery time, rejections,
CPU/job, delivered CPU and processing/response stages. Report block-level results
and sensitivity; do not count thousands of requests as independent experimental
replications. Keep phase/supply/response delays omitted by the simple model
explicit. Record rare-tail errors even when the500 ms aggregate passes.

Candidate practical thresholds from the earlier proposal: burst miss-rate
prediction within3 percentage points, peak within10 jobs and mean ordinary
recovery within250 ms; even arrivals at least99% all-offer500 ms success,
zero rejections and peak logical queue at most10 jobs. These are proposed screen
criteria, not guarantees or statistical equivalence. Finalize their rationale,
uncertainty handling and every-block versus pooled decision before collection;
do not adjust them after observing validation results.

The idealized model predicts almost no queue for even arrivals if calibrated
capacity is above113.217 jobs/s. If calibrated capacity is lower or its uncertainty
crosses that rate, freeze the resulting overload prediction and disclose that
the intended below-capacity comparison is not established. Do not force the
anticipated zero-miss outcome. At113.217 jobs/s, sustained whole-service cost
above4.416 ms/job would require more than0.5 CPU; average CPU/job alone was
already an unreliable predictor of saturated burst capacity in original V20.

If CPU cost/service behavior changes with arrival timing, the capacity-transfer
assumption fails and becomes a measured limit. Do not refit capacity to the even
validation results and then label the model prospectively successful. A large
discrepancy with stable cost suggests a more precise CPU-supply/stage account
may be needed; it does not by itself establish a scheduler bug.

## Candidate small contribution

The strongest candidate is a scoped, reproducible diagnostic case study:

> In this stock-Go service under a strict fractional CPU quota, yielding strongly
> reduces a measured post-computation delay while its net deadline benefit varies
> between sessions; independently calibrated capacity and arrival timing account
> for most deadline loss, with explicit validated transfer limits.

The first clause is supported by original V20 and its faithful repeat: the
original had no demonstrated500 ms gain, whereas the repeat retained a modest
100 ms-period gain. See the [evidence map](runtime_io_evidence_map.md), C03–C08,
for the supported claim boundaries and retained model failures. The prospective transfer
clause remains a hypothesis until V22. There is no claim of a novel queueing law,
universal Go defect, universal quota-period recommendation, solved historical
reversal or a new controller. Bursts building queues, parallelism tuning,
short-period performance effects and CPU-limit latency degradation already have
precedents. Merely reproducing those facts or observing both signs is not novelty.

The completed [Step 2 contribution matrix](runtime_io_contribution_matrix.md)
supersedes the narrower checks below, adding burst-aware modelling, container
simulation, responsive scheduling, recent tracing and a close engineering
yielding precedent. The items below remain the earlier scoped comparison.

Closest primary checks revisited2026-10-07:

- [Jeffery, Jensen and Mortier2024](https://arxiv.org/html/2407.11582v1): quota,
  thread overcommitment and neighbor-aware management; uniform open-loop workload,
  later excluding application queue latency. Our potential distinction is a
  prospective all-offer queue/deadline account plus the scoped negative yielding
  result, not discovery of quota-aware tuning.
- [Shetty et al., SoCC2025](https://sarthak-chakraborty.github.io/publications/YAAS_SoCC25.pdf):
  CPU limits and microburst-induced queueing/tail degradation are explicit;
  removing limits/resource-control changes differ from our fixed-quota validation.
  Its known queueing result must be acknowledged, not claimed as ours.
- [Ugedal and Kumar, SBAC-PAD2022](https://rakeshk.folk.ntnu.no/pubs/SBACPAD22.pdf):
  short-period throttling/accounting and performance loss are studied. Our
  unresolved sign reversal is contextual evidence, not a contribution proving
  a new accounting mechanism.

This is a focused check, not proof no prior publication has the same contribution.
Follow related work for quantitative prediction/diagnostic boundaries before
claiming an advance. Exact hardware/version/workload differences alone are weak
novelty. If no substantive distinction survives, frame an empirical replication
with its limits and choose scope/venue accordingly.

## Optional extension and paper structure

If the first stage is informative and the closest-work check supports a useful
addition, freeze predictions for one shorter and one longer burst duration with
the same mean/high/low offered rates,60-second total and exact total offer count.
Use fresh validation, not model fitting, to test the predicted onset of deadline
failure and buffer overflow. Reordering a fixed finite offer vector or validating
exact quantization may be required; do not silently change total work when
changing phase duration. This is a possible next step, not an automatically
authorized duration sweep.

The boundary calculation is ordinary queueing: excess arrival rate accumulates
backlog during a burst, and waiting grows until it crosses the remaining deadline
budget. Any contribution lies in validated applicability/error boundaries and
the intervention result for this service, not the formula itself.

One coherent paper can retain the original work: quota/parallelism context;
stage-localization and yielding result; capacity/queue predictions and prospective
checks; unresolved period-cost observations and reproducibility/observer limits.
The CPU-cost branch need not succeed for the other evidence to be reportable.
For broader claims, replication across another workload/host/runtime would be
needed; that is not included in this initial V22 design.
