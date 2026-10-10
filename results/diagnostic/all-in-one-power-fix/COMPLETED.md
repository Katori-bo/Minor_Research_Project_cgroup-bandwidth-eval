# CPU quota timing diagnostic completed

Completed: 2026-09-30T04:56:27.961094+05:30

- Pilot: 7 validated diagnostic trials.
- Full experiment: 20 validated trials.
- Research results exclude the pilot.

[All trial results](/home/Aditya/Desktop/Research_project/cpu-quota-tail-latency/results/diagnostic/all-in-one-power-fix/full/analysis/report.md)

[Trial CSV](/home/Aditya/Desktop/Research_project/cpu-quota-tail-latency/results/diagnostic/all-in-one-power-fix/full/analysis/trials.csv)

[Estimates and uncertainty](/home/Aditya/Desktop/Research_project/cpu-quota-tail-latency/results/diagnostic/all-in-one-power-fix/full/analysis/estimates.json)

[Attempt audit](/home/Aditya/Desktop/Research_project/cpu-quota-tail-latency/results/diagnostic/all-in-one-power-fix/full/analysis/attempt_audit.csv)

[Pilot checks](/home/Aditya/Desktop/Research_project/cpu-quota-tail-latency/results/diagnostic/all-in-one-power-fix/pilot/analysis/pilot_gate.json)

## Timing interaction

- e2e: 2808.47 ms (trial-bootstrap 95% interval 2572.54 to 3031.17 ms).
- pre_admission: 0.00 ms (trial-bootstrap 95% interval -0.00 to 0.00 ms).
- queue: 7.62 ms (trial-bootstrap 95% interval -83.15 to 78.94 ms).
- processing: -47.23 ms (trial-bootstrap 95% interval -51.87 to -40.38 ms).
- post_work: -99.36 ms (trial-bootstrap 95% interval -114.60 to -71.19 ms).
- request_to_first_byte: 2808.38 ms (trial-bootstrap 95% interval 2572.27 to 3030.75 ms).
- first_byte_to_body_done: 0.01 ms (trial-bootstrap 95% interval 0.00 to 0.01 ms).
- outside_measured_server: 3428.49 ms (trial-bootstrap 95% interval 3212.60 to 3626.85 ms).

These are trial-level timing estimates. Review the remaining client/server boundary and all failure rates before asserting a cause.
