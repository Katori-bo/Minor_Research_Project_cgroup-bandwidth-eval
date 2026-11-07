# Independent decision gate: completed offline assessment

11 October 2026. **The scientific design is locally frozen. Collection remains
NO-GO until isolated collectors implement and qualify the pre-target barrier.**
No new performance outcomes, predictors, hardware observers or changes to the
pending V31 package accompany this gate.

The authoritative [protocol](runtime_io_slo_independent_protocol_20261011.md) and
[machine plan](../analysis/runtime_io_slo_independent/20261011-v1-frozen/plan.json)
fix four planned host/service campaigns, 72 target windows, the q97.5 positive-
slack primary event, all secondary endpoints, the three ordinary comparisons,
all-offer failure handling, availability denominators and no-retry stopping rules.
The two known hosts and 8 h 30 min cap are planning allocations; host preference
and actual availability remain unconfirmed, with no collection authorized.

## Budget result

| Per campaign | Cap | Scheduled acquisition / minimum settling | Other declared allowances | Planning total | Remaining nominal allowance |
|---|---:|---:|---:|---:|---:|
| Go | 12,600 s | 5,000 s | 1,938 s: runtime preparation, observer inventory, analysis, cleanup and 18 barrier allowances | 6,938 s | 5,662 s |
| NGINX | 2,700 s | 1,463.958 s scheduled acquisition + 250 s settling | 120 s cleanup + 18 s barrier allowances | 1,851.958 s | 848.042 s |

These are schedule geometry and reserved allowances, not a measured new-host
runtime or a bound guaranteeing successful completion. NGINX's remaining time
must absorb startup, drain, identity checks, status/guard work, observer inventory
and other orchestration. Go's remaining time must absorb variable settling,
service and drain work. Reaching a cap or watchdog stops and preserves the
attempt; it never extends the budget. Setup/package engineering is separately
logged and is outside the 30,600 s acquired-campaign cap.

The Go reference consumes 676 selected complete-response calibration offers but
acquires all 9,022 scientific calibration offers and 3,600 calibration warmup
offers. Its 12,600 targets acquire another 4,200 warmup offers. Functional
qualification/control requests are additional and must be charged from logs.
NGINX acquires 300 qualification + 75 qualification-warmup offers, 1,600
calibration + 100 calibration-warmup offers, and 5,400 target + 450 target-warmup
offers. No selected-sample count replaces full acquisition cost.

## What was verified

- All 68 Go calibration/validation warmup/measurement vectors reconcile with the
  retained offered schedules; 64 non-idle vectors also match fresh **no-network**
  exports from the retained compiled client and an independent rational oracle.
- Fifty NGINX vectors fix the exact integer-spacing schedules. The retained
  client lacks a no-network export mode; the integer scheduling primitive was
  checked in source. This is not a new client-performance qualification.
- Nineteen synthetic checks pass for equality handling, failures, quantile ranks,
  positive versus zero slack, unavailable deadlines, undefined denominators,
  full-versus-selected warmup counts, immutable receipts, clock/ordering failure,
  expired permits and refusal to overwrite or resume.
- The retained NGINX runtime dependency/binary/archive hashes verify. The entire
  288-file Intel V31 package inventory verifies unchanged. The prior SLO replay
  and empirical consolidation pass, preserving 2,559 protected inputs.
- An incorrectly bursty calibration-warmup export was rejected before freeze.
  That [preparation receipt](../analysis/runtime_io_slo_independent/20261011-v1/rejected_preparation.json)
  is preserved. Corrected warmups match the inherited steady low-rate contract;
  no scientific attempt or outcome was involved.

## Why collection is still held

Both existing collectors separate warmup from measurement but lack the SLO
forecast hook. The old NGINX apparatus additionally binds historical generation,
boot, affinity and resource identity. The evaluator's barrier is implemented and
tested; it is not integrated into either collector. An isolated adapter must
preserve those operational controls while placing durable forecast receipts
before target child creation, and qualify its raw/receipt replay and cleanup.

The one-second allowance starts after validated warmup readback/drain, not at
the last HTTP completion. Retained client clocks do not justify inventing that
absolute physical interval. The new pipeline is not claimed behaviorally
equivalent to the old one. All methods share the resulting input/state; runtime
qualification and actual host readiness remain necessary.

This finite-window study can reproduce a concrete decision failure. It cannot
certify a general false-assurance rate from four histories or turn a zero-answer
method into a useful safety result. No power or population-rate guarantee has
been inferred from 72 windows or their request counts.

## Freeze and replay

The [seal](../analysis/runtime_io_slo_independent/20261011-v1-frozen/seal.json)
records a local registration time of **12:53:01 IST on 11 October 2026**
(07:23:01 UTC). It is a local reproducibility timestamp, not an external timestamp
authority or public preregistration. Preserve v1 for any later apparatus
supplement or scientific v2. A host-preference change occurs before collection
in a preserved amendment, not by changing these sealed files.

From the repository, the offline replay command is:

```bash
python3 -B replication/slo_decision/freeze_design.py verify \
  --output analysis/runtime_io_slo_independent/20261011-v1-frozen
```

The [verification receipt](../analysis/runtime_io_slo_independent/verification_20261011.json)
records the completed checks. Next operational work is isolated collector
integration and qualification under this fixed scientific contract. Neither
historical launcher is presented as ready for this study.
