# Resume boundary after run 95

The matrix has 95 complete, unflagged results in `raw/`. The last complete result is
`raw/p10000_w4_high_steady_r2/result.json` (matrix position 95).

Matrix position 96, `p100000_w1_high_bursty_r4`, did not produce a result. Its
`failure.json` records: `Power settings changed during settling; logs preserved.`
The user also reported a power interruption. Its config, failure record, and
settling samples were moved intact to
`interrupted-trials/p100000_w1_high_bursty_r4-attempt-1/` so the runner can
create a new `raw/p100000_w1_high_bursty_r4/` directory on resume.

The original matrix, complete results, calibration, baseline, source code,
and quality gates were not changed. The resume command must still pass the
runner's code, image, and power-setting checks before trial 96 starts.
