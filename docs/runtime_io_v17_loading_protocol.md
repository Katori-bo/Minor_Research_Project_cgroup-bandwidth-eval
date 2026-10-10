# V17: packaged versus common-file executable loading

Prepared 2026-10-04 after the [V16 offline audit](../analysis/runtime_io_v16_repeatability_review/report.md).
V16 reproduces executable bytes and image configuration, and its original-image A/A comparisons
are within discovery margins, yet rebuilt-image runs improve 500 ms timely success by 1.53–3.92
percentage points. Existing launch/resource/host samples do not identify the cause. Stay in Step 1;
preserve all prior evidence. This experiment tests a named loading/setup ambiguity, not a remedy.

## Four conditions, unchanged service program

| Arm | Immutable image | Executable backing file |
|---|---|---|
| legacy_packaged | Exact retained V12 image | Its original `/server` |
| rebuilt_packaged | Exact retained V16 rebuild image | Its packaged `/server` |
| legacy_shared | Retained V12 image | One common host file mounted read-only at `/server` |
| rebuilt_shared | Retained V16 rebuild image | The exact same common host file mounted read-only at `/server` |

No service rebuilding or source edits. All four executed binaries must have SHA-256
`b7d249454d5477ffa0ade7cf1d90ba0eee8157ee166bb6e3f71d4cf912400efd`. The exact V12 client is retained.
The shared file is extracted from the original immutable image and copied once into the session.
Both shared arms use that same session path, device/inode, bytes, owner and mode throughout.
Do not copy a fresh file for each trial or replace an asset with identical bytes during resume.

The shared-file treatment changes executable backing-file identity and read-only mount setup
together. This is not a pure inode, page-cache, filesystem, alignment or scheduler test. It does not
control all startup/runtime state. A disappearing gap supports a targeted loading/setup follow-up,
not a causal mechanism or observer qualification. A common mount can itself change timing.

Docker supports sharing a host file and mounting it read-only; inspect actual mounts rather than
trusting intended commands. [Docker bind-mount documentation](https://docs.docker.com/engine/storage/bind-mounts/).

## Startup provenance, identical procedure in all arms

Each arm mounts the same frozen qualification asset directory read-only at `/qualification`.
This contains the common executable and a separate statically compiled Go provenance utility.
After service health and before warmup, execute that utility once using `docker exec`. It reads
the already-running PID 1 executable through `/proc/1/exe` and its own executable, retaining actual
SHA-256, device/inode, size, mode/owner and executable link. Also retain `docker inspect` image ID
and mounts, including source, destination, bind type, readonly status and propagation.

Require original executable hash in every arm, common device/inode identity in shared arms and
exact expected mounts in every arm. Packaged arms must have no `/server` bind mount. Probe executable
and host identities must match sealed assets. The helper is a startup provenance qualification,
not a per-request kernel/runtime observer. It exits before the retained 20-second warmup, runs
in every arm, and adds no service counters, locks or request events. Its effects on later state
are not proven absent; all results apply to this common qualified startup procedure.

Preparation builds/tests only the helper with retained Go 1.26.1 compiler image
`sha256:2389ebfa5b7f43eeafbd6be0c3700cc46690ef842ad962f6c5bd6be49ed82039`, CGO disabled,
module networking disabled, local toolchain and no Docker networking. Eight short unquotaed HTTP
fixtures cover four arms × GOMAXPROCS1/2, six requests each, including actual process/mount identity.
They establish implementation behavior and bounded clock joins, not performance.

## Four matched blocks: 16 trials

Deterministic Williams orders, declared before collection:

1. legacy_packaged, rebuilt_packaged, rebuilt_shared, legacy_shared
2. rebuilt_packaged, legacy_shared, legacy_packaged, rebuilt_shared
3. legacy_shared, rebuilt_shared, rebuilt_packaged, legacy_packaged
4. rebuilt_shared, legacy_packaged, legacy_shared, rebuilt_packaged

Each arm occupies each position once; each ordered pair occurs once as a within-block immediate
transition; each pair appears twice in each relative order. Between-block carryover and all host
state are not balanced or eliminated. Do not call these orders randomized. Four blocks are a
discovery design, not statistical equivalence or guaranteed precision.

Retain GOMAXPROCS=1, four workers, queue128, 44,000 SHA iterations/job, quota 50 ms/period100 ms,
zero burst credits, uncapped ancestors, server CPUs2,4 and client/monitor CPUs0,1. Every arm uses
identical offered IDs/scheduled offsets in its matched block. Deterministic five-second low/high
phases at 56.605/169.815 requests/s, mean113.21/s. Each trial: ≥60 s settling, 20 s warmup, 60 s
offered arrivals, five-second timeout and full worker/client/handler drain. All arms use the same
environment variables, HTTP control-plane operations, fresh-container lifecycle and monitor cost.

## Declared outcomes, contrasts and decisions

Primary: successful responses within 500 ms of scheduled arrival / **all offered requests**.
Guardrails: 1,000 ms timely success, failure fraction, actual CPU/job and successful p99. Preserve
failed, rejected, timed-out, cancelled, late and drained outcomes, missing worker/handler events,
clock bounds and existing computation/handler deadline-crossing classes.

1. legacy_packaged → rebuilt_packaged: does V16's packaged-image gap recur in this session/procedure?
2. legacy_shared → rebuilt_shared: image gap while both execute the exact common file.
3. legacy_packaged → legacy_shared: mount/loading effect within the original image.
4. rebuilt_packaged → rebuilt_shared: mount/loading effect within the rebuilt image.
5. Interaction: shared-image delta minus packaged-image delta for fractions; ratio of the two
   image contrasts for CPU/job and p99. Report signed per-block interaction, not just pooled arms.

Retain every-block practical margins: absolute timely delta ≤1 percentage point at both deadlines,
failure delta ≤0.1 point, CPU/job ±5%, successful p99 ±10%. Missing/non-finite guardrails fail.
Report paired deltas, median/range/sample standard deviation across blocks. Individual requests
are not independent replications; no pooled-request equivalence or confidence claim.

| Observed result | Permitted interpretation |
|---|---|
| Packaged contrast does not show >+1 point at 500 ms in every block, or has missing guardrails | V16's predicted direction/magnitude is not reproduced; do not claim mounting removed the gap |
| Packaged prediction reproduced, shared contrast within every practical margin | Shared loading is a discovery control worth manual review; it supports loading/setup follow-up, not a mechanism |
| Packaged prediction reproduced, shared contrast outside any margin | Common loading did not establish neutrality; review interaction/within-image effects and remaining uncertainty |

Even if both image contrasts are neutral, inspect within-image mount effects and guardrails before
using this procedure as a baseline. Do not promote a chosen faster arm, relax margins, repeat valid
trials to obtain a pass or launch further experiments automatically. No publication timestamps,
runnable readiness, instantaneous quota budget or request-level throttling are measured here.
Persistent recorder qualification and worker/scheduler intervention remain separate decisions.

## Environment, acceptance and seals

Measure this session's own baseline after ≥10 min quiet idle and a stable 60 s window; do not copy
V16's 45.77°C baseline. Retain ±3°C tolerance, ≤2°C window range, ≤1°C/min absolute slope,
existing cooling timeout, AC power, Balanced profile, lid open and quiet-host checks. No silent
rebaseline, post-result relaxation or thermal-equivalence claim.

Freeze source/protocol, full asset/build/fixture bundle, images, matrix, client, calibration,
startup identities and baseline/idle evidence. Seal shared/probe device/inode identities at session
creation and verify before every trial/resume. Each raw attempt seals startup evidence alongside
clock namespaces, actual resource settings, clocks/conservation/monitor and outcomes. A mismatched
hash, mount, backing identity or technical check stops collection without automatic retry. Preserve
every attempt; a deliberate resume rechecks original evidence and skips valid trials. Changed
source or asset identity requires explicit review and a separate session. Completed evidence verifies
historical frozen identities without requiring the original host inode to survive archival.

Final report, trials/requests CSV, loading screen, validation, attempt audit and root completion
seal remain immutable. New derived reviews live outside result sessions. V16 is not pooled as a
matched block or rerun to replace its valid observations.

## Preparation and external-terminal launch

```bash
cd /home/Aditya/Desktop/Research_project/cpu-quota-tail-latency
python3 diagnostic/build_loading.py build
python3 diagnostic/loading_study.py verify-build
```

After saving work, use a normal external terminal:

```bash
bash /home/Aditya/Desktop/Research_project/cpu-quota-tail-latency/diagnostic/start_loading_batch.sh
```

The launcher verifies assets, closes ChatGPT/Codex, waits for shutdown and starts detached,
sleep-inhibited finite collection. Five-second display: temperature/baseline, phase, completed/16,
remaining, elapsed and log path. Closing the display does not stop the study. Keep AC/Balanced/lid
open and the desktop app closed during collection. Arithmetic floor: 16×140 +600 s = **47 min20 s**,
excluding startup, drains, cooling and analysis. Allow **1–2 hours**; this is not a timing guarantee.

```bash
python3 diagnostic/loading_study.py status
python3 diagnostic/loading_study.py watch
python3 diagnostic/loading_study.py stop
python3 diagnostic/loading_study.py verify-completion
```

Stop validates worker/launch identity and preserves evidence. Rerunning the launcher resumes valid
remaining trials under the same baseline/assets; it never duplicates a running study. Results:
`results/diagnostic/runtime-io-v17-shared-loading-1/session/analysis/` contains `report.md`,
`trials.csv`, `requests.csv`, `loading_screen.json`, `validation.json` and `attempt_audit.json`.
Root `completion.json` binds frozen analysis/environment/raw evidence. Preparation launches no
performance study.
