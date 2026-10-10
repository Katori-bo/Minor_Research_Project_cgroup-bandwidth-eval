# V16 preparation verification — 2026-10-04

**Prepared and verified. Performance collection has not started: 0/12 trials.**

[Protocol and launch](runtime_io_v16_repeatability_protocol.md).
Build bundle: `analysis/runtime_io_v16_repeatability_build`.
Results target: `results/diagnostic/runtime-io-v16-repeatability-1`.

## Findings available before performance collection

The retained prepared V12 service directory, including Dockerfile and all Go sources/tests, was
copied verbatim and compiled with the original retained Go 1.26.1 compiler image, no build cache,
no image pull and no build networking. Original Go tests passed. No Go code or service metadata
was added. The exact V12 client binary is retained.

[Full binary audit](../analysis/runtime_io_v16_repeatability_build/binary_audit/audit.json):

- Original and exact-source rebuild executable SHA-256 both equal
  `b7d249454d5477ffa0ade7cf1d90ba0eee8157ee166bb6e3f71d4cf912400efd`.
- Go build IDs and Docker image `Config` are identical.
- Original image: `sha256:9d4e51d8a227ea7b3d4ef32d2fe9df7db23111f4a17ae7ae3e199f0dec064ce5`.
- Exact rebuild image: `sha256:27556b25b0ee24f9ff2ec33953283c1c0a91051f1355e6c1265e0cf1d4d70eba`. Image creation/layer
  history differs even though executable bytes and runtime configuration match.
- The retained V15 metadata-zero executable hash is different:
  `7764a66c1218f5a23ebe5cffc595b6c9deb01254a010df02e5321cd409b63785`.
  It was only extracted/audited, not rebuilt or used as a performance arm.

This establishes reproducibility of executable bytes from exact prepared source. It does not
establish performance repeatability, explain V15's slowdown or qualify publication recording.

## Verification

- Six short real HTTP fixtures passed: three runner labels × GOMAXPROCS1/2, six requests per cell.
  All original schema/runtime, conservation and bounded-clock checks passed. Clock uncertainty
  spans approximately 106–128 µs, below the retained 1 ms bound. These unquotaed fixtures are
  behavior checks, not performance evidence.
- **60 Python checks passed, with no skips**, covering parallelism/completion/ablation/marker
  compatibility and 12 V16 checks. V16 checks exercise same-image identity/order, A/A gating,
  failed/missing/non-finite guardrails, all-offered outcomes, absent publication fields, original
  source identity, quiet-host launch refusal, stop PID identity, baseline preservation/tamper,
  real build/frozen-session tamper, and CSV/JSON/report/completion sealing. Offline export uses
  synthetic CPU values and does not qualify performance.
- `bash -n diagnostic/start_repeatability_batch.sh` and Python syntax checks passed.
- The matrix has 12 trials and balances every pair's relative order twice each way. Position and
  immediate carryover remain incompletely balanced. The not-started progress display shows 0/12.

Build, raw binary/audit and fixtures are sealed in `verification.json`. The runner freezes the full
bundle, code/protocol, matrix and independently measured baseline at collection. It retains
graceful stop/resume, finite collection, quiet-host monitoring, all attempts and sealed output.

## Next action

After saving work, run from an external terminal:

```bash
bash /home/Aditya/Desktop/Research_project/cpu-quota-tail-latency/diagnostic/start_repeatability_batch.sh
```

The launcher verifies the build, closes ChatGPT/Codex, waits for shutdown and starts the 12-trial
quiet-host pilot with live temperature/progress display. Keep AC power, Balanced profile and lid
open. Allow a 1–2 hour quiet window; the arithmetic minimum is 38 minutes before drains/cooling.
Review A/A before either rebuild contrast. No performance study or policy experiment was launched
by preparation, and there is no automatic next-stage promotion.
