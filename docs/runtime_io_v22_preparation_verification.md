# V22 preparation verification

2026-10-07. Step 4 implementation and preparation passed for
`analysis/runtime_io_v22/generation-02`. The [execution guide](runtime_io_v22_execution.md)
contains the external launch command. Generation-01 is retained as the initial
successful preparation; it is superseded for launching by generation-02.

The independently checked [review receipt](../analysis/runtime_io_v22_preparation_review/20261007/report.json)
records 32 passing tests, 126 frozen source/dependency files, unchanged retained
service/client/gate hashes, an actual unreleased Docker resource preflight and four
short HTTP checks. All 115 earlier dependency files from the initial preparation
remain unchanged. The Step 3 scientific seal and original V20 preparation seal
also verify.

| Functional check | All offers | Observed outcome |
|---|---:|---|
| Bursty | 114 | 114 successes |
| Even | 227 | 227 successes |
| Bursty cancellation | 453 | 451 timeouts, 2 rejections |
| Even cancellation | 453 | 452 timeouts, 1 rejection |

These are two-second software compatibility checks with the desktop app open,
not new performance evidence. Cancellation cases also retained completed worker
computations and missing handler records for independent raw reconciliation.
The preflight verified the actual packaged executable, CPU contract, startup gate,
affinity and original memory/PID defaults without releasing the service workload.
Owned containers and cgroups were removed; a subsequent Docker inventory found
zero V22 containers, and all five preparation cgroups were absent.

Tests cover exact arrivals and common warmup, finite-buffer/deadline ties,
shared-clock recovery bounds, calibration adequacy/stability, calibration-only
forecast generation, validation gating, complete sampled sensitivity predictions,
offline recomputation, resealed forecast corruption, raw stage joins, adverse
outcome/retry handling, duplicate accepted attempts and foreign ownership.
Synthetic calibration/forecast tests establish software behavior only.

No qualification, calibration or validation slot has run (0/2, 0/2, 0/8), and no
research prediction package exists. A complete fresh root observer inventory is
pending: noninteractive sudo in the app required a password. The external launcher
captures that read-only inventory, checks its ownership review and binds the
post-preparation, same-boot evidence before normal-user collection. It blocks on
missing coverage or unexplained observers. Fully quit Codex/ChatGPT first and
authenticate sudo locally when prompted. No host setting is changed.

Quiet-host qualification, calibration adequacy, prospective prediction transfer
and research novelty remain unestablished. No scientific criterion was changed.
