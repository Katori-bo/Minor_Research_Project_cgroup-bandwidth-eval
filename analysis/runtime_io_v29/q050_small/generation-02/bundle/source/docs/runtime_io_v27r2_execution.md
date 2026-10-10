# Run repaired V27 generation-02

Generation-01 stopped in functional preparation because its client omitted
required clocks. Its records remain preserved. This launcher uses the separately
sealed revision-02 client and the [repair protocol](runtime_io_v27r2_protocol.md).
The scientific comparison and sixteen-trial schedule are unchanged.

Save work, connect external power, and run as a normal user in an external
interactive terminal. This quits the desktop app and waits up to 30 seconds:

```bash
bash -c '
set -euo pipefail
cd /home/Aditya/Desktop/Research_project/cpu-quota-tail-latency
pkill -TERM -x "ChatGPT|Codex" || true
for ((i=0; i<30; i++)); do
  if ! pgrep -x "ChatGPT|Codex" >/dev/null; then
    exec bash diagnostic/start_v27r2.sh run analysis/runtime_io_v27/generation-02
  fi
  sleep 1
done
printf "%s\n" "Desktop app still running; quit it fully before measurement." >&2
exit 1
'
```

Enter the sudo password for the read-only observer audit. Leave the host idle;
expect roughly 50–65 minutes under ordinary settling, with a 90-minute collection
bound and separate 10-minute preparation/analysis bounds. Runtime preparation
rechecks actual resources, both full-cycle success and cancellation cases.
Failure stops and preserves the new generation. Do not resume or rerun until
favorable. Collection stops after its report; no later experiment starts.

After reopening the app:

```bash
cd /home/Aditya/Desktop/Research_project/cpu-quota-tail-latency
python3 diagnostic/v27r2_study.py status --directory analysis/runtime_io_v27/generation-02
python3 diagnostic/v27r2_study.py verify-completion --directory analysis/runtime_io_v27/generation-02
```

Return the printed decision and latest report path. Partial offline analysis
is available after measurement-lifetime records exist:

```bash
python3 diagnostic/v27r2_study.py analyze --directory analysis/runtime_io_v27/generation-02
```
