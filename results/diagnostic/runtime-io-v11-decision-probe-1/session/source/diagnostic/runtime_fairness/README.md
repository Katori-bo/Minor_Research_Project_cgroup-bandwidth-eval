# Isolated pending-preemption fairness candidate

See [the step 2 findings and candidate](../../docs/runtime_io_v9_candidate.md).
This directory contains preparation tooling, not an installed runtime or a
performance launcher.

From the repository root:

```bash
venv/bin/python diagnostic/runtime_fairness/prepare.py \
  --source analysis/runtime_io_v8_long_waits/go_source/runtime \
  --output analysis/runtime_io_v9_candidate/fresh_prepared
```

The source hashes must match the retained Go 1.26.1 compiler. The output must
be fresh. Generated runtime test additions verify queue-policy correctness;
their timings must not be interpreted as performance results. The prepared
manifest remains `eligible_for_full=false`.
