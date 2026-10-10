# V18 tool installation and capability review

The sealed installation evidence and exact nine-package installation delta verify; existing package versions are unchanged. Current BTF matches the sealed privileged inventory. All four tracing tools are installed. trace-cmd 3.4's version command prints its valid version banner and returns 255; the new assessment recognizes that specific behavior without changing the original sealed inventory.

All required scheduler events exist. The two throttle-named static events concern block I/O and memory reclaim, not CPU bandwidth. Typed fentry listings expose throttle_cfs_rq and unthrottle_cfs_rq with struct cfs_rq pointers; matching running-kernel image disassembly is retained. Actual fentry/fexit attachment and interval semantics still need the bounded fixtures.

Fourteen Python guard/evidence checks, shell syntax and native bpftrace syntax formatting pass. Ordinary unquotaed sleep/CPU worker checks pass. No privileged capture or performance batch has run. Sudo authentication from the external terminal is not available to the assistant's noninteractive process.

Next run `bash diagnostic/start_kernel_fixtures.sh` in an external terminal. Three known workloads use fresh, restricted cgroups and a bounded observer, retain raw output/counts and transition brackets, and verify owned resource cleanup plus root trace controls. A failed fixture stops qualification. Even passing fixtures do not qualify service observer overhead or request-level attribution.
