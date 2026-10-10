# Run repaired V27 generation-03

This separate generation preserves the scientific comparison and uses bounded
monitor readiness/completion. Generation-02 remains stopped and preserved.
Use this command only after generation-03's offline bundle has been prepared
and verified. Save work, connect external power and use an external interactive
terminal as your normal user. It quits the desktop app and waits up to30 seconds.

```bash
bash -c '
set -euo pipefail
cd /home/Aditya/Desktop/Research_project/cpu-quota-tail-latency
pkill -TERM -x "ChatGPT|Codex" || true
for ((i=0; i<30; i++)); do
  if ! pgrep -x "ChatGPT|Codex" >/dev/null; then
    exec bash diagnostic/start_v27r3.sh run analysis/runtime_io_v27/generation-03
  fi
  sleep 1
done
printf "%s\n" "Desktop app still running; quit it fully before measurement." >&2
exit 1
'
```

Enter your sudo password for the read-only observer audit. Leave the machine
idle while collection runs; expect roughly50–65 minutes with ordinary settling.
Preparation and analysis each have a separate10-minute bound; collection has
a90-minute bound. The launcher requalifies actual resources and all four
functional cases, then runs the sixteen composition trials. It stops after
the report. On failure, preserve the output and return it for diagnosis;
do not rerun this generation or return to an older launcher.

After reopening the app, inspect the saved result with:

```bash
cd /home/Aditya/Desktop/Research_project/cpu-quota-tail-latency
python3 -B diagnostic/v27r3_study.py status --directory analysis/runtime_io_v27/generation-03
python3 -B diagnostic/v27r3_study.py verify-completion --directory analysis/runtime_io_v27/generation-03
```

Return the printed decision and latest report path. If collection stopped after
measurement-lifetime records were created, preserve an incomplete report with:

```bash
python3 -B diagnostic/v27r3_study.py analyze --directory analysis/runtime_io_v27/generation-03
```
