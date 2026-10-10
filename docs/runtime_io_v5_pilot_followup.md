# Runtime/I/O v5 pilot follow-up (2026-10-02)

Two complete six-trial pilots were collected: `results/diagnostic/runtime-io-v5` and `results/diagnostic/runtime-io-v5-quiet-1`. All trials and enabled traces validated, but both pilots failed the frozen `failure_rates_not_worse` gate. Four-worker tracing-on trials rejected 3.9–4.4% of requests in the first pilot and 3.7–4.0% in the second; tracing-off trials rejected 0%. Lower successful-request p99 cannot be treated as an improvement when requests are rejected. The full matrix was not launched.

The first launch of `runtime-io-v5` also failed before measurement because temperature did not settle. Later reruns of that completed session only repeated analysis; they collected no new trials. Both completed pilots and their reports are retained.

Host monitors listed ChatGPT processes during every measured trial of both pilots, including the attempted quiet rerun. Baloo processes also appeared, as in older runs. Process-list presence alone does not establish their per-trial CPU impact. The repeated tracing-on rejection pattern is concerning, but its cause is not yet proven.

Next: preserve these sessions and inspect matched tracing-on/off request, queue, worker, scheduler, CPU and host-monitor evidence to locate the added delay. Check whether runtime/I/O tracing itself pushes this near-capacity workload into rejection. Do not relax the gate or reuse these sessions to claim a pass. If changing instrumentation or pilot design, document a new revision and collect a fresh session. Before any new quiet run, fully exit ChatGPT (`pgrep -a -x ChatGPT` should print nothing), suspend Baloo if desired, and verify the host monitor rather than assuming a closed window ended background work.
