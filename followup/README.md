# Run the whole follow-up with one command

**Collection status:** The `results/followup/all-in-one-v2/` run completed on 2026-09-28 with eight validated pilot and 50 validated full trials. Its `COMPLETED.md` and `full/analysis/` contain the results. The commands below document the original workflow and can create separate sessions; they are not needed to finish the completed run.

```bash
/home/Aditya/Desktop/Research_project/cpu-quota-tail-latency/followup/run_all.sh
```

This starts a background workflow: build and Go tests → Python regression tests → eight diagnostic pilot trials → pilot analysis and acceptance checks → all 50 full trials → final analysis and completion report. Each stage must pass before the next starts. Allow roughly **3–5 hours** on a quiet host; temperature settling can extend the run or stop it.

Keep the laptop plugged in, set to Balanced, and leave the lid open. The launcher requests a temporary systemd sleep/idle inhibitor while it runs, then releases it when finished. It has no interactive password prompts. If inhibition or Docker access fails, the log explains the failure. Once startup is reported successful, you may close the terminal.

All output is under:

```text
/home/Aditya/Desktop/Research_project/cpu-quota-tail-latency/results/followup/all-in-one/
```

- `COMPLETED.md`: written only after full collection and analysis validate successfully.
- `workflow-status.json`: current stage, completion or reason for a stop.
- `logs/`: separate log for every launch; earlier logs remain available.
- `pilot/` and `full/`: separate raw sessions, numbered attempts and analysis outputs.
- `full/analysis/estimates.json`: Study A and B estimates with trial-level uncertainty.

Check progress:

```bash
/home/Aditya/Desktop/Research_project/cpu-quota-tail-latency/followup/run_all.sh status
```

After an interruption, rerun the original command. It resumes the same sessions and retains failed attempts. A repeated command while the workflow is running reports its status; after completion it reports the saved result. Existing sessions keep their original build and source hashes. A failed pilot gate stops full collection and requires investigation; rerunning does not silently change its acceptance criteria or substitute new pilot observations.

To deliberately start a separate workflow after a documented source/protocol change, choose a new directory:

```bash
./followup/run_all.sh --directory results/followup/all-in-one-v2
```

The coordinator holds the existing experiment lock across all stages, so the original runner and other follow-up jobs cannot overlap it. Automated workflow tests simulate success/failure/resume and test lock inheritance; they do not collect research data.

## Individual stage commands

The code review found and corrected completion/reset races, weak resume validation, an underloaded replication arm, and ambiguous throughput accounting before collection. Go tests run during the Docker build; Python tests run independently. The live quota pilot is still required.

From the repository root, build and run the diagnostic pilot (about 25–35 minutes if cooling is prompt):

```bash
cd /home/Aditya/Desktop/Research_project/cpu-quota-tail-latency
./followup/build.sh
python3 -m unittest discover -s followup -p 'test_*.py' -v
python3 followup/run.py new --pilot --session results/followup/pilot-20260926
python3 followup/analyze.py results/followup/pilot-20260926
```

Keep the host plugged in and set to Balanced, with other heavy workloads closed. The initial ten-minute settling period is intentional. The runner never changes thermal/power settings or bypasses acceptance checks.

For an interrupted pilot, reuse its directory:

```bash
python3 followup/run.py resume --session results/followup/pilot-20260926
python3 followup/analyze.py results/followup/pilot-20260926
```

After pilot analysis reports success, review `analysis/report.md` and `analysis/pilot_gate.json`. Start the 50-trial full experiment (typically 2.5–4 hours) with:

```bash
python3 followup/run.py new --session results/followup/full-20260926 --pilot-session results/followup/pilot-20260926
```

Resume and analyze the full experiment:

```bash
python3 followup/run.py resume --session results/followup/full-20260926
python3 followup/analyze.py results/followup/full-20260926
```

A new session refuses an existing directory. Use `resume` after interruptions; keep all numbered attempts. Source/image/binary/protocol changes require a new pilot session with a new directory name and a rebuild when Go source changes. `failure.json` marks rejected attempts; `complete.json` seals accepted file hashes. SIGKILL/power-loss leftovers are reported by exact owned container ID; inspect those before removing them and resuming.

Full collection requires a passed pilot with matching source and evidence hashes. It will not launch simply because a pilot folder exists. Research output is `analysis/trials.csv`, all trial values in `analysis/report.md`, `analysis/attempt_audit.csv`, and `analysis/estimates.json`. Study A and B estimates remain separate. See `docs/followup_protocol.md` and `docs/followup_analysis_plan.md` for the timing populations and methodological limitations.
