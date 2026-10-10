# V22 implementation and preparation

Implemented 2026-10-07 against the retained
[revision-1 scientific design](runtime_io_v22_frozen_question.md).
The scientific thresholds and exact vectors are unchanged. Preparation is a
separate stage from new-boot qualification, calibration and prospective validation.

`diagnostic/v22_study.py` prepares a dedicated generation using the original
service image, native load generator and release gate. It snapshots the scientific
design and loaded implementation dependencies, verifies the actual unreleased
container/resources and performs four short HTTP compatibility/cancellation cases.
Those cases are functional software checks, not performance validation.

The external runner executes q_A/q_B, cal_1/cal_2, then the four balanced validation
pairs. Both arms receive the canonical warmup. It refuses validation without a
calibration-only sealed prediction package, stops on inadequate/unstable calibration,
and evaluates unchanged predictions against all-offer client outcomes and server
queue/stage records. The offline verifier replays raw joins and recomputes predictions
from the two calibration inputs, including sampled sensitivity summaries.

Ordinary recovery retains shared-clock uncertainty and event-boundary changes;
final drain is separate. Reports retain aggregate, queue, rejection, stage and
rare-tail errors. A failed primary result is not a rerun reason. One technical retry
is allowed in total, with earlier attempts preserved. Accepted trials are never
replaced. A completed/stopped worker requires review rather than an automatic
restart. An abrupt process death may use explicit resume only within the original
90-minute session lifetime, same boot and unchanged frozen sources.

Normal-user owned-container guards and an independent active-trial watchdog are
retained in an isolated V22 module. An independent session watchdog enforces the
90-minute collection bound and120-second cleanup grace. No new root tracing or
host-setting change is used. Fully quit the desktop app before performance collection.

After a generation has passed preparation, launch from an external interactive
terminal using the exact verified generation path:

```bash
bash diagnostic/start_v22.sh run analysis/runtime_io_v22/generation-01
```

This command includes new-boot qualification; preparation alone does not certify
the host is ready or that predictions/validation have occurred. Do not use an old
generation after a reboot or source/design change.

Read status without launching a workload:

```bash
python3 diagnostic/v22_study.py status --directory analysis/runtime_io_v22/generation-01
```

After completion, `verify-completion` replays the prospective result independently;
`analyze` creates a new retained analysis rather than overwriting an old report.
The matrix of scientific decision rules is in the frozen design, not this mutable
execution guide. If preparation fails, keep the failed generation and use a new
generation after repairs; the command above then needs that newly verified path.
