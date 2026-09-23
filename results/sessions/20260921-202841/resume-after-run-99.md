# Resume boundary after run 99

The matrix has 99 complete, unflagged results in `raw/`. Runs 96–99 were
completed after the previous backup; the last complete result is
`raw/p50000_w2_moderate_bursty_r4/result.json` (matrix position 99).

Matrix position 100, `p100000_w4_moderate_steady_r2`, did not produce a
result. Its `failure.json` records that temperature did not stabilize before
the protocol timeout. The settling trace rose to roughly 54 C, while the
original session baseline is about 40.77 C. Its config, failure record, and
settling samples were moved intact to
`interrupted-trials/p100000_w4_moderate_steady_r2-attempt-1/` so the runner
can retry position 100 in a new `raw/` directory.

The original matrix, completed results, baseline, source code, and quality
gates were not changed. The runner must still pass its code, image, power,
and temperature checks before the retry begins.
