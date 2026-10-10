# Reproducing the empirical paper from saved evidence

8 October 2026. This guide accompanies the final scientific manuscript.
All commands below are offline checks. No workload collection is required.

## Manuscript and evidence

- [Readable manuscript](capacity_calibration_empirical.md).
- [Standalone LaTeX manuscript](capacity_calibration_empirical.tex), with embedded vector figures and references; no additional project files are needed by the built-in compiler.
- [Supporting material](capacity_calibration_supporting_material.md).
- [Finalization verification](../analysis/runtime_io_paper_finalization/20261008/report.json).
- [Successful built-in LaTeX compilation](../analysis/runtime_io_paper_finalization/20261008/compiler_status.json).
- [Figure coordinates and retained coefficients](../analysis/runtime_io_paper_finalization/20261008/figure_data.json).
- [Final study protocol](../docs/runtime_io_v28_protocol.md).
- [Independent V28 result audit](../analysis/runtime_io_v28_result_review/20261008/report.json).

Version 5, earlier drafts, original supporting material, scientific thresholds
and source/result seals remain preserved. The final manuscript adds editorial
detail and saved-data figures; it does not constitute another experiment.

## Claim-to-evidence map

| Claim | Evidence | Boundary |
|---|---|---|
| The tested whole-run substitution substantially overpredicts deadline misses | V28 frozen forecasts and sixteen fresh validation trials; whole-run MAE 13.494 pp | This declared substitution and shared FIFO model, one service/host/quota |
| Busy calibration predicts accurately | V28 MAE 0.453 pp; 16/16 deadline and capacity checks | Does not identify a mechanism or validate the queue model generally |
| Nonlinear CPU calibration recovers most accuracy | V28 quadratic MAE 1.169 pp; 13/16 deadline and 16/16 capacity checks | A declared CPU-only benchmark; full published algorithms are untested |
| Busy advantage over quadratic remains inconclusive | Four block contrasts; mean 0.716 pp, 95% interval [0.086,1.346]; frozen lower-bound requirement 1 pp | Neither a confirmed meaningful advantage nor equivalence |
| Direct additive idle correction does not repair this substitution | Dedicated idle observations, mean 0.000261092 CPU; corrected MAE 13.471 pp | Does not identify loaded shared overhead |
| Earlier prospective tests cover two work sizes and burst timescales | Preserved V22/V23 reports, protocols and raw outcomes | Work-size changes are not independent application transfer |
| Composition effect did not pass its minimum-effect screen | V27 generation-03 paired blocks | Keep `composition_inconclusive`; no causal attribution |

## Verify the final numbers, figures and preservation

From the repository root:

```bash
python3 -B analysis/verify_empirical_paper.py
```

This requires only the Python standard library. It checks the preserved
1,911-file scientific inventory and additional historical records, relevant
result/forecast seals, twelve calibration points, all eighty method/trial
forecast pairs, five deadline-error summaries, four block intervals, capacity
roots, manuscript numbers, central limitations and local links. It prints a
fresh check report and does not overwrite the sealed finalization report.

The earlier V28 review independently replayed raw CPU endpoints, offered-request
deadline outcomes, bounded completion windows, estimator arithmetic and a
separate FIFO recurrence. Its retained report describes those checks. The final
paper checker verifies consistency with that unchanged evidence; it does not
repeat that full raw-data replay or certify a new platform's performance.

## Figure and manuscript derivation

[The build script](../analysis/finalize_empirical_paper.py) records the exact
transformation from preserved V5 prose and the saved V28 report to the final
Markdown, standalone LaTeX, supporting material and figures. Curve evaluation
uses retained coefficients; there is no new regression fit. The PNG/SVG figures
are derived from [the figure data](../analysis/runtime_io_paper_finalization/20261008/figure_data.json).
The LaTeX embeds coordinates rather than depending on the external images.

The recorded figures use Matplotlib 3.11.2 in the existing repository `venv`.
To regenerate a figure in a separate output directory without modifying the
final manuscript or sealed artifacts:

```bash
MPLCONFIGDIR=/tmp/cpu-quota-paper-matplotlib venv/bin/python -B analysis/finalize_empirical_paper.py --figures-only /tmp/cpu-quota-paper-figures
```

The `-B` flag prevents Python cache creation in preserved source trees. Do not
run historical workload launchers or result-audit scripts that refuse to
overwrite their existing audit destinations. No old artifact needs resealing.

## Publication preparation remaining

The scientific text is complete at its stated empirical scope. Author names,
affiliations, acknowledgments, target venue/template, external artifact URL and
submission declarations have not been supplied and are not invented. The
LaTeX therefore has an empty author block. The local artifact paths are
repository references, not a public artifact release or an anonymized archive.
The standalone source compiled successfully with the built-in desktop compiler;
the PNG figures were visually inspected. The compiled PDF's full page layout
has not been independently inspected, and no PDF was exported by that tool.
Check venue rules and redact identifying host/path metadata before an external
release; retain original records locally. No upload or submission has occurred.

Collection remains stopped. A concrete extension is a later, separately
justified task, and the period-selection proposal remains on hold.
