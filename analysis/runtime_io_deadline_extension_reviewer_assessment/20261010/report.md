# Reviewer-style assessment of the deadline-forecasting extension

10 October 2026. Reviewed document:
`paper/deadline_resolution_extension.tex`, with its Markdown source, supporting
material, sealed results and the targeted primary-source review. This is an
internal reviewer-style assessment by the same assistant that helped prepare
the manuscript, not external peer review or independent-team reproduction.
The open LaTeX file and existing finalization package are unchanged.

## Recommendation

**Revise before submission.** The completed prospective outcomes remain
supported by the saved evidence. The main weakness is the incremental research
claim, rather than the recorded arithmetic. A scoped empirical extension or
case-study note is a plausible direction; its acceptance or suitability for a
particular venue has not been assessed. The present record does not support a
new prediction method, necessary stage decomposition, universal operating
boundary or superiority over published methods.

The smallest missing ordinary comparator can be evaluated from saved records,
and this review does so. A CDF of complete client response times from V31's
four existing timing-calibration cohorts performs about as well as the frozen
queue-subtracted reference. This substantially weakens an argument that richer
stage information is needed to obtain the good 10 ms result. It does not undo
V31's predeclared comparison against periodic+delay.

The next concrete step is a manuscript revision using this result and the
definition corrections below. That revision needs no new performance collection.
Any stronger prospective statement about the newly examined comparator or
removing instrumentation would require its own qualification and design.

## What survives the review

The finalization verifier passes: 31 scientific table rows, three primary
intervals, six V31 block summaries, stage-count conservation, figure values,
LaTeX derivation, document links and preserved file identities agree. This
verifier is a saved-evidence consistency check, not another raw campaign replay.
The previously completed raw-record audits remain the source of that stronger
verification. No numerical inconsistency in the primary results was found.

- V30's 25 ms comparison passed its frozen gates. Its periodic+delay mean
  absolute error is 2.341 pp versus 73.599 pp for fluid busy. The mean gate
  does not bound every profile or trial.
- V31's 10 ms comparison passed its frozen gates in the declared observed
  low-queue domain. Its queue-subtracted empirical reference has 1.844 pp
  error versus 67.340 pp for periodic+delay. Its advantage over that specific
  comparator remains a prospective result.
- NGINX completed eligible measurement but did not satisfy its upper-interval
  accuracy requirement. Its 5.981481 pp mean error and conditional interval
  [1.320988,10.641975] pp remain unchanged.
- The exploratory burst failure, secondary-deadline counterexamples and failed
  candidate qualifications are retained and appropriately separated from the
  successful primary comparisons.

All errors here are absolute miss-fraction errors in percentage points (pp).
These values cannot be compared directly with published quantile-relative
errors, throughput gains or worst-case guarantees.

## R1. Missing ordinary response-CDF control changes the interpretation

Priority: major scientific interpretation issue. Relevant manuscript locations:
Sections 1, 8 and 10, including the account of paired calibration timing.

For each successful eligible calibration request, let E be its complete
scheduled-to-client-completion duration, Q its observed queue wait and W its
worker-wall duration. The retained reference uses R=E-Q, described by paired
worker/residual samples. But its sum is exactly

`W + (E - Q - W) = E - Q`.

Evaluating the CDF of R therefore does not require the worker/residual split.
That split is useful for diagnostics and the independent-marginal convolution
control; it is not a new predictive capability of the primary CDF estimator.

This review pools complete E values from the same four predeclared V31 timing
cohorts, using client records for the probabilities and the original frozen
10 ms deadline. Every one of their 676 offers succeeded, and every observed
queue wait was <=100 us. Consequently the client-record pool and the original
queue-selected pool contain the same offers; this check introduces no sample
trimming or preferred-cohort selection. Mean queue wait is 9,614.442 ns and the
maximum is 46,557 ns.

| V31 reference at the original 10 ms deadline | Predicted misses % | Validation MAE pp | Maximum trial error pp | Status |
|---|---:|---:|---:|---|
| Frozen queue-subtracted calibration CDF | 67.160 | 1.844437 | 5.054500 | Original prospective result |
| Ordinary complete-response calibration CDF | 67.456 | 1.802499 | 5.350358 | New retrospective comparator check |

The mean-error difference is only 0.041938 pp. This is descriptive and does
not establish superiority or equivalence. In particular, the complete-response
reference has a slightly larger maximum trial error. The important point is
that the large contrast with periodic+delay is also compatible with an ordinary
direct response-time profile, without queue subtraction in the predictor.

The method was chosen after V31 outcomes were available, even though its
probabilities use calibration values only. It cannot inherit prospective status
or acquire V31's gates. The records were collected with the existing qualified
instrumented apparatus: this is not a prospective client-only experiment, an
observer-removal qualification, a cost saving or proof that queue measurements
are unnecessary for determining the original domain.

Required revision: describe the primary reference as an ordinary queue-adjusted
response CDF, add the complete-response control as an explicitly post-hoc
diagnostic, and remove any implication that stage pairing/decomposition was
necessary for the observed 10 ms predictive accuracy. Keep the independent
convolution result as an endpoint-specific dependence/shape contrast.

## R2. Distinguish the validation target from calibration inputs

Priority: major definition correction. Relevant locations: Section 1's
“internal-queue estimand” wording, Figure 1 caption and the NGINX interpretation.

V31's primary observed outcome is the fraction of all offers whose successful
complete client response exceeds the deadline, with failures counted as misses.
It includes queue waiting; the code uses client `EndToEndLatencyNs`. Queue
subtraction occurs in the calibration predictor, not in the validation target.

NGINX also uses an all-offer scheduled-to-client-completion miss fraction. Its
timestamp is encoded-body receipt before decoding/hash verification. The Go
load generator timestamps after consuming and closing the response body.
These completion details and correctness checks differ, so the durations are
not identical measurements. Nevertheless, both targets are complete client
response outcomes including waiting; V31 is not an internal-queue outcome.

Suggested wording:

> Both studies forecast all-offer client-completion deadline misses. V31 uses
> a queue-adjusted calibration CDF and an observed low-queue applicability
> domain. NGINX uses a complete-response calibration CDF, with no observed
> internal queue. Different applications, completion checks, deadlines,
> calibration inputs and applicability contracts prevent an exact replication
> or a pooled cross-application accuracy comparison.

This correction does not change the rationale for preserving NGINX as a
separately scoped adverse result. Its failure does not refute V31, and V31
does not guarantee complete-response stationarity in the NGINX setting.

## R3. The baselines support a case study, not a method novelty claim

Priority: major publication-strength issue. Relevant locations: abstract,
Sections 2–3, 6 and 12–14.

V30's fluid comparator assigns 1/C=28.640 ms per job, greater than its primary
25 ms deadline. Its 100% miss prediction at that endpoint follows immediately
from its imposed service-time floor, even before queueing. The contrast is a
valid test of that declared substitution, but the large numerical improvement
alone is weak evidence of an unexpected new timing law.

The periodic comparator similarly uses an effective demand derived from busy
capacity, assumed uniform phase and independently appended residual delay.
It is a deliberately simplified model with an explicit information/assumption
contract. R1 shows that a direct latency profile can explain the low-queue
accuracy without demonstrating an additional modeling algorithm.

The closest literature reinforces this boundary:

- [Li, Lu and Gill, RTSS 2019](https://www.cse.wustl.edu/~cdgill/publications/rtss19.pdf)
  already analyze response distributions under periodic/deferrable CPU service.
  Their Poisson arrivals, deterministic demand and Xen scheduling premises
  differ from our finite offered schedules under a Linux bandwidth ceiling.
  Direct full-PDF retrieval again failed; indexed primary passages and author
  metadata were available, so this review does not claim a full algorithm audit.
- [Cucinotta et al., TCC 2023](https://retis.santannapisa.it/people/nino/publication/TCC23.pdf),
  Section 4.2.1, expressly requires the reservation period to be small relative
  to per-request processing for its fluid approximation; its evaluation uses
  P=2 ms and HCBS. Our 100 ms ceiling does not test those premises.
- [CEDULE, ICAC 2018](https://www2.cs.uh.edu/~fyan/Paper/Feng-ICAC18.pdf),
  Sections II–III, already predicts tail latency from CPU-limit/load profiles.
  Its credit-control setting and quantile metrics differ; its implementation
  has not been compared under our contract.

Required revision: state precisely that the added artifact is prospective,
quantitative evidence for these tested approximations and conditions. Explain
why that empirical caution is useful beyond illustrating an already known
average-speed limitation. A strong new-method claim would need a compatible
published or ordinary comparator under a matched contract; cite incompatible
methods as background, without forcing them into an invalid comparison.
There is no basis here for a “first,” state-of-the-art or universal claim.

## R4. Statistical and decision evidence needs restrained emphasis

Priority: moderate interpretation issue, much of which the text already handles.

The conditional t intervals use six sequential counterbalanced blocks and four
timing-calibration cohorts. Independence/normality of the block summaries is
assumed, not established by counterbalancing. Calibration uncertainty is not
propagated. Preserve the engineering-gate outcomes, but do not convert them
into unconditional deployment guarantees or population-wide bounds.

NGINX block errors are 3.444444, 14.777778, 3.888889, 3.555556, 6.333333 and
3.888889 pp. The largest block contributes 41.176% of their summed error;
the six-block mean and interval therefore depend substantially on one observed
excursion. No block is excluded in this review. The interval still includes
errors below five points, so the failed upper-bound gate does not prove the
population mean necessarily exceeds five. The manuscript mostly states this
correctly; retain that distinction in any revised abstract or conclusion.

V31's correct 5% miss-budget classifications are far from the decision boundary:
all trials fail at 10 ms and all show zero misses at 12 ms. An always-fail rule
at the former endpoint and an always-pass rule at the latter give the same
classifications. This supplies no evidence of a useful advance rate selector
or precise classification near 5%; keep the prediction-error result central.

No additional collection is required to state these limitations. A stronger
operating-decision or unconditional-uncertainty claim would be a new question
requiring a separately justified design, not a cosmetic change of the old gates.

## R5. Make the manuscript self-contained and less like a project log

Priority: moderate presentation/reproducibility issue. Relevant locations:
Sections 1, 4–5 and 13.

The standalone text does not give the host CPU model, kernel version, Go version,
concrete hashing operation, exact calibration schedules or busy-window eligibility
rules. These are material to a quota/latency study. Give a compact environment
and calibration table verified from the applicable original records; do not
copy a version from an earlier study without checking its retained identity.
Link exact frozen artifacts in supporting material, while keeping enough detail
in the main paper for a reader without the repository.

Introduce V30/V31 as study identifiers once, then use descriptive study names.
Move lifetime/preflight/ownership and chronological development details to
supporting material where they do not explain a result. Compress the fourteen
sections around question, methods, three results, limitations and conclusion.
Make a formal reference to the base capacity-calibration study rather than
assuming readers know what the “completed paper” means. The absence of author
and venue information is ordinary publication preparation, not an experimental
defect or a reason to invent additional measurements.

## R6. Fix visible LaTeX conversion artifacts before publication formatting

Priority: minor editorial issue. The open source still contains literal
Markdown `**` around the multiline research question; the converter handled
bold spans one line at a time. The formulas use plain text `p_hat`, `sqrt(6)`
and `+/-` rather than mathematical notation. Replace those with native LaTeX
markup when revising, and verify the updated source with the built-in compiler.
Compilation previously succeeded, but complete PDF page layout has not been
independently inspected. No new tab or replacement document was opened for
this review.

## Scope and next action

This review rechecked selected primary-source passages, source-level endpoint
definitions and an ordinary saved-data control. It did not execute a competing
published implementation, perform external peer review, certify novelty,
collect new data or choose a venue. The comparator values use fresh-calibration
records from the original study but remain a retrospective diagnostic.

Proceed with one revision pass in the existing manuscript: address R1/R2,
narrow the contribution as in R3, retain the existing statistical limits, add
the missing methods context and correct the LaTeX markup. Preserve the current
sealed finalization as the pre-review version and create a separately dated
revision record rather than overwriting its snapshots or resealing old studies.
The present review itself does not edit the manuscript or start that revision.

Detailed calculations, per-trial errors, full diagnostic deadline grid, consumed
input hashes, this report and a reproduction script are retained under
`analysis/runtime_io_deadline_extension_reviewer_assessment/20261010/`.
Verify the review package with:

```bash
python3 -B analysis/review_deadline_extension.py --verify
```
