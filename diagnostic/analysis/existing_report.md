# Existing follow-up: request timing audit

Source: `results/followup/all-in-one-v2/full/`. All 50 accepted attempts were checked against their completion file hashes. Each successful client request was matched to its server event by ID.

The remainder is calculated **for each request**: end-to-end latency minus server queue wait minus elapsed processing. It contains client dispatch, HTTP handling, transport and response completion time. It does not identify which of these caused the delay.

| Study B bursty condition | Mean trial p99 end-to-end | Mean trial p99 remainder | Mean remainder share among slowest 1% |
|---|---:|---:|---:|
| 100.0 ms, 1 worker(s) | 700.5 ms | 43.1 ms | 0.7% |
| 100.0 ms, 4 worker(s) | 4131.7 ms | 4085.7 ms | 97.8% |
| 250.0 ms, 1 worker(s) | 387.1 ms | 111.7 ms | 21.5% |
| 250.0 ms, 4 worker(s) | 986.6 ms | 876.8 ms | 84.6% |

These p99 summaries are means of trial-level p99 values. The remainder p99 and end-to-end p99 select different requests; they must not be subtracted from one another.

In the 100 ms/four-worker cell, the mean dispatch lag among the slowest 1% was 0.565 ms. Their scheduled arrivals were split 0 in low-rate halves and 340 in high-rate halves. These aggregate phase counts do not identify the delayed stage.

The existing client timing begins at scheduled dispatch and ends after the response body is consumed. Server timing begins just before enqueue and ends when SHA work finishes. The service handler then awaits the worker reply and writes the response. Neither the handler wait after work nor client HTTP phases are separately timed in these results.

Next diagnostic: measure handler entry-to-admission, work-finish-to-handler-resume, and client request-written-to-first-byte and body-read intervals using durations within each process. Cross-process timestamp subtraction is invalid. These measurements can narrow the remaining duration; aggregate cgroup counters alone cannot assign it to a request.
