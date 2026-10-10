# V18: qualify external kernel observation of post-computation delays

Updated 2026-10-04, Asia/Kolkata. Tool setup and capability review come first;
this document is a staged plan, not a frozen collection protocol or ready batch.

Latest stage: all tools are installed and their sealed package/capability evidence
is verified. The [bounded fixture procedure](runtime_io_v18_kernel_fixtures.md)
passed actual root attachment, raw replay and cleanup review in
`20261004T125437Z-86644`; see the [verified report](../analysis/runtime_io_v18_fixture_review/verified-20261004T125437Z-86644/report.md).
Single-CPU basic observation is qualified. The [service compatibility gate](runtime_io_v18_service_bridge.md)
is verified across all five cases, with three retained original controls and two
fresh capped HTTP captures. The [completed bridge review](../analysis/runtime_io_v18_service_bridge_review/verified-20261004T142940Z-97399/report.md)
replays events, threads, request outcomes, clocks and cleanup. The earlier light
capped workload remains a failed positive control. Observer-cost implementation
and the twelve-trial batch remain pending. Do not rerun the passed bridge fixtures.

## Motivation and retained evidence

[V17](../results/diagnostic/runtime-io-v17-shared-loading-1/session/analysis/report.md)
completed all 16 trials and passed its frozen completion verification. The packaged
rebuilt image improves 500 ms timely success by 1.46–2.27 percentage points in all
four blocks. With a common executable backing file, the paired median is near zero,
but one block exceeds the 1-point margin. Loading/setup is a candidate contributor;
shared loading did not establish neutrality. V17 does not identify a filesystem,
cache or scheduler cause, nor resolve V15's nonmonotonic clock effects.

The original packaged arm retains 2,198 late successful responses whose main
computation certainly finished before 500 ms. Post-work p99 remains approximately
161 ms. Existing timestamps precede publication or measure handler execution;
they do not establish when a Go goroutine became runnable.

## Tool installation, separately from performance collection

The verified host is Arch Linux, running `7.2.8-arch1-2`; matching headers and
`/sys/kernel/btf/vmlinux` already exist. Its kernel config includes tracing,
kprobes, BPF, perf events and CFS bandwidth control. Ordinary-user tracefs access
is denied; `perf_event_paranoid=2` and unprivileged BPF is disabled. The read-only
sudo attempt could not authenticate noninteractively. No controls were relaxed.

Install official-repository `perf`, `trace-cmd`, `bpftrace` and `bpf` (bpftool).
The preview proposes these tools plus libtraceevent, libpfm, libtracefs, clang and
bcc: about 69.1 MiB downloaded; no existing package upgrades. The helper permits
only these nine names, requires the `extra` repository, refuses existing package
replacement, and compares the complete installed-package map, sync DB hashes,
pacman config, helper hash and running kernel against the recorded preview.

Run as the normal user in an external terminal, authenticating sudo locally:

```bash
bash /home/Aditya/Desktop/Research_project/cpu-quota-tail-latency/diagnostic/install_kernel_tools.sh
```

The installer uses the existing synced package database with no database refresh
or full system upgrade. Normal dependency and package-signature checks apply;
it never forces file overwrites or bypasses dependency checks. A changed preview,
package lock, dependency outside the scope, mirror failure or installation error
stops the procedure. Preserve the log and review the failure; do not remove locks,
disable signature checking or silently switch to a system upgrade.

After installation it saves the actual tool versions, scheduler event formats,
quota event/function candidates, BTF identity and typed fentry probe listings.
Listing probe metadata does not attach a recording program. It does not mount
tracefs, alter tracing controls, change sysctls or boot configuration, install a
kernel, create sudoers rules or start a service. It starts no performance batch.
Each invocation writes a distinct evidence directory under
`analysis/runtime_io_v18_kernel_setup/`, with a SHA-256 setup seal when successful.

## Capability and short-fixture gates

1. Review the privileged inventory. Require scheduler switch/wakeup/fork/exit
   coverage and an exact account of service host PIDs/TIDs, including new threads
   and exits. Confirm actual CPU restrictions and cgroup ancestry.
2. Prefer supported quota tracepoints if their semantics suffice. Otherwise review
   running-kernel BTF and source semantics for targeted throttle/unthrottle probes.
   Symbol presence alone does not verify attachability or a quota mechanism.
   Do not reinterpret switch-out events as quota exhaustion.
3. Build bounded fixtures with known CPU execution, sleep and quota-limited work.
   Establish what each event means, pairing rules, CPU/cgroup scope and initial
   state. Per-CPU throttling is not automatically a process-wide pause, and nested
   ancestors or overlapping intervals cannot be added as independent lost time.
4. Qualify monotonic clock mapping to retained service/client clock brackets,
   resolution, ordering and ambiguous boundaries. Retain raw events, lost-event
   counts, buffer limits and collector exit status. Thread identity is not Go
   goroutine identity; publication and handler readiness remain unobserved.
5. Use a uniquely owned trace instance or per-process BPF resources, bounded buffers
   and timeouts, and explicit detach/cleanup on normal exit, interruption and error.
   Verify root tracing state before/after; preserve other users' tracing sessions.
   No all-function tracing, broad uprobes or runtime rebuild by default.

If actual quota events cannot be qualified, narrow the claim to execution/off-CPU
observations or stop that attribution route. Do not promise per-request throttle
intervals from aggregate cpu.stat counters.

## Next preparation: bounded service compatibility

The known quota workload produced 190 throttle attempts but only 18 successful,
closed quota intervals, with a duration-midpoint median of 49.461342 ms. Both
uncapped controls produced no quota intervals. The recorded kernel counter is
18 throttled periods in this single-CPU capture. Do not extend that count equality
to the service's two CPUs or treat every function call as a pause.

Before the cost pilot, implement and qualify the collector against the original
packaged service, without rebuilding it or adding inline markers. This is a
short functional gate, not a performance comparison or a new intervention:

1. Exercise a known two-CPU quota workload on CPUs2,4. Retain separate runqueue
   intervals and scheduling records; explicitly exercise overlapping per-CPU
   intervals. Reject identity/loss/pairing failures and never sum overlapping
   intervals into a claimed whole-service pause.
2. Validate exact service host PID/TID and cgroup filtering before startup or with
   a verified initial-state barrier. Include existing and newly created Go threads,
   final switches and exits; an enumeration performed during live thread creation
   is insufficient. Freeze the chosen filter/startup procedure before collection.
3. Inspect every cgroup ancestor and require uncapped ancestors for this scoped
   pilot. If that condition fails, stop rather than silently attributing an
   ancestor's throttling to the observed leaf. Save effective CPU restrictions.
4. Run bounded HTTP checks for GOMAXPROCS=1/2 with uncapped and 50 ms/100 ms
   allowance on CPUs2,4, retaining the exact original image, workers=4, zero burst
   and packaged executable. GOMAXPROCS=2 is a coverage check, not a performance
   treatment for the later GOMAXPROCS=1 pilot.
5. Qualify the CLOCK_MONOTONIC mapping and uncertainty against the retained Go
   service/client clock brackets. Retain ambiguous overlap as ambiguous; don't
   replace handler execution with runnable readiness. Require complete capture
   through workload drain and scoped detach/cleanup as in the primitive fixtures.

The [implementation/protocol](runtime_io_v18_service_bridge.md) and revised sealed
assets are prepared. The [first root bridge review](../analysis/runtime_io_v18_service_bridge_review/20261004T135227Z-94326/report.md)
verifies three accepted controls: 38 two-CPU quota intervals and 19 cross-CPU
overlaps, plus both uncapped HTTP captures. The G1 capped case has zero quota-state
intervals and nr_throttled=0, so it failed the positive control; G2 capped was not
run. Its error, raw outputs and source remain sealed. All attempted cleanup and
root tracing checks passed.

The two remaining capped fixture rates are now 226.42 rps over two seconds, 453
offered each. Their [non-recording preflight](../analysis/runtime_io_v18_service_bridge_preflight/20261004T142224Z/summary.json)
passes accounting/clock checks and records nr_throttled=30/33, confirming that the
revised workload actually exercises the cap. Strict observer gates remain unchanged.
The user completed continuation `20261004T142940Z-97399`. Its [verified review](../analysis/runtime_io_v18_service_bridge_review/verified-20261004T142940Z-97399/report.md)
retains the three original controls and replays two fresh capped HTTP captures.
G1 records 30 closed per-CPU quota intervals and nr_throttled=29; G2 records 64
intervals and nr_throttled=33. Counter windows end before process shutdown, while
event capture includes final exits. These are CPU/runqueue intervals, not numbers
of whole-service pauses. Both service CPUs are observed, 453 offered requests
conserve per capped case, composed clock uncertainty is 0.598/0.586 ms, diagnostics
are empty and scoped cleanup/root tracing checks pass. No accepted capture was
rerun and the original failed case is not promoted.

The traced short G1 case includes 36 late successful 500 ms responses whose
computation certainly completed before the deadline, including 14 with at least
50 ms margin. This establishes the symptom and kernel records in one functional
capture; it does not explain the historical miss count or qualify observer cost.
No request/quota-overlap attribution is performed before that cost review. The
next performance collection is the off/on pilot below; extend and qualify its
collector lifetime/capacity and root supervision before declaring it ready.

## Proposed observer-cost pilot after fixture verification

Provisionally six matched off/on pairs (12 trials), three orders of each kind,
with the exact original retained image and its packaged executable in every arm.
No service build, bind-mount treatment, inline clock or recording-path changes.
Use the same collector lifecycle in each arm, with attachment enabled only in on;
declare startup/filter/CPU affinity and measured window before collection.

Retain GOMAXPROCS=1, workers=4, queue=128, 44,000 SHA iterations, quota/period
50 ms/100 ms and zero burst credits, the exact V12 client, identical arrival
vectors within pairs, scheduled-arrival all-offered denominators, full drain,
and separately measured/sealed quiet-host thermal/power baseline.

Proposed practical screen: every paired 500 ms and 1,000 ms success delta within
1 percentage point, failure delta within 0.1 point, CPU/job within 5%, successful
p99 within 10%; missing/non-finite outcomes or incomplete trace coverage fail.
Report all paired effects and block-level uncertainty. Six pairs do not establish
statistical equivalence, absence of observer effects or a causal mechanism.
Freeze the final protocol and implementation before collecting this pilot.

Only after observer review correlate bounded computation-to-handler intervals
with qualified CPU execution and throttling evidence. Continued service execution
rejects a continuous whole-service freeze for those parts of an interval; it does
not establish that the particular handler was ready, nor prove unfair scheduling.
Throttling overlap is contribution evidence, not automatic attribution of the
entire delay or proof that shortening the period will recover each missed response.

## Primary references

- [Arch package group](https://archlinux.org/groups/x86_64/linux-tools/) and
  [bpftrace package](https://archlinux.org/packages/extra/x86_64/bpftrace/).
- [pacman transaction/preview semantics](https://man.archlinux.org/man/pacman.8.en).
- [Kernel event formats and filtering](https://docs.kernel.org/trace/events.html).
- [CFS bandwidth control](https://docs.kernel.org/scheduler/sched-bwc.html).
- [ftrace instances, buffers and lost events](https://www.kernel.org/doc/html/latest/trace/ftrace.html).
- [bpftrace kernel probe types and BTF](https://bpftrace.org/hol/kernel-probes).
