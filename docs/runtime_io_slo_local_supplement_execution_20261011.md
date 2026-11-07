# Corrected local execution: supplement 01

Use only `handoff/slo-host01-20261011-local-supplement-03` for this conditional
amendment. The earlier supplement-01 build failed during offline source adaptation;
supplement-02 is a superseded offline preparation. Neither started collection.
Original v3, v4 and v6 packages and all their evidence remain preserved.

The final package passed 53 offline checks. Its scientific plan SHA-256 is
`932fea8cf61bbe2b17f76d183e2f258012e1ab7119bba06e7e754388f818291d`;
its runtime package seal SHA-256 is
`382881b9d7615471fa04112276c41c0eea3a305610b71b2b0308ca5961c1100c`.
Offline preparation started no Docker commands, service traffic or hardware
inventory. External runtime qualification remains pending.

## Meaning of the execution flags

`--amendment-accepted` explicitly accepts the separate local supplement described
in `runtime_io_slo_local_supplement_protocol_20261011.md`: 36 new fixed target
slots and an additional campaign cap of 15,300 s (4 h 15 min), with one attempt
per service. This does not replace the original study's unavailable slots or
constitute independent hardware replication. `--allocation-confirmed` confirms
availability of the declared native AMD host for the selected allocation.
Preparing this package records neither acceptance nor availability.

## First command: fresh setup and Go

Save any work before running this external command. The launcher performs a
read-only package, lineage and order check, then closes the named background
apps, waits five seconds, performs fresh image setup once and runs Go under
`systemd-inhibit`. Power and native host eligibility are checked by the runtime.
The maximum Go campaign cap is 12,600 s (3 h 30 min), in addition to image setup.

```bash
bash /home/Aditya/Desktop/Research_project/cpu-quota-tail-latency/handoff/slo-host01-20261011-local-supplement-03/start_local_supplement.sh \
  Go --amendment-accepted --allocation-confirmed
```

This launcher is already equivalent to the previous `bash -c` wrapper. It runs
from its own directory, closes the same named apps and records amendment
acceptance before setup or service release. Do not add a separate setup command.
Sudo authentication occurs directly in the external terminal.

## Second command: NGINX after Go is closed

After the Go allocation has closed, retain its result even if it stopped early.
Then use the next command for the second allocation. The launcher checks the
closed Go return and the successful supplemental setup; it does not repeat setup.
The NGINX campaign cap is 2,700 s (45 min).

```bash
bash /home/Aditya/Desktop/Research_project/cpu-quota-tail-latency/handoff/slo-host01-20261011-local-supplement-03/start_local_supplement.sh \
  NGINX --amendment-accepted --allocation-confirmed
```

If supplemental setup itself failed, do not run NGINX or delete the setup state.
If either campaign fails or is interrupted, retain its complete terminal output
and evidence; this amendment supplies no further automatic retry. Repeating the
launcher for an already attempted allocation refuses before closing apps.

## Evidence and report

New evidence is under the final package's `runs/host01` directory, including the
amendment acceptance, setup, Go and NGINX directories. Keep its complete contents
and the sibling original v3, v4 and v6 packages. Original source and return seals
are verified read-only. The separate supplement report has 36 slots and carries
original costs in a separate historical ledger. The original v1 report still
has 72 slots, with Intel pending; do not describe the supplement as replacing it.

After both supplemental allocations are closed, assemble a new report:

```bash
python3 -B /home/Aditya/Desktop/Research_project/cpu-quota-tail-latency/handoff/slo-host01-20261011-local-supplement-03/runtime/assemble_returns.py \
  --host-package /home/Aditya/Desktop/Research_project/cpu-quota-tail-latency/handoff/slo-host01-20261011-local-supplement-03 \
  --output /home/Aditya/Desktop/Research_project/cpu-quota-tail-latency/analysis/runtime_io_slo_independent/local-supplement01-return.json
```

Assembly performs no service or host collection and refuses to overwrite an
existing output file. Novelty and independent validity remain unresolved.
