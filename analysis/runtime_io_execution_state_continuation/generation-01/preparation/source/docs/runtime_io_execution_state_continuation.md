# Four-cell execution-state continuation under a new baseline

Authorized 2026-10-07 after twelve completed generation-02 trials and the b2_D
settling failure. Preserve all old raw data and failure markers. This is a
separate session, not retroactive relaxation of the interrupted protocol.

## Collection

Run only the missing automatic-speed cells, retaining their original suffix order:

| Continuation order | Source label | Period | Counters |
|---|---|---:|---|
| 1 | b2_D | 20 ms | On |
| 2 | b2_C | 20 ms | Off |
| 3 | b2_B | 100 ms | On |
| 4 | b2_A | 100 ms | Off |

Retain the exact minimal binary/image, 44,000 SHA iterations, Go1.26.1,
GOMAXPROCS=1, GOGC=100, CPUs2/4, 0.5 CPU, zero quota burst, 20-second warmup and
60-second measurement. Fresh containers and all original work/accounting,
coverage, alignment, ownership, memory-guard, resource and cleanup checks apply.
CPU frequency settings are read-only; these four cells all use the original
automatic policy. The privileged helper only owns counter fixtures/collectors.

After the app closes and fixtures finish, obtain a **new** automatic-speed
baseline: minimum20 minutes, maximum30. Use the same stable60-second window,
<=2 C range and <=1 C/min absolute slope. Every trial then requires a stable
60-second window within +/-3 C of this new baseline, with a10-minute ceiling.
The baseline is not a current screenshot temperature, nor is it repeatedly
updated to admit a failed trial. Retain it fixed for all four cells. If it drifts
again, preserve the failure and stop; no automatic baseline reset.

The new host sampler retains the original fields and one-second cadence but
writes/flushed samples incrementally into a standard JSON array. This avoids
buffering the full session and a long shutdown serialization. This logging change
is explicitly recorded as an additional cross-session difference. Trial-local
sealed speed/power coverage remains unchanged. New counters-off/on qualification
must pass the same1% CPU/job, capacity and delivery margins; known-work fixtures,
>=99.5% coverage and <=0.5% boundary alignment are repeated.

## Analysis and limits

The primary result is the within-continuation 20-versus100 ms CPU/job contrast,
reported separately with counters on/off, instruction/job, CPI, effective user
cycle-rate, delivery, capacity and user/system CPU split. A practical >=2% signal
requires matching direction and magnitude in both observer states with observer
qualification. These margins are not statistical equivalence criteria.

Replay all twelve old cells and all four new cells separately. Record each
session's baseline and preparation/trial seals. A sixteen-label combined table
and interaction calculation may be shown **only as descriptive cross-session
results**. The old constrained cells and new automatic cells do not form a
controlled uninterrupted second block: session, baseline, preceding activity and
logging differ. Do not use the old combined decision as a causal result or claim
a replicated speed interaction. The original run remains incomplete.

Counters can support a current execution-cost explanation if the penalty returns;
they do not recover historical instructions or clocks. In particular, check
user/system CPU splitting before treating cycles/user CPU second as clock change.
No new profiler, full V20 run or follow-up experiment is automatically authorized.

## Timing and launch

Expected30–45 minutes when settling is prompt, with a75-minute whole-run ceiling.
Performance must run externally with ChatGPT/Codex closed and AC connected. No
power profile is automatically set and no CPU bounds are changed. Use:

```bash
bash diagnostic/start_execution_state_continuation.sh \
  analysis/runtime_io_leftover_observer_audit/audit-20261006-root-01.json \
  analysis/runtime_io_execution_state_continuation/generation-01
```

## Decision after review

If the short-period penalty appears, first explain it using the measured
instruction count, CPI, effective cycle-rate, user/system CPU split and CPU
supply. Only a supported, reproducible discrepancy would justify proposing one
more targeted intervention; obtain explicit scope before a new performance run.
If results again show no useful period signal, retain the original verified
penalty, later improvements, partial speed pilot and continuation with their
limits, and move to the queue/yielding paper account. A generic throughput loss
from reducing execution speed is not novel, and the exact original reversal
cause remains unknown unless new evidence specifically establishes it.
