# One-CPU generation 01: pre-measurement technical abort

The sealed bundle and exact pilot evidence file set verify. The first stock
service had the declared one-CPU resource configuration and pinned image/binary.
Its 25 warmup offers succeeded with the original complete-response JPEG hash.
Owned cleanup completed without errors. No measurement collection started, and
there are no paired cost endpoints or scientific outcomes.

The frozen helper kernel_service_bridge.snapshot requires affinity exactly
{2,4}. The new runner called it despite requiring cpuset.cpus.effective=2.
This is an implementation inconsistency: that helper rejects the intended valid
single-CPU affinity. The failure was before the first measurement counter bracket.
The rejected thread identity/affinity were not saved, so those individual values
cannot be retrospectively inspected. This result establishes no new throttle,
performance difference, or cause of the original imgproxy throttle.

Preserve the attempted pilot and all generation-01 sources/seals. The original
preparation did not exercise the snapshot path used after warmup. Correct that
gap in generation 02 using a local strict {2} snapshot checker with equivalent
cgroup identity and disappearing-thread handling. Exercise the actual checker
before and after both real stock/observed functional cohorts, add regression
tests for single-CPU success and wrong-affinity/cgroup failure, and seal before
a new bounded qualification. Rates, operation, binaries, quota, statistical
acceptance rules and no-replacement policy remain unchanged. This repair is
justified by a verified pre-measurement code defect, not a favorable outcome.
