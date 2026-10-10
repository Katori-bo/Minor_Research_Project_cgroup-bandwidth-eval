# Protected leftover-observer audit: ownership review

Reviewed 2026-10-06. The root inventory is complete, with no missing sections.
Its original conservative BPF flags remain preserved. The separate ownership
review is bound to its exact hash; no system object was detached or removed.

Evidence:
[root audit](../analysis/runtime_io_leftover_observer_audit/audit-20261006-root-01.json)
and [ownership review](../analysis/runtime_io_leftover_observer_audit/audit-20261006-root-01.review.json).

## Findings

- No collector process candidates or open perf-event descriptors were found.
- Tracefs has the nop tracer, zero enabled events, no defined kprobes/uprobes
  or dynamic events, and no additional instances. Root controls are unchanged
  across the inventory. `tracing_on=1` does not imply active event/function tracing
  with these other controls disabled.
- Twenty-five of the 26 BPF programs have PID1 systemd descriptor holders and
  expected filesystem/device/firewall policy names and types. The sole BPF link
  targets its filesystem-policy LSM program. These are system-service policy
  objects, not an experimental scheduler/CPU collector. Systemd's
  [device-policy source](https://raw.githubusercontent.com/systemd/systemd/main/src/core/bpf-devices.c)
  and [firewall source](https://raw.githubusercontent.com/systemd/systemd/main/src/core/bpf-firewall.c)
  explain these program classes.
- Program1284 is a socket filter referencing only map396. That small hash map
  is held by root NetworkManager PID542, also verified in the process inventory.
  The classification associates this filter with NetworkManager through that
  shared map. Its socket owner was not directly attributed; do not upgrade the
  association into a proved exact loading path or claim unchanged network state.
  Its recorded load time is October5 at23:34:19 +05:30, during the pilot setup.
  Timing coincidence does not make it a perf collector or explain the reversal.
- Map10 belongs to the systemd filesystem policy. Maps406/407/408 are
  libbpf_global, pid_iter.rodata and libbpf_det_bind. Their types/shapes match
  known bpftool/libbpf inventory infrastructure; pid_iter.rodata explicitly
  lists a bpftool holder. The Linux
  [BPF selftest](https://github.com/torvalds/linux/blob/master/tools/testing/selftests/net/bpf_offload.py)
  recognizes these names as inventory-side maps. Libbpf's
  [feature-probe source](https://raw.githubusercontent.com/libbpf/libbpf/master/src/features.c)
  creates and closes the corresponding feature-test objects.

## Decision

There is no unexplained experimental observer in this reviewed snapshot.
Continue to the bounded minimal-computation screen. This is not evidence that
system-service filters have zero overhead, that observers were absent historically,
or that network/host conditions were unchanged between sessions.

The launcher now checks a separately saved, reproducible ownership review instead
of demanding zero BPF objects. It rejects missing evidence, unknown objects,
unverified systemd ownership and changed audit/review hashes. This gate change is
captured in a new generation-02 preparation; generation-01's sealed preparation
is preserved. Computation, eight-cell matrix and stopping rules are unchanged.
Performance remains unrun at this review. Use the current
[protocol and launch instructions](runtime_io_minimal_computation_screen.md).
