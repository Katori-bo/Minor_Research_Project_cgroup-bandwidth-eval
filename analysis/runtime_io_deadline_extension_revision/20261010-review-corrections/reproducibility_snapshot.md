# Reproducing the deadline-resolution extension from saved evidence

10 October 2026. All commands below are offline and require no new workload
collection, sudo, Docker service creation or closing desktop applications.

- [Completed manuscript](deadline_resolution_extension.md).
- [Standalone LaTeX source](deadline_resolution_extension.tex).
- [Supporting material and adverse candidate history](deadline_resolution_supporting_material.md).
- [Finalization audit](../analysis/runtime_io_deadline_extension_finalization/20261010/report.json).
- [Review-correction audit](../analysis/runtime_io_deadline_extension_revision/20261010-review-corrections/report.json).
- [Historical reviewer assessment](../docs/runtime_io_deadline_extension_reviewer_assessment_20261010.md).
- [Saved figure coordinates](../analysis/runtime_io_deadline_extension_finalization/20261010/figure_data.json).
- [Targeted prior-work review](../docs/runtime_io_deadline_boundary_prior_work_review_20261010.md).

## Verify the corrected documents and their evidence

From the repository root:

```bash
python3 -B analysis/verify_deadline_extension_revision.py
```

The checker uses the Python standard library. It verifies preserved input
hashes, selected existing review seals, manuscript table values, primary
block arithmetic and intervals, saved figure values, stage-count conservation,
claim limits and local document links. It checks the finalized document/seal
identities and prints its result. It independently recalculates the retrospective
response-CDF control from the four retained client calibration cohorts, using
the original deadline and validation outcomes. It performs no performance
collection and does not rewrite historical audits. The original finalization
and reviewer scripts compare live files against their earlier hashes; after
this authorized revision, run the revision checker, which verifies their
immutable snapshots and retained evidence instead of changing those hashes.

## Reproduce the original campaign analyses

These stronger checks replay retained campaign records. They are separate from
the editorial finalization audit and may take longer:

```bash
python3 -B diagnostic/v30_study.py verify-completion --directory analysis/runtime_io_v30/generation-01
python3 -B diagnostic/v31_study.py verify-completion --directory analysis/runtime_io_v31/generation-01
python3 -B diagnostic/nginx_prediction_study.py replay
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
criterion at its calibration-selected frozen deadline. The exploratory burst
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
empirical scope. External peer review, authorship and publication preparation
remain separate. No upload or submission is performed.
