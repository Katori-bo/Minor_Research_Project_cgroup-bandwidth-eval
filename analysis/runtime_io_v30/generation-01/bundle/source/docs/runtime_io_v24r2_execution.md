# V24 generation-02: repaired sampler, new quiet-window run

Generation-01 is retained as incomplete after two counter-read timing failures.
Generation-02 uses separately named revision2 modules. The original scientific
question and all acceptance thresholds are retained. Read the
[sampler revision](runtime_io_v24r2_sampler_revision.md) and
[original V24 question](runtime_io_v24_frozen_question.md).

The offline bundle contains a sealed full110-second synthetic-file recording,
software checks, original retained binaries, design and source snapshots.
Actual Docker/cgroup qualification and all12 measurements remain unrun until
the external launch. Preparation cannot use a missing or mismatched full-length
software receipt. A software check is not a scientific result or real-service
qualification.

## One-command external launch

Plug in the laptop, retain the balanced power profile, save work in the desktop
app, and use an external interactive terminal as your normal user:

```bash
bash -c '
set -e
cd /home/Aditya/Desktop/Research_project/cpu-quota-tail-latency
pkill -TERM -x "ChatGPT|Codex" || true
for i in {1..30}; do
    pgrep -x "ChatGPT|Codex" >/dev/null || break
    sleep 1
done
exec bash diagnostic/start_v24r2.sh run analysis/runtime_io_v24/generation-02
'
```

Enter the sudo password locally when the read-only inventory requests it, then
leave the computer idle. The launcher verifies the package, freshly qualifies
the retained image/resources and four functional/cancellation cases, binds a
fresh observer review and collects all12 trials with sampler off/on pairs at
both work sizes. It changes no host settings. It never resumes generation-01.

Expect roughly50–55 minutes for collection plus preparation and analysis;
allow approximately75 minutes overall. Preparation is bounded to10 minutes,
collection to60 minutes including initial10-minute settling, and analysis
separately to10 minutes. Runtime cleanup grace is120 seconds. Thermal or
technical delays can still exhaust these limits and leave an incomplete result.

## Read-only status and verification

```bash
python3 diagnostic/v24r2_study.py verify-bundle --directory analysis/runtime_io_v24/generation-02
python3 diagnostic/v24r2_study.py status --directory analysis/runtime_io_v24/generation-02
```

After collection, these commands replay existing evidence without a workload:

```bash
python3 diagnostic/v24r2_study.py analyze --directory analysis/runtime_io_v24/generation-02
python3 diagnostic/v24r2_study.py verify-completion --directory analysis/runtime_io_v24/generation-02
```

Do not rerun an attempted or interrupted generation. All scientific failures
and technical attempts remain recorded; one technical retry is permitted across
the entire schedule. A reboot before first runtime preparation is allowed; a
reboot after runtime preparation requires a fresh generation. Source or software
receipt changes also require a new software check and package.
