# V19 implementation and preparation verification

Verified on 2026-10-05. The runnable study is
`analysis/runtime_io_v19_worker_control/generation-03`.
Preparation passed; full quiet-host qualification and discovery measurement are
pending (0/2 rehearsals, 0/18 trials). Functional checks are not research results.

The [execution protocol](runtime_io_v19_worker_control.md) implements the
[approved proposal](runtime_io_v19_plan.md): six balanced blocks, two identical
four-worker arms and one one-worker arm, fixed GOMAXPROCS=1, unchanged quota and
offered schedule. It reuses the original packaged server without kernel tracing.
The runner includes bounded owned-container cleanup, PID identity checks,
independent raw replay, all-offer accounting, interruption rules, block decisions,
CSV exports and scientific plots.

## Completed checks

- All 33 accounting, decision, protocol, ownership and tamper tests passed.
- Bash launcher syntax passed.
- Docker image and actual container executable match the original V18 hashes.
  The effective CPU, memory and PID limits match generation-04.
- Four-worker and one-worker HTTP controls each retained 114 offers, all
  successful, with no client drops or missed arrivals.
- The queued-cancellation control retained all 453 client timeouts: 430
  computations completed, including 384 without handler-resume records. Of the
  other offers, 22 have server rejection records and one lacks a server entry.
  These remain unsuccessful client outcomes. Missing markers are not fabricated.
- All three functional containers and cgroups were removed; their cleanup
  receipts have no errors or watchdog intervention.
- Independent replay reproduced each functional derivation. Client/server clock
  uncertainty was 0.139, 0.136 and 0.206 ms respectively, below the 1 ms bound.
- Additional tests on copies of actual evidence rejected altered raw latency,
  altered derived results, an extra unsealed file and a modified executable.
- PNG/SVG reports rendered and were visually inspected with explicitly synthetic
  block effects and relabeled retained V18 requests. These are rendering checks,
  not V19 observations.
- The unchanged V18 generation-04 completion verifier still passes, returning
  `effects_outside_margins`.

Generation-01 and generation-02 preparation failures remain preserved. Separate
sealed cleanup audits verify absence of their owned containers and cgroups.
Generation-01 exposed a Docker absence-message parsing issue. Generation-02's
cancellation fixture did not exercise missing handler records, so its functional
demand was increased in generation-03. The discovery workload was unchanged.

The generation-03 preparation seal SHA-256 is
`68a0b9cd749580c4ad657ccfcf1e6f8f5a90f323441529b398c3ff4c833eb163`.
It freezes 105 source files: the unchanged 95-file V18 set and ten V19 files.
A separate implementation review is retained under
`analysis/runtime_io_v19_preparation_review/verified-20261005`.

## Run from an external terminal

Fully quit the Codex/ChatGPT desktop app first, keep the machine otherwise idle,
and run as the normal user with Docker access. No sudo is needed.

```bash
cd /home/Aditya/Desktop/Research_project/cpu-quota-tail-latency
bash diagnostic/start_worker_control.sh run \
  "$PWD/analysis/runtime_io_v19_worker_control/generation-03"
```

This command performs initial cooling, the two full-duration operational
rehearsals, then the 18 discovery trials only if qualification passes. It writes
progress and evidence to the generation directory and automatically analyzes and
independently verifies completion. Allow roughly 75–100 minutes, potentially
longer for cooling. Do not reopen the desktop app during measurement.

After the run:

```bash
python3 diagnostic/worker_control_study.py verify-completion \
  --directory "$PWD/analysis/runtime_io_v19_worker_control/generation-03"
```

For interrupted runs, inspect `status` and retained failure evidence first.
`resume` preserves accepted trials; an interrupted discovery block is flagged and
cannot support progression to confirmation. Full measurement has deliberately
not been launched with the desktop app active.
