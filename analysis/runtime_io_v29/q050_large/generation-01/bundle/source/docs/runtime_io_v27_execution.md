# Run V27 controlled load-composition comparison

This launcher performs runtime preparation, fresh observer inventory, sixteen
fixed trials and independent analysis, then stops. See the
[frozen protocol](runtime_io_v27_protocol.md).

Offline generation: `analysis/runtime_io_v27/generation-01`. Runtime functional
qualification and all sixteen trials remain unrun until this external command.
Save your work, connect external power, and open a normal-user external terminal.
The combined command quits ChatGPT/Codex gracefully, waits up to 30 seconds,
then launches the test:

```bash
bash -c '
set -euo pipefail
cd /home/Aditya/Desktop/Research_project/cpu-quota-tail-latency
pkill -TERM -x "ChatGPT|Codex" || true
for ((i=0; i<30; i++)); do
  if ! pgrep -x "ChatGPT|Codex" >/dev/null; then
    exec bash diagnostic/start_v27.sh run analysis/runtime_io_v27/generation-01
  fi
  sleep 1
done
printf "%s\n" "Desktop app is still running; quit it fully before measurement." >&2
exit 1
'
```

Enter the sudo password locally for the read-only observer audit. Keep the
machine idle. Expect approximately 50–65 minutes under ordinary settling;
collection has a 90-minute bound, with separate 10-minute preparation/analysis
limits. No host setting is changed. Failure preserves the generation; do not
resume it or rerun until favorable.

After reopening the app:

```bash
cd /home/Aditya/Desktop/Research_project/cpu-quota-tail-latency
python3 diagnostic/v27_study.py status --directory analysis/runtime_io_v27/generation-01
python3 diagnostic/v27_study.py verify-completion --directory analysis/runtime_io_v27/generation-01
```

The generation's `latest_analysis.json` points to its sealed report. Return that
path for interpretation. A supportive screen requires qualified mixed states,
both sampler-arm cost and busy-stability screens, and observer interactions.
An inconclusive or failed result is retained without automatic follow-up.

If collection is interrupted after measurement-lifetime records exist, generate
an offline partial report without any workload:

```bash
python3 diagnostic/v27_study.py analyze --directory analysis/runtime_io_v27/generation-01
```

Partial reports remain `composition_incomplete`. Runtime preparation failures
without measurement-lifetime records remain preparation failures in status.
