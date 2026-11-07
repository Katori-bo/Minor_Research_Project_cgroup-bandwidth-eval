# Independent decision evaluation: collector integration supplement 1

11 October 2026. Offline engineering only. The frozen scientific v1 protocol,
deadlines, estimators, schedules, host allocations and budgets remain unchanged.
No new qualification, calibration or validation outcomes have been collected.

## Completed implementation

`replication/slo_decision/collectors.py` derives separate Go and NGINX collection
functions from the retained sources through exact, checked source adaptations.
It executes them in a separate namespace; it does not mutate historical modules
or expose their campaign/retry entry points. The retained service guards,
draining, monitors, per-service watchdogs and ownership cleanup calls remain in
the collection paths. The caller must supply the qualified apparatus namespace;
this module is not a scientific launcher.

Calibration must already be frozen and intact before a target service/warmup.
Go validates the entire warmup schedule and drains the service before recording
availability; NGINX drains and validates the full successful warmup before that
event. At the measurement process boundary, the adapter seals the three ordinary
forecasts, raw warmup identity and exact configuration identity, then durably
writes the permit. Both file contents and directory entries receive fsync.
It checks the frozen one-second bound and boot before entering Popen, records
the timestamp immediately before that call, then records the owned child and
release. A failed release cleans the child even if the retained loop has not yet
received its handle. These are supervisor events, not inferred absolute HTTP
completion times or third-party timestamps.

The adapter retains every scheduled offer, including ordinary failures and
Go's explicitly accounted client drops. Corrupt NGINX responses are unavailable,
not ordinary transport misses. Go's retained raw/server replay remains required
for response and service integrity. Every acquired warmup is charged; only its
last 25 outcomes update the two declared methods. Forecast code reads warmup
only. Receipt replay checks raw warmup hashes, identities, schedule accounting,
clock order and numerical forecast reconstruction before reading target data.
Final trust also requires the preserved apparatus source seal and inherited
raw/resource replay; internally consistent JSON alone does not prove collection.

`report.py` preserves 72 planned slots and all deadline labels, with separate
complete-trusted and primary-domain views. Applicability exits remain in the
complete-trusted adverse view; partial/corrupt/unobserved windows have no
complete-window decision. It reports point and DKW decisions, false assurances,
rejections, abstentions, availability and the fixed denominators. Undefined risk
denominators remain null. Only primary-domain q97.5 reference events contribute
to the independent-hardware recurrence indicator.

## Offline evidence

Thirty-nine synthetic checks pass: the original 19 scientific/barrier checks,
16 collector extraction/integration checks, and four report checks. The tests
execute the adapted retained Go `collect/load` and NGINX `trial/Service.collect`
paths with fake services/processes and independently supplied synthetic rows.
They verify durable permit-before-spawn ordering, replay, accounting,
invalid-warmup refusal, boot changes, late barriers, resource-budget admission,
host-guard failure, retained load timeout/cleanup, release failure cleanup,
foreign configurations and consumed-slot refusal. Synthetic records are not
scientific observations, hardware qualification or a runtime-overhead benchmark.

The supplement includes generated collector sources, patches, the unchanged
scientific snapshot, test outputs, consumed source hashes and a local SHA-256
seal. It refuses overwrite. The original 288-file Intel V31 package is verified
unchanged before and after preparation. Static import inventory is recorded;
it is not a packaged or qualified runtime dependency closure.

## Remaining implementation and operational gate

**Collection remains NO-GO.** This completes collection-function integration and
the report layer, not portable launchers. The retained runtime namespaces still
bind historical generation/boot/resource paths. A dedicated portable backend
must establish fresh host baselines while preserving the original guards, and
a separate external campaign supervisor must enforce the hard campaign cap,
owner-safe cleanup and campaign-level refusal to resume/retry. The adapter's
admission checks supplement that supervisor; they cannot interrupt a blocked
service startup or enforce a hard cap by themselves.

Fresh-calibration assembly must require all 16 qualified Go slots and its
inherited capacity/timing prerequisite before selecting all offers from the
four declared reference cohorts; NGINX must qualify the three external cohorts
before pooling its four fresh calibration cohorts. Neither arbitrary lists
accepted by the arithmetic library nor historical calibration may substitute
for this runtime provenance. Acquisition-stage time/offer costs need that
campaign supervisor's ledger. Host availability and runtime qualification are
also pending. No historical launcher is offered as a substitute.

The next engineering work is therefore **portable runtime backend and dedicated
external supervisor**, followed by qualification under the sealed apparatus.
Preserve this supplement when adding that layer; seal its source before any
new qualification outcome. The observer hardware hold and the separate pending
V31 handoff remain in force.

From the repository, replay the supplement with:

```bash
python3 -B replication/slo_decision/build_apparatus.py verify \
  --output analysis/runtime_io_slo_independent/20261011-apparatus-01
```
