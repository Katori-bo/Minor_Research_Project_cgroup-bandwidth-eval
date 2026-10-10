# Next step after V20: explain burst backlog before collecting again

2026-10-05. This is an offline analysis proposal, not an implemented new benchmark or authorization for another performance batch. Keep the sealed V20 outcomes and original decision unchanged.

## Immediate evidence

A clock-bounded decomposition of the existing V20 request rows puts worker-start time at completion time minus recorded processing wall time. Subtract the same exact duration from both completion clock bounds; do not replace ambiguous cases with certainty. Classify only successful misses whose computation certainly finished after 500 ms. The result locates the deadline boundary, not the cause of the preceding wait.

- Original 100 ms, yield off: 3,781 of 4,853 misses already exceeded the deadline before worker computation began (77.91%). Another 819 had computation/publication bounded before the deadline but handler execution afterward.
- Original 100 ms, yield on: 4,661 of 4,877 misses already exceeded the deadline before worker computation began (95.57%). Another 198 started certainly before the deadline but completed certainly after it. The existing completed-before/handler-after class is zero.
- Counts, clock-boundary ambiguity and all unsuccessful offers are retained separately in the accompanying sealed JSON. These are pooled descriptive counts across four blocks, not independent request replications.

This strengthens the case for examining waiting before worker execution. It does not distinguish application backlog from earlier entry delays, runtime contention or quota pauses during the buildup.

## Next analysis, using existing evidence

1. Reconstruct offered arrivals, HTTP entry, admission, worker starts, completions and queue occupancy by each burst cycle. Locate exactly which waiting stage crosses the deadline, and measure buildup and recovery. Retain all offers, rejections and clock uncertainty; compare paired blocks.
2. Construct a simple predictive queue/service account using the observed service behavior. Keep nominal quota allowance distinct from achieved service capacity; do not infer actual replenishment phase from wall clock or assign aggregate throttle counters to individual requests. Test whether a common account predicts buildup, recovery and deadline outcomes in blocks not used to construct it. Report prediction error, rather than only fitting the observed miss totals.
3. Audit the 20 ms arm's recorded CPU/job increase. Compare processing CPU components and existing host/thermal/frequency evidence where present. Missing frequency or actual throttle timelines remain missing. Do not infer overhead merely from the period change or treat those arms as acceptable remedies.
4. Summarize the supported and unresolved explanations against known resource/queueing mechanisms. Keep one worker/GOMAXPROCS=1, 100 ms quota period, yield off as the best observed 500 ms baseline; yield on is a diagnostic counterfactual, not a demonstrated deadline improvement.

## Decision before any new run

If a simple service/backlog account adequately predicts outcomes, close the isolated delayed-handler remedy route. Report the result as evidence consistent with established resource and scheduling behavior, with the stated attribution limits. The broader burst-history question can then be a separate research contribution only after literature review and a specific predictive claim.

If prediction fails materially and reproducibly, select the smallest experiment from the unexplained discrepancy. One possible validation compares bursty and evenly spread arrivals with the same total offers, work and quota contract. Freeze numerical predictions and acceptance criteria before collecting. Such a comparison tests burst-driven buildup, not exclusive attribution to quota throttling. If the discrepancy specifically concerns unobserved runnable/throttle intervals, revisit the feasibility and qualification of that observation instead.

Do not automatically launch V21, another yield/worker/period sweep, a controller or a new scheduler patch.
