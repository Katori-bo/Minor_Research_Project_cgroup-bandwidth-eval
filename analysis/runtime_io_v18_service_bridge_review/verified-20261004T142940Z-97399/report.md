# V18 bounded service compatibility review

Decision: **bounded_service_compatibility_verified**.

The complete capture/asset/source seals verify. Raw scheduler/quota records,
thread snapshots, original service/client outcomes, clock joins and exported
request bounds reproduce both fresh validations and the five-case summary.
Three earlier controls are independently reverified and retain their original
origins; they are not new replications. Recorded owned detach/cgroup cleanup
checks passed and root tracing controls match before/after.

| Fresh capped case | Offered | Per-CPU quota intervals | nr_throttled | Clock uncertainty |
|---|---:|---:|---:|---:|
| G1 | 453 | 30 | 29 | 0.598 ms |
| G2 | 453 | 64 | 33 | 0.586 ms |

Quota intervals are separate CPU/runqueue state intervals, not counts of
whole-service pauses. Counter reads end before container stop; capture extends
through final exits. Interval counts need not equal throttled-period counts.
Do not sum overlapping per-CPU intervals into whole-service lost time.

The short traced G1 case retains 36 late successful 500 ms responses whose
computation certainly completed before that deadline under the original
client/server clock bounds (14 with at least 50 ms margin). This establishes
that the symptom and kernel records coexist in this functional capture.
The load is revised steady traffic, not the historical bursty trial.

Observer overhead is unqualified. No kernel overlap/HTTP-cause attribution
or G1/G2 performance contrast is accepted from these short captures.
Publication and handler runnable-readiness remain unobserved. The earlier
light-load failed positive control remains failed and unchanged.

Next: prepare and freeze the six-pair off/on cost protocol, using the same
original packaged service, fixed G1/workers4/quota and historical bursty load
in both arms. Extend and qualify collector lifecycle/capacity through warmup,
measurement and full drain. Both arms need identical startup/monitoring
procedures, root-helper scope/cleanup and a quiet-host thermal/power baseline.
The twelve-trial implementation remains pending; this review launches no batch.
Passing practical margins would still not establish statistical equivalence.
