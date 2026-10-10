# V22: verified prospective prediction transfer

2026-10-07. Generation-02 completed four qualification/calibration slots and
eight validation trials. Independent raw completion replay passed again during
the follow-up review. No failed technical attempts are recorded. The frozen
scientific design, prediction package and original report are unchanged.

All12 primary checks passed: every eight trial miss error and every four paired
even-minus-burst contrast error was within3 pp. Busy capacity was152.47 jobs/s,
from two independent calibration runs agreeing within0.26%. Frozen burst miss
prediction10.38% compared with10.97–11.92% in validation; even prediction0%
matched all four even trials. Maximum primary error was1.55 pp.

Supporting queue/rejection/recovery, the conditional even-arm screen and the
declared baseline advantage all passed. Predicted burst peak87 compared with
88–92; even peak was1 versus predicted0. Worst recovery error was46.1 ms versus
a250 ms limit. All requests returned200, with no rejections or responses after1 s.
These do not establish exact request timing: individual burst-response prediction
errors reached98.2 ms, and predicted burst p99 undershot observed p99 by11–23 ms.

The nominal quota/whole-trial CPU-job estimate gave139.39 jobs/s and predicted
44.05% burst misses. That overprediction is a reproducible failure of this
specific substitution, not a universal rejection of CPU-demand models. Even
arrivals used approximately14.8% more measured cgroup CPU per completed job
than bursty arrivals in the paired blocks, while having much lower latency.
The causal origin of either difference is not identified by these records.

V22 supports queue-account transfer for this service/host/boot/44k work size
and these two patterns. Yielding was off. The500 ms aggregate screen does not
validate stage/tail predictions, new schedulers or general transfer. Novelty
remains an assessment against prior work.

Reproduce the retained independent interpretation receipt:

```bash
python3 analysis/review_v22_results.py
```

It refuses to overwrite an existing receipt. The receipt is already saved in
[result review](../analysis/runtime_io_v22_result_review/20261007/report.json).
For a fresh completion verification without creating a receipt:

```bash
python3 diagnostic/v22_study.py verify-completion --directory analysis/runtime_io_v22/generation-02
```

See the [original sealed report](../analysis/runtime_io_v22/generation-02/analysis/1791352638937269784/report.md),
[short draft](runtime_io_short_working_draft.md) and
[bounded novelty/generality review](runtime_io_novelty_generality_review.md).
