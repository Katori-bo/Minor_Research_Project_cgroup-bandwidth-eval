# Run the V25 repeated-control diagnostic

This runs sixteen diagnostic trials and stops after independently replaying
their report. It reuses the exact qualified-to-capture native binary. It does
not run the blocked V24 scientific study or establish statistical equivalence.
See the [frozen design](runtime_io_v25_protocol.md).

Save your work, plug in the laptop and run this as your normal user in an
external interactive terminal:

```bash
bash -c '
set -e
cd /home/Aditya/Desktop/Research_project/cpu-quota-tail-latency
pkill -TERM -x "ChatGPT|Codex" || true
for i in {1..30}; do
    pgrep -x "ChatGPT|Codex" >/dev/null || break
    sleep 1
done
exec bash diagnostic/start_v25.sh run analysis/runtime_io_v25/generation-01
'
```

Enter the sudo password locally for the read-only observer inventory. Leave the
machine idle. Expect approximately 60–75 minutes including preparation,
settling and replay; collection has a 90-minute bound, with separate 10-minute
preparation and analysis limits. Thermal settling can extend the expected time
within those bounds. Nothing changes the power profile or host configuration.

Valid performance variation or an ineligible workload phase is reported,
rather than raising a qualification failure. Technical collection or replay
errors still stop the run and preserve evidence. Do not resume a failed or
interrupted generation. No automatic follow-on experiment runs.

After returning:

```bash
python3 diagnostic/v25_study.py status --directory analysis/runtime_io_v25/generation-01
python3 diagnostic/v25_study.py verify-completion --directory analysis/runtime_io_v25/generation-01
```

The report separates recording quality, observed same-condition variability,
balanced sampler comparisons and workload-state checks. Four trials per
condition/size are a design diagnostic; they do not prove equivalence or novelty.
