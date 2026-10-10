# Complete retrospective calibration comparison

All 30 declared labels are shown. `spaced3`, `d_opt3` and `a_opt3` select the same rates and share results; they are not independent experiments. Existing validation outcomes were known. No standalone smaller acquisition procedure was run.

| Variant | Trials | Capacity (jobs/s) | Deadline MAE (pp) | Maximum error (pp) | ≤3 pp cases | Recorded selected lifecycle (s) | Measurement late/failed offers |
|---|---:|---:|---:|---:|---:|---:|---:|
| busy_5 | 1 | 149.500 | 0.407 | 1.571 | 16/16 | 202.3 | 992 |
| busy_6 | 1 | 149.417 | 0.453 | 1.714 | 16/16 | 177.0 | 909 |
| busy_11 | 1 | 149.500 | 0.407 | 1.571 | 16/16 | 177.0 | 1000 |
| busy_12 | 1 | 149.250 | 0.544 | 2.071 | 16/16 | 182.1 | 948 |
| busy_5_6 | 2 | 149.458 | 0.425 | 1.604 | 16/16 | 379.3 | 1901 |
| busy_5_11 | 2 | 149.500 | 0.407 | 1.571 | 16/16 | 379.3 | 1992 |
| busy_5_12 | 2 | 149.375 | 0.453 | 1.714 | 16/16 | 384.4 | 1940 |
| busy_6_11 | 2 | 149.458 | 0.425 | 1.604 | 16/16 | 354.0 | 1909 |
| busy_6_12 | 2 | 149.333 | 0.481 | 1.833 | 16/16 | 359.1 | 1857 |
| busy_11_12 | 2 | 149.375 | 0.453 | 1.714 | 16/16 | 359.1 | 1948 |
| busy_5_6_11_12 | 4 | 149.417 | 0.453 | 1.714 | 16/16 | 738.4 | 3849 |
| quadratic_spaced3_b1 | 3 | 160.696 | 16.119 | 35.952 | 8/16 | 420.9 | 0 |
| quadratic_spaced3_b2 | 3 | 160.340 | 16.119 | 35.952 | 8/16 | 425.9 | 0 |
| quadratic_spaced3_b12 | 6 | 160.509 | 16.119 | 35.952 | 8/16 | 846.8 | 0 |
| quadratic_d_opt3_b1 | 3 | 160.696 | 16.119 | 35.952 | 8/16 | 420.9 | 0 |
| quadratic_d_opt3_b2 | 3 | 160.340 | 16.119 | 35.952 | 8/16 | 425.9 | 0 |
| quadratic_d_opt3_b12 | 6 | 160.509 | 16.119 | 35.952 | 8/16 | 846.8 | 0 |
| quadratic_a_opt3_b1 | 3 | 160.696 | 16.119 | 35.952 | 8/16 | 420.9 | 0 |
| quadratic_a_opt3_b2 | 3 | 160.340 | 16.119 | 35.952 | 8/16 | 425.9 | 0 |
| quadratic_a_opt3_b12 | 6 | 160.509 | 16.119 | 35.952 | 8/16 | 846.8 | 0 |
| quadratic_d_opt4_b1 | 4 | 152.771 | 3.503 | 9.262 | 8/16 | 561.5 | 0 |
| quadratic_d_opt4_b2 | 4 | 152.976 | 3.747 | 9.738 | 8/16 | 566.5 | 0 |
| quadratic_d_opt4_b12 | 8 | 152.873 | 3.615 | 9.500 | 8/16 | 1128.1 | 0 |
| quadratic_a_opt4_b1 | 4 | 126.084 | 31.147 | 37.690 | 0/16 | 561.6 | 0 |
| quadratic_a_opt4_b2 | 4 | 126.241 | 31.147 | 37.690 | 0/16 | 566.7 | 0 |
| quadratic_a_opt4_b12 | 8 | 126.163 | 31.147 | 37.690 | 0/16 | 1128.3 | 0 |
| quadratic_all6_b1 | 6 | 148.369 | 1.224 | 3.738 | 13/16 | 837.6 | 0 |
| quadratic_all6_b2 | 6 | 148.558 | 1.057 | 3.381 | 13/16 | 873.1 | 0 |
| quadratic_all6_b12 | 12 | 148.463 | 1.169 | 3.619 | 13/16 | 1710.7 | 0 |
| historical_whole4 | 4 | 139.669 | 13.494 | 16.905 | 0/16 | 738.4 | 3849 |

All fits were available and answered all 16 cases. Costs above are sums of observed lifecycle components for selected trials, excluding shared initial collection overhead of 602.2 s, shared functional trial lifecycles of 48.0 s and unmeasured preparation/prior asset costs. These are not measured standalone savings. Actual chronological availability and the full cost vector are in report.json.

Two-point busy repeats pass the retained 5% range reference in all six declared pairs. Singletons have no across-trial repeatability test.
