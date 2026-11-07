# Local SLO runtime readiness: setup complete, qualification pending

11 October 2026. The user authorized the host-availability/runtime-qualification
gate. Native AMD prerequisite checks and sealed image setup completed. No service
was started; no fresh functional qualification, calibration or target data were
collected. Actual time availability still requires the operator's confirmation;
the independent Intel machine's availability and readiness remain unconfirmed.

The initial portable topology guard rejected the frozen AMD control siblings
0,1. Its correction was registered before setup in preserved apparatus
supplement 3. Use only successor packages `slo-host01-20261011-runtime-v3` and
`slo-host02-20261011-runtime-v3` for the forthcoming work. Both passed 35 offline
checks and 69 compiled schedule exports. The scientific v1 plan, previous
packages, collector adapters and pending V31 handoff are unchanged.

The local machine is AMD Ryzen 5 5600H, native Linux kernel 7.2.8-arch1-2 with
the required frozen affinity available. AC is online, the power policy is
balanced, and local rootful Docker/cgroup-v2/systemd prerequisites pass. Setup
imported the exact retained Go image and the sealed NGINX runtime filesystem,
recording its fresh Docker metadata identity. Setup took approximately 0.553 s;
this is separate external image-preparation cost, not a scientific acquisition
or a runtime-qualification result. The final native check independently verified
both image identities. No host policy or observer setting was changed.

Receipts are retained in the host01 package under `runs/host01/setup/`, and copied
alongside native readback and the initial guard refusal in
`analysis/runtime_io_slo_independent/20261011-host-readiness-01/`. That snapshot
has a local hash seal. The native read-only check ran outside the sandbox because
the sandbox's virtualization status cannot establish native hardware eligibility.

## Next external action

Keep AC connected and close Codex/ChatGPT fully. The sealed package README
requires: **"Quit Codex/ChatGPT before runtime qualification"**. This satisfies
the retained quiet-host guard; it is not a new permission requirement. Image
setup is complete on local AMD, so do not rerun setup.

When the local host can be reserved for the full Go allocation (up to 3 h 30 min),
run in an external terminal:

```bash
cd /home/Aditya/Desktop/Research_project/cpu-quota-tail-latency/handoff/slo-host01-20261011-runtime-v3
systemd-inhibit --what=sleep:idle --mode=block \
  python3 -B runtime/supervisor.py run --application Go --allocation-confirmed
```

**This command includes the entire Go campaign.** It performs fresh functional
qualification and observer/quiet-host checks, then continues into calibration
and 18 target windows if all prerequisite gates pass. There is no separate
qualification-only command or pause-and-resume path. Executing it confirms the
allocation and authorizes that full single attempt. Failure remains consumed
and cannot be retried. Preserve all logs and raw evidence; return here after it
exits so the actual qualification result and cleanup can be reviewed.

NGINX follows Go on local AMD and has a separate 45-minute cap. On Intel, NGINX
must precede Go; confirm actual access/availability and avoid overlap with the
separate pending V31 replication. No message was sent to the friend and no
remote readiness or qualification is assumed. The observer-research collection
hold is unchanged: this study adds no new hardware observer or predictor.

Readiness does not establish independent validity, scientific novelty, barrier
overhead neutrality or publication suitability.
