# Independent SLO evaluation: host readiness and qualification gate

11 October 2026. The user authorized proceeding with host availability and
external runtime qualification. The local AMD machine passes a read-only native
host prerequisite check. Time availability and the independent Intel machine's
readiness still need confirmation. No image setup, service, qualification,
calibration, target run or new hardware observer has started during preparation.

## Pre-outcome apparatus correction

The first local check exposed an overly strict portable topology guard. It
required all service and control CPUs to occupy different physical cores, but
the frozen AMD control pair 0,1 consists of SMT siblings on physical core 0.
Service CPU 2 occupies physical core 1 and service CPU 4 occupies core 2.
The corrected guard permits the prescribed AMD control sharing while requiring
distinct service physical cores disjoint from all control cores. Intel retains
its existing distinct control-core requirement. CPU allocations, scientific
endpoints, schedules and budgets are unchanged. Original packages, apparatus
supplements and the failed read-only check are preserved. No campaign allocation
was consumed by this prerequisite check.

The accepted successor packages are `handoff/slo-host01-20261011-runtime-v3` and
`handoff/slo-host02-20261011-runtime-v3`, registered in apparatus supplement 3.
Both pass 35 offline checks and 69 compiled schedule exports. The two added
checks cover actual AMD sibling numbering and the retained Intel numbering,
including rejection of service/control overlap and Intel control overlap.
These checks are software validation, not runtime qualification.

The native prerequisite check records AMD Ryzen 5 5600H, kernel
7.2.8-arch1-2, all 12 allowed logical CPUs, AC online, balanced power policy,
local rootful Docker with cgroup v2/systemd, readable temperature sensors and
over 160 GiB free space. It validates fresh state; it does not substitute for
quiet-host, observer-inventory, response-integrity or workload qualification.
The sandbox reports a virtualized environment, so it cannot qualify this native
apparatus. The read-only native check ran outside that sandbox.

## External actions

Use an external terminal on the matching machine. Keep AC connected and the
recorded balanced policy; fully quit Codex/ChatGPT for qualification. Confirm
that the host is actually available. The full study later allocates up to
4 h 15 min per host. Do not overlap with pending V31 work on Intel.

First run image setup, which starts no service or scientific traffic:

```bash
cd /home/Aditya/Desktop/Research_project/cpu-quota-tail-latency/handoff/slo-host01-20261011-runtime-v3
python3 -B runtime/setup.py verify-package
python3 -B runtime/setup.py setup
python3 -B runtime/setup.py check
```

On Intel, use its transferred host02 successor package directory. Preserve any
setup failure; do not rerun setup into a replacement directory. Setup success
means images and prerequisites are ready, not that runtime qualification passed.
Its receipts are under `runs/<host>/setup/`.

The existing scientific campaign command is **not qualification-only**: after
preparation, observer checks and qualification gates pass it continues through
fresh calibration and the 18 target windows. Executing it authorizes that full
single-attempt allocation. Use it only when ready for the entire bounded
campaign; it does not support stopping for review and resuming later.

Local host01 first campaign, once setup and availability are confirmed:

```bash
systemd-inhibit --what=sleep:idle --mode=block \
  python3 -B runtime/supervisor.py run --application Go --allocation-confirmed
```

Its second campaign is NGINX, using the same command with `--application NGINX`.
Intel host02 runs NGINX first, then Go. Qualification failure closes its consumed
allocation with unavailable target windows; no favorable replacement is allowed.
All stages remain charged to the frozen cap. Preserve raw files, logs, cleanup
and return seals. A genuinely unavailable host remains pending until explicit
study closure; absence of a reply does not confirm it or consume its cells.

At this checkpoint only the prerequisite check has passed. External image setup,
quiet-host qualification and independent scientific validation remain pending.
No novelty or publication claim follows from readiness.
