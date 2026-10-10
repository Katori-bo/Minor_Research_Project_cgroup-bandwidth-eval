# V31 verified findings and next research step

V31 generation-01 completes with `low_queue_timing_prediction_confirmed`.
The sealed result review is
`analysis/runtime_io_v31_result_review/20261009-generation01/report.md`.
The extension manuscript now separates the V30 timing-CDF discovery from the
fresh V31 confirmation in Section 9. V1 and the frozen V30/V31 evidence remain
preserved.

The complete record has sixteen fresh calibration trials, eighteen new-rate
steady validation trials and 12600 measurement offers. The calibration CDF
uses 676 paired timings across four cohorts. All validation trials qualify
technically and remain inside the declared scientific domain. There are zero
measurement throttled periods; the smallest trial queue<=100 us fraction is
99.825% of all offers. There are no technical retries. Forty released services
and one unreleased preflight have successful owned cleanup. The campaign
takes 113.0 minutes.

At 10 ms the paired CDF has 1.844 pp equal-profile/block mean absolute error,
compared with 67.340 pp for periodic+delay. Improvement is positive in all six
blocks, with mean 65.495 pp and declared 95% t interval [63.925,67.065] pp.
All frozen gates pass. The CDF classifies all eighteen trials correctly at
both 10 and 12 ms: all fail the 5% budget at 10 ms, and all have zero observed
misses at 12 ms.

The claim remains narrow. Individual 10 ms error reaches 5.055 pp; paired-CDF
mean error at 10.5 ms is 3.852 pp. The independent convolution is better at
secondary 9 ms. The 12 ms decision endpoint is well separated from 5%, and
periodic forecasts also succeed there. Cohort-only predictions vary; the
leave-one-cohort-out audit is descriptive. Stage-clock ambiguity remains
material. There is no causal phase explanation, universal forecast, overload
capability, rate-selection rule or independent-service transfer result.

The independent review replays the frozen completion verifier and separately
reconstructs the paired calibration samples, offered misses, raw measurement
throttling and queue-domain fractions, forecast aggregates, block errors,
confirmation gates, stage conservation and cleanup/lifetime counts.
It neither refits the frozen result nor launches measurements.

The next research step is to consolidate the empirical claim, then predeclare
one independent service or host replication. Its measured timing contract,
fresh calibration, offered workload, domain criteria, deadline/decision gates
and resource/runtime qualification must be specified before collection. The
purpose is to test transfer of the surviving low-queue timing boundary.
Additional SHA sweeps on this same host do not resolve that question.
No next-generation collector or further collection is started by this finding.
