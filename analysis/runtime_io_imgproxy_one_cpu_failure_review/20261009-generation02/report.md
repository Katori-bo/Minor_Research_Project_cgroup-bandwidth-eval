# One-CPU imgproxy: verified qualification domain exit

The corrected generation-02 runner completed all twelve offered-traffic cohorts
in 675.173 seconds (11.253 minutes). Eleven services passed their individual
gates; the final stock service p6_stock failed the zero-throttle measurement
gate. All 2,400 measurement offers and 300 warmup offers succeeded with the
original complete-response JPEG hash. All twelve owned cleanups verify.
Input/evidence seals, root observer inventory, image/executable identities,
single-CPU resource settings and both actual thread snapshots per service verify.
The six observed cohorts retain all 226 server records each and their raw joins.

In p6_stock, nr_throttled increased from 3 before measurement to 4 afterward;
throttled_usec increased by 46,064 us. This is a measurement increment, not
just startup accounting. The service used 3,244,797 us of CPU in that window,
or 16.224 ms per offer. Its longest offered-to-full-body response was 21.890 ms.
The 46.064 ms is cgroup throttle accounting, not a measured delay of any one
request. No time-resolved trace locates it inside a particular request window.
The stock arm intentionally has no recorder or per-stage timing.

This failure occurs with the uninstrumented binary and one granted logical CPU.
Thus neither the added timing recorder nor simultaneous execution on CPUs 2,4
is necessary for measurement throttling under these tested conditions. This does
not identify the mechanism or prove why the earlier observed-arm throttle
occurred. Periodic memory freeing, other background work, and budget-period
alignment remain unproven explanations.

There are five complete domain-eligible pairs plus one clean observed cohort
and one stock domain exit. The JSON report includes the six-pair cost endpoints
as descriptive calculations including the failed cohort. They cannot override
the joint acceptance rules or establish observer-cost qualification.

Stop this imgproxy candidate at its predeclared gate. Do not repeat the pilot
until a favorable run appears, remove the last trial, or loosen zero throttling
after seeing this outcome. A future changed candidate needs an independently
justified prospective protocol. No imgproxy calibration or held-out forecast
validation occurred; this is an applicability limitation, not a rejection of
V31's forecast within its tested domain, an independent replication, or novelty.
The original pilot and pre-measurement generation-01 code abort remain preserved.
