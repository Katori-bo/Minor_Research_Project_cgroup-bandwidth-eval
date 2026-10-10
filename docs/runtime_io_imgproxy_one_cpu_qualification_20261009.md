# New one-CPU imgproxy qualification

This prospective engineering candidate preserves the original failed imgproxy
pilot, its frozen collector, and the subsequent clean forensic probe. Neither
run qualifies instrumentation cost or confirms application transfer.

The declared engineering reason is to constrain simultaneous native CPU execution.
Allow only logical CPU 2 instead of CPUs 2,4. Verify cpuset.cpus.effective=2 at
startup and throughout collection; merely setting an application worker or Go
processor count would leave native execution unconstrained. This is a new resource
condition, not an exact repetition of the original pilot. It does not establish
what caused that pilot's throttle or guarantee that another throttle cannot occur.
The single-CPU allowance does not reserve that CPU exclusively from host tasks.
Background work can still interfere with image processing on the allowed CPU.

Reuse the pinned stock and observed images, input, resize/JPEG operation, original
full-response client and ownership/lifecycle helper closure. Keep quota 25 ms per
100 ms, burst zero, GOMAXPROCS=1, worker=1, queue=128, memory=512 MiB and PID
limit=128. Do not tune GC, the upstream periodic memory freeing, image size, rate
or quota. Supervisor/client affinity remains CPUs 0,1. No counter sampler is
added to the cost pilot. One filesystem-thread snapshot before and after each
measurement window remains a descriptive check. It does not establish absence of
background interference or equality of CPU demand and worker hold duration.

Preparation permits exactly two functional services, stock then observed, without
retries: one decoded image check and eight paced offers per arm. Check original
image-body identity, dimensions, all-offer IDs, timing-header/raw-event joins,
actual packaged executable, resources, watchdog and owned cleanup. Preparation
timings with Codex open are not performance evidence. Seal the new protocol,
runner/test/launcher sources, functional evidence and review before the pilot.
The original sealed bundle protects reused helper sources, binaries and client.

Pilot: six pairs with stock,observed and observed,stock orders alternating, twelve
services total; ten seconds settling before each service, 25 warmup offers and
200 measurement offers, both at 5 req/s (200,000,000 ns spacing). No replacement,
retry, overwrite or resume. Hard active-service limit 120 s; total budget 1200 s
including 120 s cleanup reserve. Independent frozen owner-death/timeout watchdog
removes only the nonce-verified immutable container and owned client process.
Require fresh privileged read-only observer inventory and Codex/ChatGPT closed.
The run changes no host tracing or frequency controls.

Preserve each observed service's bounded raw server buffer after traffic drains
and before testing the zero-throttle gate. Export attempts save even incomplete
or overflowed data. Early failures attempt a bounded best-effort export before
cleanup and retain an explicit export limitation if it fails. CPU counters
bracket measurement before export. Preserve and seal unsuccessful pilot evidence.

Acceptance rules match the original qualification: every offered request must
succeed with matching complete JPEG body hash and echoed ID; dispatch p99 <=2 ms,
maximum <=10 ms; observed queue<=100 us for >=99% of measurement offers; zero
recorded measurement throttled periods in both arms. Failures terminate this
candidate and remain in its evidence. Do not weaken these rules after collection.

Both cost endpoints (whole-cgroup CPU per offer and median offered-to-complete-body
latency) use six paired relative changes. Their 95% t upper bounds are
mean + 2.571*sample_sd/sqrt(6), and each must be <=5%. All twelve services must
meet the timing/domain rules. Offline replay reconstructs raw joins, counter
deltas, image/resource identities, all paired endpoints and confidence bounds.
These engineering margins are not a power calculation for the later science.

Even success leaves ready_for_scientific_collection=false. Review background
interference, stage boundaries and model assumptions, then separately freeze
fresh calibration and held-out validation. Never import V31 forecasts or treat
this engineering pilot as the eighteen-trial application-transfer experiment.
This candidate cannot establish a causal mechanism for the earlier failure,
hardware generality, independent-team replication, or novelty.

Evidence: analysis/runtime_io_imgproxy_one_cpu_qualification/generation-01/.
External launch: bash diagnostic/start_imgproxy_one_cpu_qualification.sh.
Offline completed-pilot replay: python3 -B diagnostic/imgproxy_one_cpu_qualify.py replay.

The CPU allowance semantics are documented at
https://docs.kernel.org/admin-guide/cgroup-v2.html#cpuset-interface-files.
