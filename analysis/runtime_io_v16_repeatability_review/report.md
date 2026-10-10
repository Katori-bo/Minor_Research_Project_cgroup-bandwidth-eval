# V16 repeatability review and offline execution audit — 2026-10-04

All 12 accepted trials and the frozen source/build/environment/raw/analysis seals verified.
The original-image A/A comparison is within the declared discovery margins in every block.
The exact-source rebuild is outside the timely-success margin in both comparisons in every block,
in the direction of improvement: +1.53–3.92 percentage points at 500 ms. This is a failed neutrality
screen, not a technically invalid collection. Four blocks do not establish statistical equivalence.

## What the offline audit establishes

Actual launch arguments match except for declared image ID and trial container name. Actual own
cgroup settings, runtime configuration, power settings and every offered ID/scheduled-offset
vector match. All inherited acceptance checks passed. Executable bytes, Go build IDs and image
runtime configuration match. Image identity/rootfs layer, creation/history/reference metadata differ;
the recorded image size differs by one byte. These differences do not establish a runtime cause.

The sampled mean temperatures under load range from 59.98–60.85°C across trials. This does not
support a large arm-specific temperature separation in these samples, but does not prove thermal
equivalence. Sampled frequencies and process CPU-placement snapshots vary and do not identify
actual frequency during each computation or exclusive occupancy. No clear causal host or
configuration mismatch was identified in the retained records.

The rebuilt-image runs use approximately 0.27–0.51% less aggregate CPU per completed job than
original label A and 0.38–0.46% less than B. Most of the difference is in user CPU accounting;
system CPU is not consistently lower. Queue p99 is 468–480 ms in rebuilt runs versus 496–508 ms
in original runs. Post-work p99 remains approximately 160–162 ms in all arms. This accompanies
the timely-success improvement, but neither marginal percentiles nor small CPU changes establish
the mechanism.

## The original research problem remains

Each arm offers 27,172 requests across four blocks. Original label A retains 2,344 successful late
responses whose computation certainly finishes before 500 ms; B retains 2,311 and the rebuild
2,381. Requests with computation certainly finishing after 500 ms number 4,935, 5,084 and 4,182,
respectively. These are descriptive request counts, not independent replications. Overall improvement
coexists with persistent post-computation misses; it is not a handoff remedy. No publication or
runnable-readiness boundary has been added.

## Decision and bounded next task

Stay in Step 1. Exact build reproducibility is established for bytes; original-image repeatability
passes the discovery screen. Behavioral neutrality across separately built image layers is still
unresolved. Do not return to another clock-count sweep or claim a scheduler cause.

If further collection is justified, prepare one narrow container-execution comparison that deliberately
equalizes the backing executable file and keeps image choice/order explicit. Declare which image/layer
or launch-state ambiguity it tests, its contrasts and interpretation before collection. A common-file
loading control is a proposed treatment, not an established solution; record identity/mount settings
without new per-request markers. If the effect persists or the control itself changes timing, report
that uncertainty and reconsider the precision/scope rather than layering instrumentation onto it.
Persistent publication recording and worker/parallelism interventions remain unqualified. No new
performance batch was prepared or launched by this offline review.

[Sealed result report](../../results/diagnostic/runtime-io-v16-repeatability-1/session/analysis/report.md)
[Detailed audit](review.json)
