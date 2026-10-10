# V24 execution: prepare offline now, collect only in the next quiet window

The offline bundle at `analysis/runtime_io_v24/generation-01/bundle` is a frozen
software/design package. It contains the original retained binaries and
synthetic software-check receipts. It has not contacted Docker, run a workload,
performed root authentication or qualified the new sampler on the real service.
Actual resource and four functional/cancellation checks are deliberately deferred
to the external launch. They must pass before any of the twelve measured trials.

Read [the fixed question and rules](runtime_io_v24_frozen_question.md). This
experiment measures CPU/completion separately during sustained backlog and
light load, and checks counter-sampler perturbation with paired off/on runs.
It does not introduce a new service binary or change host settings.

## Next quiet-window command

Use an external interactive terminal as your normal user, with the laptop plugged
in and the retained balanced power settings. Save work in Codex/ChatGPT first.
The command below requests normal app termination and waits up to30 seconds.
The launcher refuses to proceed if the app remains present.

```bash
bash -c '
set -e
cd /home/Aditya/Desktop/Research_project/cpu-quota-tail-latency
pkill -TERM -x "ChatGPT|Codex" || true
for i in {1..30}; do
    pgrep -x "ChatGPT|Codex" >/dev/null || break
    sleep 1
done
exec bash diagnostic/start_v24.sh run analysis/runtime_io_v24/generation-01
'
```

At this future launch only, enter your sudo password locally when the read-only
observer inventory requests it. The workload itself runs without root. No sudo,
Docker or benchmark command was issued during unattended preparation.

The launcher verifies the offline bundle, qualifies the actual retained image,
startup resources and sampler with four short cases, obtains a fresh observer
ownership review, then starts the quiet collection. No automatic rebuilding,
host-setting adjustment, existing-container cleanup or measurement resume occurs.
Source/image/resource/topology/power/boot problems stop the run and preserve
evidence. A reboot before first runtime preparation is allowed: that preparation
captures the current boot and the experiment qualifies it afresh. A reboot after
runtime preparation requires a new generation rather than reuse of old receipts.

Runtime qualification is bounded to10 minutes, collection to60 minutes including
initial10-minute settling, and offline analysis to10 minutes, with cleanup grace
for runtime phases. Expected collection is approximately50–55 minutes plus
several minutes for qualification and verification. The collection watchdog is
disarmed after completed collection/cleanup and before offline report replay,
preventing the V23 final-replay interruption from consuming its measurement
allowance. Thermal or technical delays can still produce incomplete evidence.

## Read-only checks and recovery

These commands read saved evidence and do not launch a service:

```bash
python3 diagnostic/v24_study.py verify-bundle --directory analysis/runtime_io_v24/generation-01
python3 diagnostic/v24_study.py status --directory analysis/runtime_io_v24/generation-01
```

After collection, an offline report can be generated or independently verified:

```bash
python3 diagnostic/v24_study.py analyze --directory analysis/runtime_io_v24/generation-01
python3 diagnostic/v24_study.py verify-completion --directory analysis/runtime_io_v24/generation-01
```

Do not run `prepare-runtime`, the launcher or `_foreground` until a quiet window
is available. Do not resume an interrupted generation. A failed runtime
preparation is retained; use a new offline generation after reviewing its cause.
Existing V22/V23 protocols, sources and data remain sealed and unchanged.
