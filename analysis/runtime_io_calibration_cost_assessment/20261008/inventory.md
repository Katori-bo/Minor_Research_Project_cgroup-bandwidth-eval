# Calibration observation inventory

All listed records were collected in the completed original V28 study. No observations were newly collected. Monitor CPU samples have enclosing host-clock brackets; native sub-period counter files are absent. This assessment does not shorten any trial.

| Calibration trial | Role | Rate | Lifecycle (s) | Settling (s) | Measurement CPU (s) | Warmup + measurement offers | Measurement late/failed | Queue peak | Coarse CPU samples |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| cal_b1_steady15 | steady | 15 | 135.4 | 80.8 | 2.036 | 300 + 450 | 0 | 1 | 51 |
| cal_b1_steady120 | steady | 120 | 140.7 | 85.9 | 13.286 | 2400 + 3600 | 0 | 1 | 51 |
| cal_b1_idle0 | idle | 0 | 139.5 | 85.9 | 0.008 | 0 + 0 | 0 | 0 | 50 |
| cal_b1_steady60 | steady | 60 | 140.6 | 85.9 | 8.043 | 1200 + 1800 | 0 | 1 | 51 |
| cal_b1_mixed30 | mixed | 30 | 202.3 | 116.1 | 16.694 | 600 + 4596 | 992 | 104 | 81 |
| cal_b1_mixed15 | mixed | 15 | 177.0 | 91.0 | 14.088 | 300 + 3996 | 909 | 101 | 81 |
| cal_b1_steady90 | steady | 90 | 140.7 | 85.9 | 11.848 | 1800 + 2700 | 0 | 1 | 51 |
| cal_b1_steady30 | steady | 30 | 140.7 | 85.9 | 4.080 | 600 + 900 | 0 | 1 | 51 |
| cal_b2_steady30 | steady | 30 | 140.6 | 85.9 | 4.049 | 600 + 900 | 0 | 1 | 51 |
| cal_b2_steady90 | steady | 90 | 140.8 | 85.9 | 11.899 | 1800 + 2700 | 0 | 1 | 51 |
| cal_b2_mixed15 | mixed | 15 | 177.0 | 90.9 | 14.096 | 300 + 3996 | 1000 | 104 | 81 |
| cal_b2_mixed30 | mixed | 30 | 182.1 | 95.9 | 16.703 | 600 + 4596 | 948 | 100 | 81 |
| cal_b2_steady60 | steady | 60 | 140.6 | 85.9 | 7.984 | 1200 + 1800 | 0 | 1 | 51 |
| cal_b2_idle0 | idle | 0 | 144.6 | 90.9 | 0.008 | 0 + 0 | 0 | 0 | 50 |
| cal_b2_steady120 | steady | 120 | 140.7 | 85.9 | 13.244 | 2400 + 3600 | 0 | 1 | 51 |
| cal_b2_steady15 | steady | 15 | 165.7 | 111.1 | 2.031 | 300 + 450 | 0 | 1 | 51 |

No failed scientific attempts were recorded. Warmup offers were timely; all offers succeeded, so the not-timely counts above are deadline misses rather than HTTP failures. The reported queue peak is the waiting queue, excluding the executing job.

Original lifecycle starts precede per-trial settling, and finishes follow recording, replay and cleanup. Whole-life service CPU is not fully measured; inventory.json separately reports startup-to-final counter consumption and measurement CPU. Controller/estimator CPU and prior research acquisition are not included.
