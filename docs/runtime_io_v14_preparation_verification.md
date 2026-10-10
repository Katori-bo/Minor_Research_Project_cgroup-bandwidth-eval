# V14 overnight ablation preparation — 2026-10-04

**Status: ready for a quiet-window launch; performance collection has not started.**

[Protocol and launcher](runtime_io_v14_ablation_protocol.md), [research tracker](current_research_plan.md).

## Prepared and verified

- [Four new worker variants and passive buffer](../diagnostic/ablation_service.go), [meaningful Go concurrency/cancellation/reset/overflow checks](../diagnostic/ablation_service_test.go).
- [Isolated builder](../diagnostic/build_ablation.py), preserving exact verified V12 and V13 reference images. Prepared source/images are at `analysis/runtime_io_v14_ablation_verified_build`.
- [Eight-block/48-trial runner](../diagnostic/ablation_study.py), with frozen protocol/source/build-bundle hashes, inherited full-outcome/resource/environment validation, observer drain and complete technical-attempt reuse checks.
- [Bound-aware all-offered analysis and seven declared contrasts](../diagnostic/ablation_analysis.py), including a separate passive-versus-legacy practical screen and explicit manual review before controls.
- [External-terminal overnight launcher](../diagnostic/start_ablation_overnight.sh), shell syntax verified, displaying temperatures, baseline, elapsed time, completed/48 and trials remaining. Closing the display leaves the background worker running; completed results are analyzed/sealed automatically.

All four new images passed normal Go tests with the retained Go 1.26.1 compiler, networking disabled for builds. The full host Go race test suite passed using the same compiler SDK and existing GCC, with no download/installation. This exercised simultaneous live metrics reads, single-writer buffer publication, repeated reset generations, queued cancellation, overflow without overwrite/blocking and the inherited service tests. [Race record](../analysis/runtime_io_v14_ablation_verified_build/race_verification.json), [race log](../analysis/runtime_io_v14_ablation_verified_build/race_tests.log).

Twelve short **unquotaed real-HTTP fixtures** passed: all six arms × GOMAXPROCS=1/2, six offered IDs each, complete joins and bounded clocks. [Functional seal](../analysis/runtime_io_v14_ablation_verified_build/functional_verification.json), [build manifest](../analysis/runtime_io_v14_ablation_verified_build/build.json). They establish implementation behavior, not deadline performance under quota.

The diagnostic Python suite passed **131 tests**, with none skipped after fixtures were prepared. Tests cover every arm's full-outcome analysis, missing clocks-only publication evidence, duplicate/dropped/pending-record refusal, 48 unique configurations, paired order balance, first-six position/carryover balance, separate causal contrasts/candidate qualification, observer drain, failed-attempt exclusion, quiet-host refusal before spawn, isolated preparation, whole-bundle/source tampering, remaining counts and end-to-end CSV/report/export seal checking against functional data with synthetic CPU counters. [Tests](../diagnostic/test_ablation.py).

The sealed V13 completion was reverified after V14 preparation. Original evidence and source snapshots are unchanged.

## Preserved preparation failure

The first unsealed bundle at `analysis/runtime_io_v14_ablation_build` passed normal Go tests and the new recorder race tests, but inherited runtime-trace tests attempted to create `/runtime.trace` on the host and returned HTTP 500. It is preserved. The verified bundle's **host test copy only** redirects that fixture output to an owned temporary directory; the source adjustment and actual tested source hashes are recorded. Production images retain the original trace path and tracing remains disabled in performance collection. The complete race suite then passed.

## Remaining evidence and scope

Collect the finite 48-trial batch with the app closed, power connected, Balanced profile, lid open and the validated temperature/quiet-host criteria. Budget approximately 3–6 hours, with cooling-dependent uncertainty; the 48-trial arithmetic floor plus initial idle is just over two hours. Resume only after inspecting a technical failure; genuine deadline/failure outcomes are not rerun criteria.

Review legacy→clocks, clocks→passive, passive→mutex_early, mutex_early→mutex_late, mutex_late→V13, legacy→passive and legacy→V13 before advancing. Clock/path, allocation/commit and V13 remaining differences are declared bundles, not pure attribution to one implementation detail. Exact runnable readiness and per-request kernel/quota attribution remain unqualified. No independent-control or policy experiment launches automatically.
