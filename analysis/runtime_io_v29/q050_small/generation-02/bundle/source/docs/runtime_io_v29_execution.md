# Launch the prepared overnight V29 campaign

Package revision: generation-02. Earlier unrun generation-01 bundles remain
preserved and are superseded because the observer audit path was corrected.

Status: offline preparation only; runtime functional qualification and scientific
collection must occur externally. Keep external power connected and the retained
balanced power profile. Fully quit Codex/ChatGPT before launching because the
collector's inherited quiet-host guard rejects a running desktop app.

In a normal-user external interactive terminal:

```bash
cd /home/Aditya/Desktop/Research_project/cpu-quota-tail-latency
bash diagnostic/start_v29.sh
```

The launcher checks four frozen offline bundles, asks for initial sudo
authentication, inhibits sleep, qualifies all four contexts, obtains one
read-only observer inventory and runs each independent calibration/frozen-
forecast/validation sequence. It does not rebuild or download anything.
Expected duration is approximately 6–7 hours; the complete campaign has a hard
seven-hour limit including preparation and analysis. A partial result is retained
if that bound or a qualification failure prevents completion.

Terminal output shows each slot and stage. The supervisor progress is in
`analysis/runtime_io_v29_campaign/generation-02/progress.json`; each context's
`progress.json` records its current scientific slot. Final references are in
`analysis/runtime_io_v29_campaign/generation-02/summary.json`. An interruption
has `interruption.json` and preserved attempted data. Do not rerun an attempted
generation or reopen the desktop app during collection.

After collection has stopped, inspect supervisor status:

```bash
python3 -B diagnostic/v29_campaign.py status --directory analysis/runtime_io_v29_campaign/generation-02
```

For a completed individual context, read-only full verification is:

```bash
RESEARCH_V29_CONTEXT=q025_small python3 -B diagnostic/v29_study.py verify-completion --directory analysis/runtime_io_v29/q025_small/generation-02
```

Replace both context occurrences together for another completed context.
Status markers alone are not scientific verification. The complete design,
scope, failure rules and recorded evidence are in the [protocol](runtime_io_v29_protocol.md).
