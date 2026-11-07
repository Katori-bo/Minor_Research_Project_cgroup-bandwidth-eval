# Friend's V31 host: readiness and troubleshooting

**Package update:** A separate Intel host02 package has now been prepared and passes 45 offline checks, exact compiled schedule exports, bundle verification after relocation, and return-archive inventory verification. See the [sendable instructions](../handoff/SEND_TO_FRIEND.md), [archive](../handoff/v31-host02-intel-20261011.tar.gz), [checksum](../handoff/v31-host02-intel-20261011.tar.gz.sha256), and [build receipt](../handoff/v31-host02-build-receipt-20261011.json). Its launcher uses server CPUs 2,3 and control CPUs 0,1, freezes new host defaults, preserves the original primary scientific contract, and predeclares the ordinary complete-response CDF secondary comparator. No collection has started and runtime qualification on the friend’s laptop remains pending. The earlier readiness diagnosis below describes the historical runner before this package was prepared.

11 October 2026. Assessment of the supplied terminal inventory and the current local historical runner. No access to the friend's computer, no collection, no launcher edits, and no manuscript changes. The supplied output contains no V31 command, traceback or failed experiment record. The user subsequently supplied instructions directing the friend to `scripts/start_fresh.sh` and a 300-trial matrix. That identifies an incorrect protocol handoff; it does not establish that the friend actually started that run.

## Correction: the 300-trial matrix is a different study

`scripts/start_fresh.sh` invokes `scripts/experiment.py new`. That runner's matrix is 5 CPU-period choices x 3 worker counts x 2 load levels x 2 traffic patterns x 5 repetitions = 300 trials. It recalibrates work and rates, uses half a CPU for capped configurations, and is the older general factorial study.

The supplied explanation that V31 is baked into that matrix is incorrect. V31 has a separate implementation in `diagnostic/v31_study.py`, with 16 fresh calibration trials and 18 held-out validation trials, plus six functional qualification cases and a resource preflight. Its primary **response deadline** is 10 ms; its **CPU bandwidth period** is 100 ms, with a 25 ms quota. Its fixed work is 88,000 rounds; validation rates are 5/11/19 requests/s. Selecting a 10 ms CPU-period row from the older matrix does not reproduce V31.

The general runner also describes settling as a minimum duration plus stability checks, not an exactly ten-minute idle. Its generated `processed/summary.csv` and plots are not the V31 prediction seal and completion evidence.

Steps for the friend now:

1. Do not launch `scripts/start_fresh.sh` for this replication. If its 300-trial campaign has started, interrupt it with Ctrl+C in its foreground terminal and preserve its session directory and launch log. Do not treat it as V31 evidence or delete its data.
2. Preserve the host inventory already supplied; Docker access has succeeded. Establish which project/package has been transferred before attempting another launcher.
3. A separate Intel host package must be prepared with the proposed nonoverlapping CPU assignment below, a fresh host/generation namespace, retained binary/image identities, independent fresh calibration and the predeclared ordinary complete-response CDF comparator. Software checks can be prepared locally; actual runtime qualification must occur on the friend's host.
4. Run that package's resource, functional, lifecycle and observer-inventory qualification first. Then use its documented host-specific launcher for calibration, prediction freeze and validation. The historical `diagnostic/start_v31.sh` is not yet that host-specific launcher.

There is no qualified host02 launch command available in the current project. The next required work is packaging the intended replication apparatus, rather than running the older matrix or asking the friend to guess a script substitution.

## What the inventory establishes

| Item | Supplied observation | Implication |
|---|---|---|
| CPU | Intel Core i5-10300H, x86-64, 4 physical cores / 8 logical CPUs | Basic architecture/topology prerequisites appear present; timing qualification remains necessary |
| OS/kernel | Ubuntu 26.04.1; 7.0.0-31-generic | Record as the new host's environment; do not import the old baseline |
| Virtualization check | `systemd-detect-virt` reports `none` | No virtualization detected by this check |
| cgroups | cgroup2fs; cpu and cpuset controllers listed | Basic controller presence established; quota enforcement, delegation and ancestor limits remain unverified |
| Docker | Engine 29.1.3 responds to normal-user `docker info`; cgroup v2, systemd driver | No Docker access failure in this output; no reinstall is indicated |
| Python | 3.14.4 | Available; retained software checks have not been run here, so compatibility is unqualified |
| Sleep inhibitor | `/usr/bin/systemd-inhibit` present | Tool availability only; inhibition must be checked by the qualified launcher |
| Memory | 7.1 GiB total; 2.6 GiB available; 372 MiB swap used | The 202 MiB free figure alone does not establish insufficient memory; this snapshot does not establish active swapping |

## A concrete incompatibility in the historical CPU assignment

The reported sibling pairs are `(0,4)`, `(1,5)`, `(2,6)`, `(3,7)`.

The historical V31 apparatus places service work on logical CPUs `2,4` and client/control work on `0,1`. Here CPU 4 and CPU 0 are threads of physical core 0. The two roles therefore share a physical core. `scripts/experiment.py:check_topology()` explicitly rejects this intersection with:

```text
CPU topology differs from the study configuration; update CPU affinity first.
```

This is a demonstrated configuration mismatch, not evidence that this is the particular error the friend encountered. It will be encountered if the unchanged runner reaches that topology check on the reported topology.

A proposed host-specific assignment is:

| Role | Logical CPUs | Physical cores | Sibling logical CPUs |
|---|---|---|---|
| Server | 2,3 | 2,3 | 6,7 |
| Client, monitor, watchdog, control | 0,1 | 0,1 | 4,5 |

This proposal separates the roles' physical cores. It does not reserve those cores against other processes or disable SMT. Qualification must still check the actual affinity and host interference. The assignment must be incorporated consistently into service startup, Docker cpuset, client, monitor, watchdog, orchestration and topology/affinity verifiers. Editing one constant will not produce a qualified package.

## Other confirmed portability restrictions

- `diagnostic/start_v31.sh` targets historical `analysis/runtime_io_v31/generation-01` and campaign `generation-01`. It refuses a campaign or session containing attempted data. Preserve that refusal and all existing records.
- `diagnostic/v31_common.py:owned_directory()` only accepts the historical parent and generation name. Renaming the directory alone is insufficient.
- `diagnostic/v31_verify.py:verify_bundle()` requires retained design, historical evidence, build receipts, binaries and source hashes. The current prepared bundle carries the historical resource baseline. A repository clone or copied completed generation is not a fresh host replication package.
- Runtime preparation verifies the pinned Docker image exists, hardware topology and the prepared environment. Reachable Docker does not establish that the retained service image is installed.

The existing [friend replication plan](runtime_io_v31_friend_replication_20261010.md) already states that a portable host02 launcher has not been implemented or qualified. This inventory supplies the topology needed to prepare that apparatus; it does not remove that prerequisite.

## Next troubleshooting step

Obtain the exact attempted command and complete error output, plus whether the friend has a plain clone, a transferred historical bundle or a separately prepared host package. Preserve any attempted generation. Then classify the failure:

| Output | Appropriate response |
|---|---|
| `can't open file`, missing module, missing design/seal/binary | Confirm project directory and transferred dependency closure |
| `Preserve attempted data` | Preserve data; prepare a separate host generation rather than delete the old one |
| Topology or affinity mismatch | Apply and qualify the complete new CPU mapping |
| Source changed / seal differs | Preserve sealed historical material; freeze adapted sources in a new host package |
| Missing pinned image | Transfer/import the exact retained image and verify identity before qualification |
| Calibration stopped or scientific domain failed | Inspect retained receipts; this may be a valid adverse host-transfer result, not a setup error to retry away |

No reinstall, OS/Python downgrade, CPU-offlining command or scientific parameter adjustment is justified by the supplied inventory. Host-specific packaging and functional qualification precede fresh calibration, prediction freeze and validation. Keep the original quota, work size, rates, deadlines and scientific gates unchanged for V31 replication.
