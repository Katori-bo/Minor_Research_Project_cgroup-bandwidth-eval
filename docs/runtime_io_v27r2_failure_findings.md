# V27 generation-02: host-monitor count failure

Verified 8 October 2026. Runtime preparation and the clock repair passed. The
first composition slot, `b1_low15_on`, was attempted twice. Both attempts failed
the frozen host-monitor record-count screen; the one technical retry was
exhausted and collection stopped. No trial received an accepted completion
marker. This generation cannot support the scientific composition comparison.

| Check | First attempt | Retry |
|---|---:|---:|
| Required host-monitor records | 80 | 80 |
| Actual records | 79 | 79 |
| Desktop-app flag rows | 0 | 0 |
| Power-setting mismatch rows | 0 | 0 |
| Mean record interval (s) | 1.031410 | 1.031070 |
| First-to-last timestamp span (s) | 80.469 | 80.443 |
| Measurement offers / successes | 3,996 / 3,996 | 3,996 / 3,996 |
| Warmup offers / successes | 300 / 300 | 300 / 300 |
| Owned cleanup errors | 0 | 0 |

Both attempts recorded all six client clock anchors. No client drops, missed
arrivals, admission rejections or other unsuccessful offers were reported.
Client p99 dispatch lag was approximately 1.06–1.07 ms. Cleanup receipts verify
owned container/cgroup removal without watchdog intervention; the recorded
cgroup paths are absent.

The common error text groups three checks together. Here only the record count
failed. The retained monitor sleeps one second, then scans/read records and
runs its process inspection. That work adds approximately 31 ms per record;
the 80-record minimum was set too tightly against 20-second warmup plus
60-second measurement. Seventy-nine records can therefore span over 80 seconds.
The minimum is a frozen count requirement, not proof that the host changed
power settings or the desktop app ran. Recorded interval sums likewise do not
replace the frozen screen or establish all required endpoint coverage.

The [sealed diagnosis](../analysis/runtime_io_v27r2_failure_review/20261008/report.json)
retains both attempt references, exact counts/intervals, quiet/power checks and
cleanup evidence. The [offline partial report](../analysis/runtime_io_v27/generation-02/analysis/1791423912070421519/report.json)
retains `composition_incomplete` with zero accepted trials and both technical
failures. Original records, sources and thresholds remain unchanged.

The next software repair should give the host monitor sufficient startup and
shutdown lifetime for the required records, with a bounded wait and clear
failure reason. Preserve the 80-record screen, native capture/drain rules and
scientific design. Verify the actual lifecycle with a monitor that takes more
than one second per record before preparing a separate frozen generation.
Do not resume generation-02 or rerun the existing launcher unchanged. No new
measurement or repaired generation was launched as part of this diagnosis.
