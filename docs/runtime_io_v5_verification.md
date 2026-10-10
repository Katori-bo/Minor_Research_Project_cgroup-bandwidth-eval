# Runtime/I/O revision 5 verification

Verified on 2026-10-01. These are functional checks, not performance results.
No revision-5 pilot or full matrix was launched.

## Changes

- Request ID zero is distinct from an unknown socket-write association.
- Connection Active, Idle and Closed callbacks bracket parsing/handler entry and
  completion of final response flushing. The runner waits for pending final
  responses, and the trace stop endpoint refuses to truncate them.
- Request analysis includes connection context before handler entry, post-parse
  delay, handler stages, individual socket writes, final flushing and cleanup.
  Every interval reports Go scheduler states and other completed jobs.
- Go Running is named `go_running_ns`; it does not prove CPU execution throughout
  the interval. OS descheduling and quota throttling remain possible within it.
- All client outcomes are retained. Observed failures need the same lifecycle
  integrity as successes, with worker evidence for every admitted job. Failures
  never observed at the server remain explicitly unobserved.
- Broken scheduler transition chains, missing initial/interval coverage, missing
  task or connection events, duplicate IDs, invalid clock mapping and incomplete
  captures fail validation. Validation recomputes derived analysis from retained
  scheduler/I/O evidence.
- The current build uses schema 6, `quota-diagnostic-service:4`, and a new
  `results/diagnostic/runtime-io-v5` session. Workload and pilot thresholds are
  unchanged.

## Results

| Check | Result |
|---|---|
| Pinned Go 1.26.1 service tests | Passed: 11 tests |
| Python configuration, validation and analyzer tests | Passed: 23 tests |
| Service image build and build seal | Passed |
| Load-generator image build | Passed; unchanged source used cached tested build |
| Python compile checks and shell syntax | Passed |
| Launcher help | Passed; pilot remains the default |
| Actual Go runtime trace parse and request analysis | Passed |

The functional fixture made four HTTP work requests: two successes (including
ID zero), one real queue rejection, and one real client timeout whose admitted
job subsequently completed. It also reused a connection for a control request
between work requests, verifying that its write was not assigned to the previous
work ID. The raw trace contained 708 parsed runtime events; the two clock anchors
intersected in an offset interval 672 ns wide. Final socket writes and connection
completion were matched, including for the failed requests. Separate tests
injected a socket write error, checked instrumentation-disabled behavior, and
proved trace stop refuses undrained final responses.

Python tests additionally removed scheduler states, handler exits, admission
markers, task ends and final connection boundaries; corrupted task and clock
associations; supplied incomplete captures; and checked a runnable post-handler
gap while another job completed. These cases are rejected where evidence is
missing or corrupt. A timeout never observed by the server stays in the output
with no invented server state. A read that could contain multiple requests keeps
its ambiguous framing classification.

Retained functional evidence (outside performance results):

- [Request tables](../diagnostic/verification/runtime-io-v5/trace_report.md)
- [All outcomes and intervals](../diagnostic/verification/runtime-io-v5/trace_requests.json)
- [Raw artifact and source hashes](../diagnostic/verification/runtime-io-v5/verification.json)

## Launch

During a quiet measurement window, from the repository root:

```bash
cd /home/Aditya/Desktop/Research_project/cpu-quota-tail-latency
bash diagnostic/run_all.sh --directory results/diagnostic/runtime-io-v5
```

Status:

```bash
bash diagnostic/run_all.sh status --directory results/diagnostic/runtime-io-v5
```

The launcher builds/verifies, collects six pilot trials, analyzes them, and stops.
A failed validation or overhead screen stops for review and retains its evidence.

## Remaining interpretation limits

The pre-handler connection context includes idle time and read-ahead. It does
not locate the arrival of bytes for a particular request. A buffered or pipelined
request can lack a separate Active callback and is labeled accordingly. Final
socket-write completion does not prove peer delivery. Go Running does not
separate active CPU execution from OS throttling/descheduling. These limits are
included in every request report; the diagnostic cannot turn them into a cause
claim automatically. Actual performance overhead and the cause of the long tail
remain untested until the quiet-window pilot is collected and reviewed.
