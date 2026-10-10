# Launch the prepared overnight V29 campaign

Package revision: generation-03. Earlier generation-01 offline bundles and the generation-02 attempt remain
preserved. Generation-02 qualified all four contexts, then stopped at sudo
authentication before any scientific trial. Generation-03 fixes terminal-bound
authentication; its runtime checks will run again.

Status: offline preparation only; runtime functional qualification and scientific
collection must occur externally. Keep external power connected and the retained
balanced power profile. Fully quit Codex/ChatGPT before launching because the
collector's inherited quiet-host guard rejects a running desktop app.

In a normal-user external interactive terminal:

```bash
cd /home/Aditya/Desktop/Research_project/cpu-quota-tail-latency
bash diagnostic/start_v29.sh
```

The launcher checks four frozen offline bundles, inhibits sleep, qualifies all
four contexts, then invokes sudo in your terminal for one read-only observer
inventory. Stay at the terminal for about four minutes, enter your password if
prompted, and wait for the first scientific context before leaving it. There is
no initial authentication whose cache must survive detached runtime preparation.
The audit has a five-minute bound including authentication; no later sudo
authentication is required by the campaign. It then runs each independent
calibration/frozen-forecast/validation sequence. It does not rebuild or download anything.
Expected duration is approximately 6–7 hours; the complete campaign has a hard
seven-hour limit including preparation and analysis. A partial result is retained
if that bound or a qualification failure prevents completion.

Terminal output shows each slot and stage. The supervisor progress is in
`analysis/runtime_io_v29_campaign/generation-03/progress.json`; each context's
`progress.json` records its current scientific slot. Final references are in
`analysis/runtime_io_v29_campaign/generation-03/summary.json`. An interruption
has `interruption.json` and preserved attempted data. Do not rerun an attempted
generation or reopen the desktop app during collection.

After collection has stopped, inspect supervisor status:

```bash
python3 -B diagnostic/v29_campaign.py status --directory analysis/runtime_io_v29_campaign/generation-03
```

For a completed individual context, read-only full verification is:

```bash
RESEARCH_V29_CONTEXT=q025_small python3 -B diagnostic/v29_study.py verify-completion --directory analysis/runtime_io_v29/q025_small/generation-03
```

Replace both context occurrences together for another completed context.
Status markers alone are not scientific verification. The complete design,
scope, failure rules and recorded evidence are in the [protocol](runtime_io_v29_protocol.md).
