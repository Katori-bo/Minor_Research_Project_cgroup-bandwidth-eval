# Fresh experimental protocol (v2)

The existing `results/raw`, `results/pilot`, and `results/preflight` are legacy exploratory data. Leave them intact. New results go exclusively to timestamped directories under `results/sessions/`; v2 analysis never imports legacy results.

## Preparation

Run once, before closing desktop applications:

```bash
cd /home/Aditya/Desktop/Research_project/cpu-quota-tail-latency
bash scripts/build_v2.sh
```

For publication measurements, save your work and close Chrome, VS Code, ChatGPT/Codex and other active applications. Plug in power. In your normal desktop settings, disable automatic suspend for the run. Keep the lid open and use the same power mode throughout. Leave the CPU governor unchanged unless deliberately choosing and recording another configuration before the entire session. No script changes system settings or closes applications.

Open a standalone terminal (not an editor's integrated terminal), then run:

```bash
cd /home/Aditya/Desktop/Research_project/cpu-quota-tail-latency
bash scripts/start_fresh.sh
```


The terminal must remain open. Do not use the computer for other work during measurement. Choose **Balanced** before launching. The runner starts with an automatic ten-minute settling period, so you do not need to time it manually. Expect roughly 13–16 hours including calibration, checks, and at least one minute of settling per trial; actual time depends on temperature stability and queue drain. Output and failures are saved under `results/launch-logs/`. The launcher prints the session path. Ctrl-C stops the run and cleans up only the container it created.

With applications open, test the workflow using `bash scripts/start_fresh.sh --diagnostic`. This runs calibration, saturation checks, and a pilot; it never starts the formal matrix. Such sessions cannot be resumed into publication data.

## Protocol

- Calibrate CPU work using persistent HTTP requests and cgroup CPU accounting. Shell/curl startup is excluded. The approximate 5 ms target includes small per-request service overhead.
- Bracket the sustainable rate on one fixed reference (one worker, 100 ms period, 0.5 CPU). Assess successful throughput including queue drain, errors, and latency growth; save every calibration attempt. Refine the bracket three times. Calibration windows are 30 seconds, so capacity is an operational estimate, not an absolute machine constant.
- Derive moderate and high rates as 50% and 85% of the lower stable bound. All configurations receive exactly the same rates and work. Bursts use 0.5R/1.5R in 5-second phases, preserving mean R. A high burst peak can exceed reference capacity; report queueing and rejections as outcomes.
- Check 0.5 CPU usage under saturation for each of the four quota periods.
- Run a 12-condition pilot with 20-second warm-up and 60-second measurement, then the fixed randomized matrix of 300 trials with five repetitions.
- No assertion requires shorter periods or more workers to perform better. No observed effect is a valid scientific outcome. Inspect the pilot for interpretation; do not tune rates to manufacture the expected result.
- Container affinity is logical CPUs 2 and 4 (separate physical cores on this host). Runner, monitor, and generator use 0 and 1. This is affinity, not exclusive isolation; sibling CPUs 3 and 5 remain accessible to the OS.
- Verify actual `cpu.max`, zero container `cpu.max.burst`, and uncapped ancestors. Save image ID, code/binary hashes, topology, governor, per-request measurements, and monitoring samples including process names and frequencies.
- End-to-end latency includes dispatch delay, response headers, and the complete response body. Successful-request latency and all failure counts are retained. Throughput uses elapsed time including drain; generator lag flags are distinct from application overload.
- The generator uses 512 client workers, above the application's 128-slot queue plus server workers. This lets the application report queue-full responses rather than hiding them behind a smaller client concurrency cap.
- Results flagged for generator delay or missing monitoring stop the formal matrix for review; application rejections are retained. Do not silently delete outliers. Record any exclusions and reruns with a reason independent of the desired outcome.
- Initial settling samples the temperature and power settings every five seconds for at least ten minutes. The last full minute must have a temperature range no greater than 2 C and an absolute linear trend no greater than 1 C/min for every selected sensor. Its mean becomes the session baseline. These are declared starting tolerances for this protocol, not validated hardware limits or a guarantee of precision.
- Before every trial, require the same full-minute stability test and a mean within 3 C of the original baseline. The baseline stays fixed; it does not follow gradual heating. There is no fixed 65 C cutoff. Logs are preserved in `initial-settling.json`, `environment.json`, and each trial's `settling.json`. If the check does not pass within twenty minutes beyond its minimum wait, stop for investigation rather than silently relaxing the thresholds.
- Governor, energy-performance preference (EPP), frequency bounds, platform profile, and external-power state are captured and checked during settling and measurement. The desktop power profile is also read at phase boundaries when `powerprofilesctl` is available. A detected change stops the session; the scripts never change power settings. If the desktop profile is unavailable, select Balanced manually and document it; null does not mean verified Balanced. External power is required when its status is exposed by sysfs.
- The stability gate controls the **pre-warm-up starting condition**. The fixed 20-second workload warm-up is followed by measurement, during which temperature and frequency traces are preserved. The code does not require flat temperature under load, compensate latency, or prove absence of thermal throttling. Review these traces alongside outcomes. A rising temperature caused by a configuration is evidence to report, not an automatic reason to delete the trial.

## Progress and analysis

Read `SESSION/status.json`, the launch log, and `SESSION/raw/*/result.json`. Successful completion generates `SESSION/processed/summary.csv` and plots split by load, worker count and traffic pattern. Regression runs only for a complete unflagged matrix, with quota period categorical and the unlimited baseline excluded.

Resume a session only with identical code/binary and unchanged experimental environment:

```bash
taskset -c 0,1 venv/bin/python -u scripts/experiment.py resume --session /absolute/path/to/session
```

Resume repeats the ten-minute settling period, requires the original power settings, and returns to the original temperature baseline. The runner skips valid completed results. An incomplete trial directory or a flagged result requires review; it is never overwritten automatically. A diagnostic session or code change requires a fresh session. Preserve interrupted data and document the reason for any new session.

Legacy shell runners are deprecated. Do not use `run_matrix.sh`, `calibrate.sh`, or `run_single.sh` for the new dataset. The old paper draft and figures are exploratory and must be replaced after the formal matrix; do not reuse their empirical claims.
