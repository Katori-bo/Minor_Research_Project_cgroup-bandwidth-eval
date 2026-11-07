# Local SLO supplement 01: observed result and authentication stop

The prospective local Go evaluation completed all 18 target windows within its
12,600 s cap. Offline return assembly and retained raw/resource replay verify
one preregistered positive-slack, small-error false-assurance event. This is fresh
same-host evidence; independent hardware validity and novelty remain unresolved.
The NGINX allocation stopped at the sudo inventory gate before qualification,
calibration or target collection. Its 18 windows remain unavailable.

The separate 36-window supplemental report is
`analysis/runtime_io_slo_independent/local-supplement01-return.json`.
It does not replace the original v1 denominator of 72 or the original failed
AMD allocations. The original Intel allocations remain pending. The supplement
is now closed: 18 primary-domain Go windows and 18 unavailable NGINX windows.

## Verified event and decision tradeoffs

Go window `v31_b3_A` uses the fixed profile A at 5 offers/s, with 300 target
offers and a calibration q97.5 cutoff of 10,497,189 ns. The ordinary reference
predicts 16/676 misses (2.3669%), below the illustrative 5% miss budget. The
observed window has 19/300 misses (6.3333%). Forecast slack is positive, and
absolute error is 3.9665 percentage points, within the preregistered five-point
threshold. This reproduces the specific event in one local window.

At that same calibration-only primary deadline, across the 18 trusted Go
windows:

| Point procedure | Meets decisions | Wrong assurances | Unnecessary rejections |
| --- | ---: | ---: | ---: |
| Reference | 18 | 5 | 0 |
| Recent 25 warmup offers | 15 | 4 | 2 |
| Sample-size-weighted update | 18 | 5 | 0 |

There are 13 observed-compliant windows. The ordinary two-sided 95% DKW
procedure is inconclusive in all 18 windows for each method at this primary
deadline, with zero assurance coverage. Its false-assurance-per-assurance
denominator is undefined, not a zero-risk estimate. The full report retains
all other fixed quantile/deadline labels and both report views; this table is
the fixed primary-deadline view, not an endpoint chosen to maximize a result.

These are descriptive decisions in the recorded stress episodes. No population
false-assurance rate, causal CPU-quota mechanism, optimal remedy or scientific
novelty is established. Local calibration, target collection and the durable
forecast barrier were frozen under the supplemental protocol before these new
outcomes, after the disclosed earlier apparatus failures.

## Replay, provenance and cost

The verification checked both complete return inventories and package identity,
fresh preparation and all six functional cases, all 16 calibration cases and
18 target cases, raw offered schedules, resource/configuration identity, cleanup,
phase accounting, the saved observer ownership review, and the exact 676-offer
calibration reference and capacity/timing prerequisite. Numerical decision and
durable forecast/permit/child ordering replay also passed. This was offline
replay with no live host or service probes. Receipts are in
`analysis/runtime_io_slo_independent/20261011-local-supplement01-raw-replay.json`.
Hashes and local timestamps are reproducibility records, not independent
attestations.

Go acquired 29,932 declared offers across functional, calibration, warmup and
target acquisitions. It used 9,652.677339705 s (about 2 h 41 min). NGINX used
301.790196732 s with zero acquired client offers. Their observed campaign total
is 9,954.467536437 s within the separate allocated 15,300 s cap. Image setup and
the original attempts remain separately recorded; preparation acquisition is
a subset of campaign acquisition and is not added twice. Saved supervisor and
Go case cleanup receipts report no errors; this is not a new live cleanup audit.

## NGINX failure and prospective command correction

The NGINX command reached the read-only inventory step. Its child command was
`sudo ... leftover_observer_audit.py`, with a 300 s bound. It exited after
300.172549166 s with the saved timeout reason. No NGINX audit JSON was completed;
no collector phase, qualification, calibration or targets were started. The
terminal reported `sudo: a password is required`.

The failure supports authentication unavailability during the inventory step.
Expired cached credentials after the long Go campaign are a plausible explanation;
the saved data do not establish the exact sudo policy or historical credential
state. The combined command still required interactive authentication for each
service. One command did not make it an unattended run, which was not clear in
the earlier instructions.

The original executed combined wrapper is preserved in
`analysis/runtime_io_slo_independent/20261011-local-supplement01-observed-review-01/combined_launcher_used.sh`.
The external wrapper was subsequently changed to check the next allocation
read-only, then perform bounded interactive `sudo -v` before launching it.
Three fake-command regression checks verify authentication before each launch,
refusal to launch NGINX after failed second authentication, and stop after a
failed Go command. These tests make no sudo, Docker, service or hardware calls.
This reduces the observed late-authentication failure risk; it does not prove
that credentials will stay usable under every sudo policy or preparation delay.

No used package, scientific plan or raw evidence was edited. The correction
does not reopen this closed NGINX allocation and supplies no replacement attempt.
Do not rerun the combined command on this consumed supplement. The next research
gate remains the independent Intel host and its pre-outcome apparatus readiness,
alongside the claim-specific novelty comparison. Further local predictor tuning
does not provide independent validation.
