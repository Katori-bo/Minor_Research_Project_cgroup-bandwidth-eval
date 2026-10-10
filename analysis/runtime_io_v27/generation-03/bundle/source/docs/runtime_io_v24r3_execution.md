# V24 native collector: qualify first

Use an external interactive terminal as your normal user, with the laptop
plugged in, balanced profile retained, and saved work. The native revision uses
new sources and prospective window-quality rules; see the
[frozen protocol](runtime_io_v24r3_protocol.md).

## Next command: actual collector qualification only

```bash
bash -c '
set -e
cd /home/Aditya/Desktop/Research_project/cpu-quota-tail-latency
pkill -TERM -x "ChatGPT|Codex" || true
for i in {1..30}; do
    pgrep -x "ChatGPT|Codex" >/dev/null || break
    sleep 1
done
exec bash diagnostic/start_v24r3.sh qualify analysis/runtime_io_v24/generation-03
'
```

Enter the sudo password locally when requested. Leave the PC idle. This repeats
real resource/function checks and runs exactly four collector-qualification
trials: one off/on pair at each size. Expect approximately 25–30 minutes including
preparation and the initial 10-minute idle; the qualification collection itself has
a 30-minute bound. Runtime preparation and offline report replay have separate
10-minute bounds. It stops after the qualification report. A failed or incomplete
qualification blocks the full study and preserves every attempt.

Offline software receipts alone are insufficient: actual cgroup latency and
sampler effects must be assessed under the retained service workload. One
engineering pair per size does not confirm the scientific explanation.

## Later, after qualification passes

Review its report before running the separate scientific collection. With the
app fully quit and the same boot/sources retained:

```bash
bash diagnostic/start_v24r3.sh run analysis/runtime_io_v24/generation-03
```

This command independently verifies qualification and performs fresh observer
review before the twelve scientific trials. Qualification data are not pooled
with scientific data. Allow roughly 75 minutes. No automatic full run follows
qualification, and neither phase resumes after an attempted interruption.

## Saved-data checks

```bash
python3 diagnostic/v24r3_study.py verify-bundle --directory analysis/runtime_io_v24/generation-03
python3 diagnostic/v24r3_study.py status --directory analysis/runtime_io_v24/generation-03
python3 diagnostic/v24r3_study.py verify-qualification --directory analysis/runtime_io_v24/generation-03
```

The last command succeeds only after all real qualification requirements pass.
Preserve both failed prior generations and every new qualification failure.
