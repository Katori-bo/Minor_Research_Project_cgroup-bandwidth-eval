# Running the prepared V28 comparison

The offline package, schedules and software checks are prepared inside chat.
No scientific trial has run. Use a normal-user external interactive terminal,
keep external power connected and the retained balanced profile, then fully
quit Codex/ChatGPT before launching. The script rejects a running desktop app.

```bash
cd /home/Aditya/Desktop/Research_project/cpu-quota-tail-latency
bash diagnostic/start_v28.sh run /home/Aditya/Desktop/Research_project/cpu-quota-tail-latency/analysis/runtime_io_v28/generation-01
```

The command verifies the frozen bundle, checks the runtime and six functional
cases, asks sudo only for a read-only observer inventory, inhibits sleep and
runs16 calibration trials. If they qualify, it seals all forecasts and runs16
validation trials. It replays records and prints the final decision/report path.
It changes no observer configuration. It never resumes an attempted generation.

Allow roughly90–110min plus preparation; collection has a hard120min bound,
analysis10min and bounded cleanup. The terminal prints slot/stage progress;
progress.json contains the current phase. Do not reopen the desktop app during
measurement. Collection stops after the report. Preserve any traceback and all
partial data instead of launching the same attempted generation again.

After measurement has stopped, read-only verification or a separately bounded
partial-data replay is available:

```bash
cd /home/Aditya/Desktop/Research_project/cpu-quota-tail-latency
python3 -B diagnostic/v28_study.py status --directory analysis/runtime_io_v28/generation-01
python3 -B diagnostic/v28_study.py analyze --directory analysis/runtime_io_v28/generation-01
python3 -B diagnostic/v28_study.py verify-completion --directory analysis/runtime_io_v28/generation-01
```

`status` reports markers only; it is not full verification. The replay requires
successful runtime preparation and a recorded measurement lifetime/observer
review; a preparation failure must be diagnosed before any scientific launch.

The detailed thresholds, estimator contracts and outcome meanings are in
[the frozen protocol](runtime_io_v28_protocol.md).
