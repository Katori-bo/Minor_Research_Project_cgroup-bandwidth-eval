# Run 178 retry boundary

The matrix still has 177 complete, unflagged results. A second attempt at
matrix position 178, `p250000_w2_high_steady_r2`, failed its pretrial
temperature settling check and produced no `result.json`. Its config,
failure record, and settling trace were moved intact from `raw/` to
`interrupted-trials/p250000_w2_high_steady_r2-attempt-2/`.

Later resume attempts repeated the session's initial settling check. The
latest check passed with a one-minute mean of 43.76923076923077 C, exactly
3 C above the original 40.76923076923077 C baseline. It then stopped with
`FileExistsError` because the partial run 178 directory still occupied
`raw/`. No new matrix result was produced by that attempt.

The retry path under `raw/` is now free. The completed results, matrix,
baseline, code, and quality gates were not changed.
