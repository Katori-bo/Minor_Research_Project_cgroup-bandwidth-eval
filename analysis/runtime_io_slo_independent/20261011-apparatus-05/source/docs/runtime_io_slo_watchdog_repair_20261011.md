# Independent SLO evaluation: watchdog repair and closed local allocations

The saved NGINX observer ownership review passed. Collection stopped during the
first qualification case because the independently spawned Python watchdog could
not import `common` from the portable runtime directory. This was an apparatus
packaging error, not evidence of a forecasting failure or an observer leak.

## Evidence from the attempted NGINX allocation

The original attempt is retained in
`handoff/slo-host01-20261011-runtime-v4/runs/host01/NGINX`. Its return seal is
`c49f2b707375bc3fe34bb394dc95765ddd7419aee2bec622af43a1a3da975d2b`.
The review and copied evidence are preserved under
`analysis/runtime_io_slo_independent/20261011-host01-nginx-failure-01`.

The audit inventory requested ownership review for 26 programs, five maps and
one link. The saved review classified these as systemd policy, a network filter
associated with NetworkManager through its held map, and transient bpftool
inventory infrastructure. Its result was
`no_unexplained_experimental_observer_in_reviewed_snapshot`, with
`performance_eligible: true`. The NetworkManager association does not establish
direct socket ownership. This snapshot establishes neither historical observer
absence nor zero overhead. No BPF objects were removed or checks relaxed.

The qualification service started, but its independent watchdog exited with
`ModuleNotFoundError: No module named 'common'`. The guard stopped collection
before the HTTP client spawned. The acquisition inventory contains zero client
offers and zero raw acquisition files. Calibration and target collection did
not begin. The sealed case cleanup receipt records no errors and 0.827709716 s;
the campaign supervisor also records no cleanup errors. These are saved cleanup
records, not a new live host inspection. The allocation closed after
187.520880128 s within its original 2,700 s cap.

## Apparatus correction and verification

The portable builder now gives diagnostic subprocess entrypoints their own
runtime, diagnostic, script, analysis and collector import paths. A parent's
temporary `sys.path` changes do not propagate to a fresh Python process, which
the previous tests had failed to exercise.

Fresh-process checks exercise the NGINX watchdog, both Go watchdogs and the
worker, supervisor, setup, return assembler, audit and monitor command entrypoints.
The diagnostic tests run isolated Python interpreters from unrelated working
directories without inherited Python path settings. Watchdog fixtures already
contain cleanup or completion receipts, so these tests start no services,
Docker commands, HTTP traffic or observer inventories.

The successor packages are:

| Host | Package | Package seal SHA-256 |
| --- | --- | --- |
| AMD host01 | `handoff/slo-host01-20261011-runtime-v6` | `c2a6a0f2895890f0e986b4bc5e7bab981729966640f4f63dde9f02e3e8936ec8` |
| Intel host02 | `handoff/slo-host02-20261011-runtime-v6` | `6852b0bb6cee9746d8f5e8ad188e42636448f253d5ee958b19c20bee2d2ff697` |

Each package passed 43 offline checks and exported 69 compiled client vectors.
This establishes offline engineering checks, not external runtime qualification.
Supplement 5 preserves the correction, source snapshots, package seals and test
receipts in `analysis/runtime_io_slo_independent/20261011-apparatus-05`.
The intermediate v5 preparation is also retained and has no campaign outcomes.

## Scientific accounting and next gate

The earlier Go attempt remains closed under its original v3 package and return
seal. Its audit-route failure occurred after functional preparation, before
calibration or target collection. Its saved acquisition inventory contains 510
declared functional offers and its supervisor records 46.675556012 s.
The NGINX v4 attempt is now also closed. Together these consume both host01
allocations and leave all 36 planned local target windows unavailable. They
provide no SLO decision evaluation outcomes. Both source packages, full evidence
and costs remain preserved. The successor resolves each allocation to its
original source and refuses retries. Keep v3 and v4 beside v6 under their original
directory names for provenance verification and final assembly.

The frozen scientific v1 plan and its 72-window denominator are unchanged.
The 36 Intel target windows remain pending; host availability is still
unconfirmed. A final study verdict requires all four closed allocations. No
synthetic check closes a real allocation or supplies scientific observations.

The next execution gate is confirming the declared Intel host and its allocation,
then external qualification using the corrected host02 package, in the frozen
NGINX-then-Go order. There is no further local relaunch under v1. A replacement
local study would require an explicit preserved amendment before collecting its
outcomes; no such amendment has been selected here. Observer hardware collection
remains held. Novelty and independent validity remain unresolved.

The original empirical consolidation, manuscript and separate pending Intel V31
package retain their sealed inputs. New operational notes are stored here rather
than changing those historical checkpoints.
