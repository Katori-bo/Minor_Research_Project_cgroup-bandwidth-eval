# V17 preparation verification — 2026-10-04

**Prepared and verified; performance collection remains unstarted at 0/16.**

[Protocol and launcher](runtime_io_v17_loading_protocol.md).
Bundle: `analysis/runtime_io_v17_loading_build`.
Results target: `results/diagnostic/runtime-io-v17-shared-loading-1`.

## What is prepared

Four conditions cross the exact retained V12/V16 image IDs with packaged/common-file loading.
Neither service is rebuilt or changed. All service executable hashes equal
`b7d249454d5477ffa0ade7cf1d90ba0eee8157ee166bb6e3f71d4cf912400efd`; the exact V12 client is retained.
The same asset directory is mounted read-only in every arm. Shared arms additionally bind the
exact same host file at `/server`; packaged arms retain their image's executable.

A separate statically linked startup utility records the running PID 1 executable and its own
file hash/device/inode/size/owner/mode, with actual Docker image/mount evidence. It executes before
warmup identically in all arms, not during request collection. This is provenance qualification,
not new request-level runtime/kernel observation. Shared loading and extra mount setup are a combined
treatment; startup checks may affect subsequent state and are part of this protocol.

Four declared Williams orders provide 16 trials, one appearance per arm in every position, each
ordered pair once as within-block immediate carryover, and twice in each relative order. Between-block
carryover remains uncontrolled; order is deterministic. The primary and guardrail margins remain unchanged.

## Verified evidence

- The retained Go 1.26.1 compiler built the startup helper offline with CGO disabled and local
  toolchain/module networking disabled. Both helper Go tests passed; `file` confirms a statically
  linked Linux x86-64 executable. Helper SHA-256:
  `46e66c6dd670debe25962bb13d66c2d7bc1f157f20a776faa32620711e824a6f`.
- Eight real short HTTP/loading fixtures passed: four arms × GOMAXPROCS1/2, six requests each.
  Actual running executable hashes and mount readonly/source/type/propagation checks passed.
  All four shared fixtures identify the same host device/inode and bytes, across both images.
  Clock uncertainty spans approximately 107–149 µs, below the retained 1 ms bound. These are
  unquotaed behavioral/provenance fixtures, not performance observations.
- **73 Python checks passed with no skips**, including 13 V17 checks and prior-runner compatibility.
  V17 checks cover order/identity, real mount/process provenance, wrong hashes/inodes/mounts,
  common-file replacement with identical bytes, missing packaged-gap refusal, interactions,
  failed/missing guardrails, all-offered outcomes, absent publication markers, wrapper cleanup,
  quiet-host refusal, frozen-bundle tamper and CSV/JSON/report/completion sealing.
- Python syntax and launcher shell syntax passed. Progress shows 0/16, with no collection worker.

Session validation checks the complete frozen bundle, including fixtures, rather than assuming the
older fixture manifest schema. The session copies the common/probe files once and seals their new
device/inode identities; collection/resume rejects replacements even if bytes match. Completed
verification uses sealed historical identities, supporting later archival without an original inode.

## Launch and interpretation

After saving work, run in an external terminal:

```bash
bash /home/Aditya/Desktop/Research_project/cpu-quota-tail-latency/diagnostic/start_loading_batch.sh
```

The launcher verifies the bundle, closes ChatGPT/Codex and starts the quiet-host finite study with
temperature/progress monitoring and sleep inhibition. Retain AC power, Balanced profile and lid open.
Allow 1–2 hours; arithmetic floor 47 minutes 20 seconds excludes startup, drains and extra cooling.

Interpret packaged-image reproduction first, then shared-image and both within-image mount
contrasts, plus the signed interaction. If the packaged gap does not recur, shared-file neutrality
cannot establish that mounting removed V16's effect. Four blocks do not establish equivalence,
filesystem/cache causation or a scheduler defect. No persistent recorder or intervention is qualified,
and no additional experiment is launched automatically.
