# HTTP goroutines ready to run before handler entry

Saved-data follow-up to the v8 queue reconstruction, 2026-10-02. No workload launched. Scheduler/request/job files were checked against the queue review's retained input hashes.

| Block | Mode | Longest pre-handler Runnable span | Other worker completions during span | Request ID | Begins after previous cleanup |
|---|---|---:|---:|---:|---|
| 1 | trace | 2320.715 ms | 314 | 1713 | True |
| 1 | yield_trace | 88.466 ms | 7 | 1867 | True |
| 2 | trace | 2900.648 ms | 384 | 1695 | True |
| 2 | yield_trace | 88.379 ms | 8 | 547 | True |
| 3 | trace | 2208.931 ms | 298 | 560 | True |
| 3 | yield_trace | 86.839 ms | 6 | 794 | True |
| 4 | trace | 2611.479 ms | 356 | 664 | True |
| 4 | yield_trace | 85.930 ms | 6 | 1538 | True |

In all four non-yielding traced cells, the longest observed pre-handler Runnable spans are 2.21–2.90 seconds. They begin after the previous request's server cleanup on the reused connection has finished. During these spans, 298–384 other CPU jobs complete. The largest yielded counterparts are 85.93–88.47 ms, with 6–8 other completions.

This localizes an additional delay to the HTTP connection goroutine waiting to run before entering the next handler. It cannot be explained solely by waiting for the previous handler's cleanup to finish. Ready HTTP work and ongoing CPU job completion coexist; worker yielding substantially changes that scheduling pattern.

Spans are intersections with the conservative latest possible client request-write callback → handler-entry interval. A client write callback is not physical server arrival. The Go Runnable state does not identify the exact runtime queue, which scheduler policy chose another goroutine, or whether tracing affected wakeup behavior. Job completion counts are temporal overlap, not attribution of CPU time.

Same-state generation snapshots are joined into one span, not treated as new wakeups. The runtime/service clock mapping is independent of the causal client/service offset bracket. Both uncertainties are retained in `examples.json`. Trace-off goroutine states remain unavailable.

The next discriminator is raw trace wakeup/enqueue context and stacks at these saved span boundaries, including the accept goroutine where a connection handler does not yet exist. This requires examining retained runtime events; there is still no identified tracing call to patch or qualified transparent fix.

Reproduce after the queue review:

```bash
venv/bin/python diagnostic/inspect_prehandler_ready.py \
  analysis/runtime_io_v8_queue_review \
  --output analysis/runtime_io_v8_queue_review/prehandler_ready_fresh
```
