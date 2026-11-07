# V31 host02 — Intel i5-10300H replication

Revised 19 October 2026 (cpuset01) for the supplied native Ubuntu laptop. This is a separate package: use these commands from this directory. It contains the pinned Linux/amd64 service image and retained service/client/gate/counter binaries. Python uses the standard library; no venv or local Go rebuild is required. No 300-trial study is launched.

The package passes offline software checks. **Runtime qualification on your laptop is pending** and is the first launch gate. Successful setup does not guarantee calibration or prediction success. The run retains adverse outcomes and stops if its fixed contract cannot be met.

## CPU-list compatibility correction

This revision accepts equivalent Linux CPU-list forms (`2-3` and `2,3`) by comparing CPU IDs. It still requires exactly CPUs 2 and 3, quota 25,000 us, period 100,000 us and burst zero. Raw cgroup strings remain in the evidence and the observed resource baseline remains frozen. No workloads, rates, models or scientific gates changed.

Preserve the original failed package, its `runs` directory and the complete return archive. Do not patch or reseal that attempt in place. This revision authorizes a fresh attempt in the separate directory below only for the reported failure at the unreleased resource preflight, before functional traffic or scientific slots. Confirm that the old logs show no released workload and no calibration or validation slots. If any traffic or scientific slots ran, return those records for review before launching again. Retain both attempts, including any adverse outcome from this revision. Runtime qualification on the Intel laptop remains pending.

## 1. Receive and extract

Save both `v31-host02-intel-20261019-cpuset01.tar.gz` and `v31-host02-intel-20261019-cpuset01.tar.gz.sha256` in the same directory, for example Downloads. Run:

```bash
cd "$HOME/Downloads"
sha256sum -c v31-host02-intel-20261019-cpuset01.tar.gz.sha256
```

Continue only if it says `OK`. Extract into a NEW empty directory:

```bash
mkdir "$HOME/v31-host02-handoff-cpuset01"
tar -xzf v31-host02-intel-20261019-cpuset01.tar.gz -C "$HOME/v31-host02-handoff-cpuset01"
cd "$HOME/v31-host02-handoff-cpuset01/v31-host02-intel-20261019-cpuset01"
```

If the destination already exists, preserve it and its outputs; do not overwrite an earlier setup or attempt.

## 2. Prepare without running the service

Boot directly into Ubuntu, connect AC power, and select the balanced desktop power profile. At least 20 GiB free disk is required. Docker is already reachable in your supplied report. `bpftool`, `sudo`, `taskset`, `systemd-inhibit`, and readable Intel coretemp/tracefs interfaces are additional prerequisites; setup reports missing items explicitly and stops. Do not disable tracing checks to bypass a missing prerequisite.

```bash
bash setup_v31_host02.sh
```

Setup checks your CPU and sibling topology, verifies all supplied hashes, imports the included Docker image using [Docker's archive-load command](https://docs.docker.com/reference/cli/docker/image/load/), runs offline tests, exports the exact client schedules and prepares a fresh software bundle. It starts **no containers or scientific traffic**. It should end with `HOST02 offline bundle verified: 16 calibration + 18 validation, runtime qualification pending.`

Before setup, check:

```bash
bpftool version
```

If the command is missing or fails, Ubuntu 26.04 provides the standalone [bpftool package](https://packages.ubuntu.com/en/resolute/devel/bpftool). Install that prerequisite, then verify it:

```bash
sudo apt update
sudo apt install bpftool
bpftool version
```

Do this before collection. It installs an inventory tool; it does not attach BPF programs. If installation fails or setup reports another missing requirement, preserve the exact `STOP:` or traceback text for review. No OS/Python/Docker replacement is selected automatically.

## 3. Run the bounded V31 campaign

Save work. Fully quit browsers, Codex/ChatGPT, Discord, Slack and Steam. Keep power connected and the laptop ventilated. Use a normal external terminal, not a root shell or an editor-integrated task.

```bash
cd "$HOME/v31-host02-handoff-cpuset01/v31-host02-intel-20261019-cpuset01"
bash start_v31_host02.sh
```

Expected sequence:

1. Host/package/bundle checks.
2. Unreleased resource preflight; establish your own observed memory/PID defaults and verify uncapped CPU ancestors, affinity and clock/runtime identity.
3. Six short functional cases, with owned-container cleanup verification.
4. A sudo prompt for a **read-only** observer inventory. Stay present. It does not attach probes or change settings; unknown observers or an incomplete inventory stop the run for review.
5. Stable initial settling for at least ten minutes, then **16 fresh calibration slots**.
6. Calibration qualification and forecasts sealed before **18 validation slots**. If calibration fails its declared gates, validation does not start; keep this outcome.
7. Offline raw replay and sealed result report.

Progress should show a total of **34 scientific slots**, not `MATRIX .../300`. The historical host needed about two hours; this host's duration is unknown. The whole campaign has a 3 h 30 min upper bound including cleanup reserve. Settling, technical failure or an adverse calibration result can stop it earlier.

The response deadline is **10 ms**; CPU bandwidth is **25 ms quota per 100 ms period**, burst zero. Fixed work: 88,000 SHA-256 rounds, one worker, GOMAXPROCS=1, 128 waiting slots, no yielding. Validation rates: 5/11/19 requests/s, 20 s warmup plus 60 s measurement, six counterbalanced blocks, 12,600 scheduled validation offers. Server CPUs are 2,3; client/control CPUs are 0,1. Their SMT siblings remain online; affinity does not reserve cores from other work.

The original primary models, deadlines and gates are unchanged. An ordinary complete-response calibration CDF is predeclared as an additional secondary comparator. It uses every offer from the four timing-calibration cohorts, including failures; it does not select favorable outcomes.

Do not alter rounds, rates, quota, deadline, affinity or gates after seeing results. Do not restart an interrupted/attempted campaign to obtain a pass. Ctrl+C preserves partial records and triggers owned cleanup. Never run `scripts/start_fresh.sh` for this replication.

## 4. Inspect and return all evidence

```bash
cat runs/host02/campaign/generation-01/summary.json
```

If that file is missing, keep `runs/host02/launch.log` and any interruption/qualification files. After the terminal has finished and cleanup has returned, package complete OR partial evidence:

```bash
python3 -B scripts/return_results.py
```

Send the entire `v31-host02-return-...` directory printed by that command: archive, inventory and checksum. It preserves raw requests, host measurements, sources, qualification, calibration, forecast seals, cleanup and partial/interruption records. Do not send only a screenshot or the final verdict. The inventory records the original package root for later explicit relocation replay; do not edit sealed absolute paths.

The archived historical functional cases in `assets/software_fixtures` are explicitly labelled offline software-test fixtures. Their timings never supply fresh host02 calibration. No manuscript claim or independent replication result exists until the returned host02 records are verified.
