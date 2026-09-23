# Resume boundary after run 177

The matrix has 177 complete, unflagged results in `raw/`. Runs 100–177 were
completed after the previous backup. The last complete result is
`raw/p250000_w1_moderate_bursty_r3/result.json` (matrix position 177).

Matrix position 178, `p250000_w2_high_steady_r2`, did not produce a result.
Its `failure.json` records that temperature did not stabilize before the
protocol timeout. The config, failure record, and settling trace were moved
intact to `interrupted-trials/p250000_w2_high_steady_r2-attempt-1/` so the
runner can retry position 178 in a new `raw/` directory.

The original matrix, completed results, baseline, source code, and quality
gates were not changed. The runner must still pass its code, image, power,
and temperature checks before the retry begins.
