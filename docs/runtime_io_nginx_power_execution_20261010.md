# Executable NGINX power-policy study

10 October 2026. Implementation of the
[candidate contract](runtime_io_nginx_power_policy_candidate_20261010.md).
Preparation/software tests are distinct from hardware qualification and results.
The original application, client, campaigns and protocol files are preserved.

## Running the prepared generation

Open an external terminal, fully quit Codex/ChatGPT, and run as the normal user:

```bash
bash /home/Aditya/Desktop/Research_project/cpu-quota-tail-latency/diagnostic/start_nginx_power.sh
```

The launcher requests sudo credentials locally, inhibits sleep, verifies the
prepared source/runtime chain and schedule, audits leftover observers, executes
two real policy-control fixture cycles (including an owned child exit test),
and runs four qualification smoke cohorts. Only a passing raw/evidence replay
permits the scientific campaign. No retries, replacements or overwrites.

The quiet-desktop requirement comes from the retained collection guard
[imgproxy_qualify.py](../diagnostic/imgproxy_qualify.py), `desktop_absent`:
“fully quit Codex/ChatGPT before overhead qualification.” The new runner calls
that guard in qualification and measurement. Preparing files in this chat is
not a performance measurement. Do not bypass the guard to run within the app.

Ceilings: qualification 10 minutes; scientific campaign 45 minutes including
cleanup reserve. Total scientific offers 9,500: 4 calibration cohorts x 400,
24 validation cohorts x 300, and 25 warmup offers for every scientific cohort.
The primary deadline remains 20,565,395 ns. The fresh calibration predictions
and per-cohort warmup predictions are saved before their validation measurements.

## Policy ownership and restoration

The privileged helper has a fixed CPU2 sysfs target and accepts only set P0,
set P1, check and finish. It holds a nonblocking exclusive host lock, verifies
the baseline and all policy fields, journals intent before writing the EPP,
and reads back the setting at each phase boundary. It never writes another
policy, governor, min/max, boost, idle-state or security setting.

Each lease is at most 150 seconds. The helper independently monitors the
runner PID/start identity and monotonic deadline. It restores the original EPP
on normal finish, owner exit, control EOF, timeout, rejected command or handled
termination signal. The qualification fixture tests actual restoration after
an owned child exits, rather than treating mocked software tests as host proof.
The service/container has its original separate owned cleanup watchdog.

Boundary policy snapshots exclude instantaneous frequency: this is an EPP
intervention, not fixed-frequency evidence. CPU3 procstat snapshots are taken
before/after measurement to describe sibling activity. They do not identify
competing tasks or establish CPU isolation. Ten-second settling is retained;
it is not proof of thermal reset or absence of treatment carryover.

Restoration cannot survive the privileged helper itself receiving SIGKILL,
kernel failure or loss of power. If restoration fails, stop and inspect the
exact policy journal; do not claim a valid outcome. Parent/service failure
is covered by the independent helper. No implementation can make a userspace
watchdog survive arbitrary destruction of that watchdog.

## Forecasting and analysis

The source-sealed seed generates balanced fresh calibration and six uniformly
permuted validation blocks. Forecasts are ordinary pooled, policy-conditioned,
baseline-only and warmup CDFs, plus sample-weighted matched/warmup and
pooled/warmup updates. No fitted weights, thresholds or new estimator.

The comparison uses six block means. Useful matching requires average MAE
improvement >=2 pp with its conditional 95% block interval excluding zero,
and matched MAE's conditional upper bound <=5 pp. Per-cohort maximum, errors
>5 pp and all cell-level errors remain visible. Secondary deadlines are
10/25/50 ms; none replaces the primary endpoint.

An exact 4,096-assignment test conditions on the two rate positions per block
and flips the within-rate policy assignments under the sharp policy-null.
It assumes credible randomized assignment without interference/carryover.
Report that limitation, not an unconditional causal frequency explanation.
Consecutive blocks and calibration samples are not automatically iid.

Ordinary failures remain all-offer misses. Corrupt output, foreign identity or
policy readback invalidates trustworthy measurement. Throttling, client overlap,
dispatch or calibration/qualification failures stop the campaign with all
completed/partial raw records retained. No favorable early stopping.

## Files and replay

Prepared and collected files go only to
`analysis/runtime_io_nginx_power_policy/generation-01/`. Qualification and campaign
directories are exclusively created. An attempted run cannot be resumed or
replaced. Source changes after preparation fail verification.

```bash
cd /home/Aditya/Desktop/Research_project/cpu-quota-tail-latency
python3 -B diagnostic/nginx_power_study.py verify
python3 -B diagnostic/nginx_power_study.py dry-run
# After a complete collection:
python3 -B diagnostic/nginx_power_study.py replay
```

The campaign summary reports completion or the phase/reason of stopping.
`campaign/comparison.json` contains the complete numerical comparison if
collection completes. No statistical result or novelty follows from preparation,
unit tests, qualification, verified preferences or observer presence alone.

Preparation found a different boot identity from the original NGINX run, with
the same kernel and recorded topology. Historical seals are verified without
representing historical qualification as current-boot qualification. This
generation seals a fresh baseline and requires the fixture/smoke qualification
on that exact baseline. A further reboot before execution invalidates the
prepared generation; do not bypass the check or treat it as a performance retry.
