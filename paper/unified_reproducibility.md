# Reproducing the unified manuscript

11 October 2026. The new manuscript and closeout use saved evidence only.
No new performance collection, model fit, observer, external registration or
submission is performed. All older documents, source packages and seals remain
unchanged. [RESEARCH_FINAL.md](../RESEARCH_FINAL.md) is the current editorial
entry point; historical next-step statements retain their dates and scopes.

## Current verification

From the repository root:

```bash
python3 -B analysis/verify_unified_manuscript.py
```

The standard-library checker verifies current document/evidence hashes,
Markdown-to-LaTeX derivation, compiler receipt, result tables, local links,
all decision labels/views and exact returned reports from both used source
packages. It reruns the **sealed package assemblers** against raw target and
warmup schedules and durable decision/permit receipts; the maintained runtime
template is not substituted for the apparatus actually used. Full prior
calibration/resource/cleanup replays and their receipts remain preserved.
This is not a new live host probe, independent attestation or population-risk test.

The [closeout report](../analysis/runtime_io_unified_closeout/20261011/report.json)
states the exact scope. [Generated joint tables](../analysis/runtime_io_unified_closeout/20261011/decision_tables.md)
retain all fixed deadlines, quantiles, procedures and both reporting views,
including unavailable allocations and undefined denominators. The
[cost ledger](../analysis/runtime_io_unified_closeout/20261011/decision_costs.json)
retains successful and stopped allocations separately. The 126-slot provenance
ledger never becomes a pooled scientific endpoint.

## Historical replay

```bash
python3 -B analysis/verify_unified_manuscript.py --history
```

This additionally runs the existing empirical-consolidation checker, preserving
its thirteen saved-data checks and 2,559 protected inputs. It also runs the
original capacity-paper checker in a temporary logical workspace using the
**byte-identical historical planning file** from the retained 8 October snapshot.
Its expected planning hash is
`cc909de7dcf38834386b60c8dcb2ea28b7c17066ecd824357b40d16b1f702e51`.
All scientific inputs and historical checker code remain unchanged. The
later live plan is preserved and is not rewritten to make an old checker pass.

Directly running the older capacity checker against the current live workspace
flags the later planning-file revision. This is a known version mismatch,
not a newly changed experiment or a reason to relax original hashes. The
closeout report separately preserves current live-document identity and
historical-version replay.

The [capacity guide](capacity_calibration_reproducibility.md) and
[deadline guide](deadline_resolution_reproducibility.md) provide the deeper
raw/resource replay commands and prior arithmetic/figure provenance. Never
launch historical `run`, `campaign` or preparation commands to reproduce saved
results. No used run or failed attempt needs replacement or resealing.

## Standalone manuscript

```bash
python3 -B analysis/render_unified_manuscript.py --check
```

The [LaTeX](unified_manuscript.tex) derives deterministically from the
[Markdown](unified_manuscript.md), embeds all tables and references, and needs
no additional project files. It is opened in the built-in editor and compiled
with the desktop compiler. Its source hash and successful diagnostics are
recorded in the closeout package. Compilation confirms valid source; a full
exported-PDF page-layout inspection is not claimed.

## Outstanding scope

No independent Intel result has been received. Its separate V31 and SLO
contracts are listed in the [independent evidence status](../docs/unified_independent_evidence_status_20261011.md).
Prepared packages and inventory checks are not performance confirmation.
Authors, affiliations, target-venue formatting and public artifact location
remain unset. The current scientific manuscript is closed at its measured
same-host scope, with independent confirmation explicitly outstanding.
