# V18 service bridge partial review

The original capture seal and all frozen source hashes verify. The three successful
controls replay against their saved validations and summary: two-CPU quota work,
G1 uncapped HTTP and G2 uncapped HTTP. The known workload records 38 closed per-CPU
quota intervals, 19 throttled periods and 19 certain cross-CPU overlaps. Per-CPU
intervals remain separate. Both uncapped HTTP cases record no quota intervals.

The capped G1 case has 36,870 loss-conserved events, empty diagnostics, 272 throttle
attempts but zero successful quota transitions; nr_throttled=0. It uses 962,067 us
CPU during two seconds of offered arrivals. All 227 requests complete without
client errors or 503s. This did not exercise the required positive control. It is
not accepted as a successful capped qualification and is not evidence about the
historical late-response cause. The G2 capped case was not launched.

All four attempted cases report clean scoped detach/cgroup cleanup; root trace
controls match before/after. The old failed summary and every sealed file remain
unchanged. Three successful controls are retained with explicit original origins,
not rerun or counted as new independent replications. A temporary-copy check rejects
altered raw evidence.

The revised remaining HTTP positive controls double rate to 226.42 rps, offering
453 requests over two seconds with unchanged original service/client and quota.
Collector, loss, pairing, thread, clock and cleanup gates stay strict. This changes
functional fixture demand, not the planned performance pilot. Root continuation
will reverify retained evidence before/after collecting only G1/G2 capped cases.
No observer-cost result or HTTP mechanism is established.
