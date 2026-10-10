# Ordinary timing models: V29 discovery comparison

Retrospective model development, with parameters restricted to calibration records. No new service experiment or measured replenishment phase.

| Context | Model | 25 ms MAE pp | 50 ms MAE pp | 100 ms MAE pp | 500 ms MAE pp |
|---|---|---:|---:|---:|---:|
| q050_small | fluid_busy | 3.451 | 1.517 | 1.020 | 0.479 |
| q050_small | fluid_quadratic | 6.686 | 6.733 | 9.469 | 29.436 |
| q050_small | fluid_busy_calibrated_delay | 3.688 | 1.611 | 0.948 | 0.548 |
| q050_small | periodic_zero_phase_full_budget | 1.294 | 3.299 | 5.250 | 1.201 |
| q050_small | periodic_uniform_phase | 2.626 | 4.839 | 6.692 | 1.736 |
| q050_small | periodic_uniform_phase_calibrated_delay | 2.354 | 4.659 | 6.420 | 1.636 |
| q025_small | fluid_busy | 3.158 | 2.329 | 0.648 | 1.359 |
| q025_small | fluid_quadratic | 6.366 | 6.584 | 6.229 | 23.301 |
| q025_small | fluid_busy_calibrated_delay | 3.555 | 2.330 | 0.599 | 1.181 |
| q025_small | periodic_zero_phase_full_budget | 0.499 | 1.489 | 3.532 | 5.395 |
| q025_small | periodic_uniform_phase | 1.786 | 3.137 | 5.711 | 7.107 |
| q025_small | periodic_uniform_phase_calibrated_delay | 1.690 | 2.981 | 5.577 | 6.973 |
| q050_large | fluid_busy | 5.176 | 3.093 | 0.952 | 0.672 |
| q050_large | fluid_quadratic | 8.497 | 8.670 | 11.455 | 29.994 |
| q050_large | fluid_busy_calibrated_delay | 5.296 | 3.133 | 1.132 | 0.734 |
| q050_large | periodic_zero_phase_full_budget | 0.755 | 2.065 | 4.362 | 1.241 |
| q050_large | periodic_uniform_phase | 1.530 | 3.776 | 6.094 | 1.837 |
| q050_large | periodic_uniform_phase_calibrated_delay | 1.385 | 3.548 | 5.777 | 1.774 |
| q025_large | fluid_busy | 20.624 | 2.979 | 0.555 | 1.295 |
| q025_large | fluid_quadratic | 20.624 | 6.899 | 6.754 | 23.568 |
| q025_large | fluid_busy_calibrated_delay | 20.624 | 3.029 | 0.982 | 1.295 |
| q025_large | periodic_zero_phase_full_budget | 0.528 | 0.616 | 3.406 | 4.375 |
| q025_large | periodic_uniform_phase | 1.485 | 2.277 | 5.232 | 5.959 |
| q025_large | periodic_uniform_phase_calibrated_delay | 1.386 | 2.164 | 5.090 | 5.756 |

Unknown phase is averaged uniformly over a sampled 1 ms grid, with full initial budget. This is an assumed prior, not an observed kernel phase. The separately reported scenario range includes full/empty starting balances and independently calibrated capacity extremes; it is neither a continuous envelope nor a guaranteed Linux bound. The ideal work-conserving budget server omits CPU-local retained slices, competing cgroup threads, CPU migrations and OS/runtime interference. Effective demand covers the whole busy service, not isolated SHA work.

The empirical non-queue delay distribution comes only from the four low-rate calibration trials, with queue wait <=100 us. It is appended independently of worker latency and does not consume additional modeled budget. That independence/transfer assumption may fail under load. No negative delay or validation residual is fitted.

Original busy-model errors reproduce at all six deadlines. V1 and all frozen V29 inputs remain untouched. Numerical tests independently compare the budget replay with discrete CPU-slot simulation, continuous service, spillover, idle-budget retention, queue rejection and delay CDF counting.

These are ordinary baselines informed by [Linux bandwidth control](https://docs.kernel.org/scheduler/sched-bwc.html) and established [reservation timing models](https://retis.santannapisa.it/people/nino/publication/TCC23.pdf). The latter uses guaranteed hierarchical real-time reservations and small-period assumptions; it is not a hard-bound algorithm reproduced here. Bandwidth ceilings do not justify a finite worst-case response-time guarantee without a lower service assumption.

Further conclusions and a prospective protocol must be written from these discovery results before a new experiment. Selecting the best phase from validation would be an oracle and was not used.
