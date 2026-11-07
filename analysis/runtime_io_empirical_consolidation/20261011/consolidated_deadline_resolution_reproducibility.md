# Reproducing the deadline-resolution extension from saved evidence

11 October 2026. All commands below are offline and require no new workload
collection, sudo, Docker service creation or closing desktop applications.

- [Completed manuscript](deadline_resolution_extension.md).
- [Standalone LaTeX source](deadline_resolution_extension.tex).
- [Supporting material and adverse candidate history](deadline_resolution_supporting_material.md).
- [Finalization audit](../analysis/runtime_io_deadline_extension_finalization/20261010/report.json).
- [Review-correction audit](../analysis/runtime_io_deadline_extension_revision/20261010-review-corrections/report.json).
- [Historical reviewer assessment](../docs/runtime_io_deadline_extension_reviewer_assessment_20261010.md).
- [Saved figure coordinates](../analysis/runtime_io_deadline_extension_finalization/20261010/figure_data.json).
- [Targeted prior-work review](../docs/runtime_io_deadline_boundary_prior_work_review_20261010.md).
- [Current consolidation audit package](../analysis/runtime_io_empirical_consolidation/20261011/).
- [Historical integrated manuscript audit](../analysis/runtime_io_deadline_transfer_integration/20261010/).
- [Fresh deadline-panel assessment](../docs/runtime_io_nginx_deadline_panel_assessment_20261010.md).
- [Execution-rate collection hold](../docs/runtime_io_execution_rate_qualification_design_20261011.md).
- [Completed transfer consolidation](../docs/runtime_io_transfer_consolidation_20261010.md).
- [Power confirmation assessment](../analysis/runtime_io_nginx_power_confirmation_review/20261010-generation01/report.md).
- [Rate-transfer assessment](../analysis/runtime_io_nginx_rate_transfer_review/20261010-generation01/report.md).

## Verify the integrated documents and preserved history

From the repository root:

```bash
python3 -B analysis/verify_empirical_consolidation.py
```

The checker uses the Python standard library. It verifies all four current
document hashes, the Markdown/LaTeX derivation, native compiler receipt, local
links, unchanged historical tables and the fresh panel's primary policy table.
It preserves 2,559 protected inputs, substituting captured manuscript snapshots
only where the original seals name historical live documents. Every other
protected path is checked at its original location.

For historical replay, a temporary logical workspace copies unchanged top-level
Python sources and the small protected-input closure, and links bulk saved datasets. The four manuscript documents
use their captured 10 October versions. The dedicated observer-inventory reviewer
keeps its original path because its saved absolute audit identities require it.
No checker, raw record, original seal or forecast is rewritten. The current
checker runs the preceding integration audit, complete deadline-panel replay,
timing/CPU/continuous/stage/sensitivity screens, worker-wait qualification replay
and worker-wait/warmup/execution-rate planning verification. These runs are
read-only saved-evidence checks, not new workload experiments.

Older integration, review and capability commands intentionally verify their
then-live manuscript versions. After this authorized revision use the current
checker for the full chain; running an old checker directly may correctly flag
a changed live document rather than a changed historical experiment. The sealed
snapshots and new audit make that distinction explicit.

## Reproduce the original campaign analyses

These stronger checks replay retained campaign records. They are separate from
the editorial finalization audit and may take longer:

```bash
python3 -B diagnostic/v30_study.py verify-completion --directory analysis/runtime_io_v30/generation-01
python3 -B diagnostic/v31_study.py verify-completion --directory analysis/runtime_io_v31/generation-01
python3 -B diagnostic/nginx_prediction_study.py replay
python3 -B analysis/review_nginx_power_confirmation.py --verify
python3 -B analysis/review_nginx_rate_transfer.py --verify
```

Use the preserved bundles and current verified study sources. Never invoke
`run`, `campaign`, `prepare-runtime` or historical launchers to reproduce the
existing outcomes. Do not rerun result-review scripts that refuse to overwrite
their original destinations. A future study needs its own scientific contract.

## Regenerate the figure in a separate directory

```bash
MPLCONFIGDIR=/tmp/deadline-extension-matplotlib venv/bin/python -B analysis/finalize_deadline_extension.py --figures-only /tmp/deadline-extension-figures
```

This uses the existing Matplotlib environment and saved values; it does not
fit a curve or change a forecast. The standalone LaTeX embeds a vector version
of the summary figure and requires no external project files. Compiler status
is recorded separately in the finalization package. Compilation success does
not constitute independent inspection of every PDF page.

## Scope of reproduction and publication preparation

The recorded results are V30's primary 25 ms comparison, V31's primary 10 ms
observed low-queue comparison, and NGINX's unsupported complete-response accuracy
criterion at its calibration-selected frozen deadline. They also include the
fresh policy confirmation's improvement without sufficient accuracy and the
fresh rate control's accuracy without supported advantage. The first three NGINX scientific campaigns retain the original 20.565395 ms
primary deadline. The sixth scientific campaign uses a fresh calibration-only
five-cutoff panel per policy and fails both policy accuracy gates. The older
cutoff is descriptive in that study; no favorable endpoint is substituted.
The exploratory burst
failure and candidate qualification exits remain distinct records. Checksums
establish identity, not scientific originality or performance on another host.

Existing review reports previously replayed the raw data; the finalization
audit explicitly reports whether a new full campaign replay was performed.
The six-block t intervals remain conditional on frozen calibration and their
distributional assumptions. Neither thousands of requests nor software checks
increase the number of independent experimental blocks.

Authors, affiliations, venue formatting, acknowledgments, submission declarations
and a public artifact location remain unset. The LaTeX author field is empty.
The manuscript incorporates the internal review corrections at its stated
empirical scope, complete ordinary-control follow-ups, fresh panel result and
later development/qualification limits. The local collection hold remains in
force; new-observer variability and clock-to-response accuracy are unmeasured. The independent
friend-host V31 result remains pending and excluded. No additional method,
causal attribution or reliable-transfer guard is established. External peer
review, authorship and publication preparation
remain separate. No upload or submission is performed.
