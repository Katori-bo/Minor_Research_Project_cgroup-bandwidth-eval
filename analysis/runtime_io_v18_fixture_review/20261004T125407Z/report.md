# First V18 fixture failure and repair

The original failed attempt seal verifies. The observer attached and returned zero, but the sleep capture remains invalid because of diagnostics. Root trace controls matched before/after, owned BPF program detach checks passed, and the empty temporary cgroup was removed; no cleanup errors were recorded. The quota fixture and full benchmark never ran.

Expected misses in ordinary map value lookups generated warnings under bpftrace -k, and discarded delete return values generated compiler warnings. Those are script mistakes, not evidence about late HTTP responses. The repair uses has_key for membership and checks deletion results; required quota-state lookup failures still produce explicit errors. Strict warning/error/loss validation and -k remain enabled.

Fourteen Python checks, launcher syntax and native syntax formatting of both the capture and the new map API guard pass. The new guard natively tests present/missing membership and deletion before starting workloads. Repaired root behavior is not yet verified. Run the same external-terminal fixture launcher to collect a distinct immutable source snapshot and attempt. Preserve the failed attempt; no warning suppression or retrospective promotion occurs.
