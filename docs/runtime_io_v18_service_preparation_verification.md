# V18 service bridge preparation verification

Prepared 2026-10-04. This verifies the implementation and non-recording startup/
HTTP/clock preflights. It does not verify the new root collector against the real
service, qualify observer overhead, or explain late HTTP delivery.

- [Protocol](runtime_io_v18_service_bridge.md).
- Runner: `diagnostic/kernel_service_bridge.py`; native gate: `kernel_start_gate.c`;
  observer: `kernel_bridge.bt`; fail-closed analyzer: `kernel_bridge_analysis.py`.
- Sealed assets: `analysis/runtime_io_v18_service_bridge_assets/seal.json`.
- [Four-case HTTP preflight summary](../analysis/runtime_io_v18_service_bridge_preflight/20261004T133114Z/summary.json).

## Completed checks

The complete retained V16 build file seal matches. Original image
`sha256:9d4e51d8a227ea7b3d4ef32d2fe9df7db23111f4a17ae7ae3e199f0dec064ce5`,
server SHA-256 `b7d249454d5477ffa0ade7cf1d90ba0eee8157ee166bb6e3f71d4cf912400efd`
and retained client SHA-256
`03a3876212b87508c64489c79c612e1c757b3916c488fc2bda393ad957f9ac5e` remain
the inputs. The service binary is not rebuilt, bind mounted or instrumented anew.

Native gate compiles statically with warnings treated as errors; ELF has no
dynamic interpreter. An actual unquotaed native gate test verifies the initial
single-thread stop, resume, fork, pinning to CPUs2,4 and successful joins. Original
server/client runtime.nanotime1 and time.now disassembly records CLOCK_MONOTONIC
clock ID 1 through vdsoClockgettimeSym with syscall fallback. Namespace/empirical
clock mapping checks still apply to each root case.

Twenty-six Python tests pass, including two-CPU state separation, snapshot race
bounds, missing final switches, unknown fork parents, CPU escape, uncapped quota
and lost-event rejection, composed clock bounds, generation reset, inconsistent
anchors and excessive clock uncertainty. Shell syntax, Python compilation and
native bpftrace formatting pass. BPF formatting does not attach probes.

The Docker preflight exercised the actual static launcher in the scratch image,
its FIFO handshake, original HTTP service and retained client for all four cells:

| Case | Offered requests | Composed kernel/client clock uncertainty |
|---|---:|---:|
| G1 uncapped | 227 | 0.522 ms |
| G2 uncapped | 227 | 0.561 ms |
| G1 quota | 227 | 0.459 ms |
| G2 quota | 227 | 0.473 ms |

Entry accounting and drain pass in every cell. Actual image ID, CPUs2,4 and sole
read-only qualification mount verify. Output seal matches, and asset/source
verification passes after all cases. These are normal-desktop functional timings,
not performance-effect estimates. No BPF collector was attached in the preflight.

## Retained failures and remaining work

The first preflight was blocked by sandbox access to Docker; the elevated tool
retry reached Docker and exposed the unsuitable self-SIGSTOP barrier at container
PID 1. Both failures remain sealed. The corrected FIFO preflight passed. Earlier
prepared versions are preserved under
`analysis/runtime_io_v18_service_bridge_preparation_history/` and are not current
assets. Existing V12–V17 results and V18 primitive captures were unchanged.

The next step is the [external root launcher](runtime_io_v18_service_bridge.md#launch-after-preparation).
It requires local terminal sudo authentication, which the assistant process
cannot reuse. Review raw root events, effective settings/uncapped ancestry,
thread conservation, quota pairs, request clock bounds, owned resource cleanup
and unchanged root tracing controls before accepting service compatibility.
The twelve-trial cost pilot remains unprepared; no automatic launch follows a pass.

## Revision after the first root bridge capture

The [partial review](../analysis/runtime_io_v18_service_bridge_review/20261004T135227Z-94326/report.md)
verifies the original seal and replays three accepted root cases. Known two-CPU
work records 38 quota intervals, 19 throttled periods and 19 certain cross-CPU
overlaps. Both uncapped HTTP cases pass thread/clock coverage with no throttling.
The fourth G1 capped case records 272 attempts but no successful intervals and
nr_throttled=0; its 962,067 us CPU over two-second arrivals did not exhaust quota.
This case remains unqualified, and G2 capped was not launched. All attempted cases
have clean scoped cleanup and unchanged root tracing controls.

Only the capped fixture rate increases to 226.42 rps, yielding 453 offered requests
over two seconds. This adjusts functional positive-control demand; it is not a
paired performance treatment. Original service/client, native gate, kernel/BPF
collector and analyzer semantics remain fixed, with strict positive-control,
loss, identity, clock and cleanup checks retained.

The current asset seal references the original capture's seal and path. Continuation
rechecks every retained file/frozen source and original inputs, replays all three
accepted validations and records explicit case origins. Only two capped cases
will be collected. The old failed case is not imported. A temporary-copy check
rejects an altered raw event file. Twenty-nine Python checks, shell syntax, native
gate compilation/test, asset verification and retained-source replay pass.

The [revised HTTP/counter preflight](../analysis/runtime_io_v18_service_bridge_preflight/20261004T142224Z/summary.json)
passes both remaining cells: 453 offered each, clock uncertainty 0.504/0.501 ms and
nr_throttled=30/33. Before/after CPU counters and deltas are retained and sealed.
This confirms actual quota exhaustion before another privileged observer capture.
Earlier preparation versions and preflights are preserved. Root continuation
remains pending, and observer overhead is still unqualified. The external command
is unchanged; its output will state that three passing cases are retained.

## Completed root continuation and raw review

The user completed `20261004T142940Z-97399`; [derived review](../analysis/runtime_io_v18_service_bridge_review/verified-20261004T142940Z-97399/report.md)
verifies full capture/asset/frozen-source seals and retained origins. Both fresh
event/thread lifecycles, original request classifications, clock joins and direct
kernel request bounds replay exactly against saved validations and the summary.
Recorded detach/cgroup cleanup passes and root tracing controls match before/after.

G1 capped: 453 offered, 4,577 received events, 30 closed per-CPU quota intervals,
nr_throttled=29 and composed clock uncertainty 0.598080 ms. G2 capped: 453 offered,
4,960 events, 64 closed per-CPU intervals, nr_throttled=33 and uncertainty 0.585887 ms.
Both CPUs2,4 are observed. Counters stop before container shutdown, and per-CPU
interval counts are not whole-service pause counts or equal to period counters
in general. All five compatibility cases are now verified, with the three retained
controls attributable to their original capture; they are not new replications.

The short G1 capture also retains 36 late successful 500 ms responses with
computation certainly before that deadline under original clock bounds. This
shows the symptom alongside kernel records at the revised functional load.
Observer overhead and causal interpretation remain unqualified. The twelve-trial
off/on cost implementation is the next preparation task; do not rerun this gate.
