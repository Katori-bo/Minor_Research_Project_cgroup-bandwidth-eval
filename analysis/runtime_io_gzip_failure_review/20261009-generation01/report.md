# Gzip qualification: verified queue-domain exit

Generation 01 stopped after seven services and 391.693 seconds (6.53 minutes).
Three complete pairs passed. The first service of pair 4, p4_observed, failed
the predeclared queue-domain gate: 197/200 offers (98.5%) had enqueue-to-worker
acquisition time <=100 us, while the requirement was >=99% (198/200).
The three exceedances were 132.037, 100.468 and 113.252 us. No observations are
rounded to change their classification. The failed trial remains failed.

All 1,400 measurement offers and 175 warmup offers returned matching full gzip
bodies and request IDs. All 1,582 native jobs, including seven correctness
requests, verify identity/affinity/cgroup/pidfd/exec/reap and body size. Each
measurement window has zero increments of both nr_throttled and throttled_usec;
startup/warmup counter values are separate. Dispatch gates, raw timing joins,
owned cleanup, source/runtime identities, actual one-CPU snapshots, root
observer inventory, evidence file sets and hashes verify for all seven services.
The original failure replays exactly, and all failed-trial raw records survived.

For the three longer queue intervals, the preceding worker release occurred
180.852317, 180.181956 and 180.822303 ms before the new request's enqueue.
The new request therefore did not wait behind the preceding compression job.
The recorded queue interval includes dispatcher critical-section work, worker
wakeup/scheduling, mutex reacquisition, dequeue and work before the acquisition
timestamp. This is the declared implementation boundary, not proof of backlog
or an identified operating-system fault. No scheduler trace resolves these
components. The failed trial's median offered-to-full-body latency was 20.426 ms;
its queue exceedances were 0.100468–0.132037 ms.

Seven completed traffic cohorts cannot establish the required six-pair observer
cost result. Qualification is unavailable and no scientific calibration or
held-out forecast validation began. This applicability limit neither confirms
nor refutes V31's prediction in its original tested domain and establishes no
novelty or independent replication.

Do not rerun this fixed pilot, discard the failed cohort, or relax 100 us/99%
after seeing the outcome. The useful next step is a timing-boundary and model
applicability review using these saved records, before choosing another service
or proposing a separately justified prospective revision. Any later changed
candidate must retain this result and explicitly declare its changed scope.
