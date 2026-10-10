# Run the four-trial V26 low-load pilot

This launcher performs separate runtime preparation, a fresh observer inventory,
four steady low-load recordings and independent analysis, then stops.
See the [frozen protocol](runtime_io_v26_protocol.md).

The offline bundle is prepared in `analysis/runtime_io_v26/generation-01`.
Offline preparation does not qualify the actual resource setup or workload.

Save your work, plug in the laptop and fully quit Codex/ChatGPT. In an external
interactive terminal, run as your normal user:

```bash
cd /home/Aditya/Desktop/Research_project/cpu-quota-tail-latency
bash diagnostic/start_v26.sh run analysis/runtime_io_v26/generation-01
```

Enter the sudo password locally for the read-only observer inventory. Leave the
machine idle. Expect roughly 20–30 minutes under ordinary settling conditions;
collection is bounded to 45 minutes, with separate 10-minute preparation and
analysis limits. Failure or interruption preserves the attempted generation.
Do not resume it or rerun until it passes.

After reopening the app, inspect status and independently verify completed data:

```bash
python3 diagnostic/v26_study.py status --directory analysis/runtime_io_v26/generation-01
python3 diagnostic/v26_study.py verify-completion --directory analysis/runtime_io_v26/generation-01
```

The latest report path is recorded in that generation's `latest_analysis.json`.
A valid failed-state trial is retained and does not trigger retry. The four
recordings must all qualify for `both_low_rates_qualified`. There is no busy
phase or equivalence claim. The launcher starts no further experiment.

If collection stops before its report, and measurement-lifetime records exist,
an offline partial report can be generated without launching any workload:

```bash
python3 diagnostic/v26_study.py analyze --directory analysis/runtime_io_v26/generation-01
```

Partial reports retain the `pilot_incomplete` decision. Preparation failures
without measurement-lifetime records remain preparation failures in status.
