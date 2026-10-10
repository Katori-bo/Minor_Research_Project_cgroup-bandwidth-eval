# V30 fresh collection

V30 uses the unchanged scientific specification in
`docs/runtime_io_v30_confirmation_protocol_20261009.md`. Its original sealed
design continues to say implementation was pending at specification time;
the new offline bundle and preparation review record implementation status.
Runtime qualification occurs in the external launcher before any scientific
trial. No V30 performance measurements have been collected during development.

The separate `v30_*` collector, verifier, service ownership label and output
namespace preserve all V29 sources and records. Six runtime functional cases
include idle, high steady load, retained calibration burst, new steady profile A,
new 2-second profile C and cancellation. One additional unreleased FIFO resource
preflight verifies the packaged executable and limits before those six cases.
At most 41 containers may be released: six functional, 34 scientific, one
ordinary technical retry. The unreleased preflight is a separately accounted
container, so at most 42 containers are created. Scientific failures are retained
outcomes; deliberate interruption, watchdog intervention and lifetime expiry
are terminal. No automatic resume or extra blocks are allowed.

All sixteen calibration trials must qualify before validation. Delay residuals
come only from the four new low-rate calibration trials; negative values make
the primary model unavailable and stop validation. All nine deadlines and every
per-offer miss probability are sealed before the first validation offer. The
100 sampled phase values are an assumed uniform prior; kernel phase is neither
measured nor selected from outcomes. Sampled envelopes retain the Stage A
no-added-delay scenario definition, with empty/full credit and calibration
capacity extremes. They are secondary diagnostics, not confidence bounds.
The frozen discovery model-switch heuristic can give a nonmonotone miss curve
when it changes models above 25 ms; report that discontinuity explicitly. It is
a comparison of separate forecasts, not one coherent latency distribution.

The collector retains all-offer failures and server/client stage records.
Steady low-load validation does not require a nonempty queue, successful cohort,
or V29's busy-window capacity gate. Raw replay still checks clock, resource,
dispatch, ownership, cohort conservation, reset, drain, power and monitor state.
The six-block accuracy, improvement and SLO gates are unchanged from the sealed
protocol. Both negative and inconclusive results are useful evidence.

The preparation watchdog is 600 seconds, observer authentication/inventory
300 seconds, measurement 9000 seconds (including settling and forecast freeze),
offline analysis 900 seconds, active service lifetime 360 seconds and total
campaign 12600 seconds with 120 seconds reserved for cleanup. Expect roughly
two hours; adverse settling or software/state failures stop the generation.

Save your work first: the command below gracefully terminates the named desktop
applications. Run it in an ordinary terminal outside Codex/ChatGPT. Keep the PC
plugged in, retain the balanced power profile and do not reopen those apps until
collection finishes. Sleep is inhibited while the campaign runs. Stay present
until the post-qualification sudo prompt has accepted your password and the
first calibration trial has begun.

```bash
bash -c '
set -euo pipefail
cd /home/Aditya/Desktop/Research_project/cpu-quota-tail-latency
TASK_APPS="ChatGPT|Codex|chrome|chromium|firefox|brave|msedge|Discord|discord|slack|steam"
pkill -TERM -u "$UID" -x "$TASK_APPS" || [ "$?" -eq 1 ]
sleep 5
exec bash diagnostic/start_v30.sh
'
```

On success read:
`analysis/runtime_io_v30_campaign/generation-01/summary.json` and the sealed
report referenced by `analysis/runtime_io_v30/generation-01/latest_analysis.json`.
If collection stops, preserve the entire generation and campaign directories;
do not rerun this launcher until the interruption has been reviewed.
