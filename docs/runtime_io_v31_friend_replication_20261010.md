# V31 replication on a friend's Ubuntu laptop

Prepared 10 October 2026. The friend's laptop has Windows and an Ubuntu
partition. Boot directly into that Ubuntu installation for this study.
This document is a handoff plan, not a claim that a portable collector is
already qualified. No new measurements have been taken.

## 1. Immediate step: obtain the host information

Your friend can run this in an Ubuntu terminal now. It only reads system
information and saves a new text file. It does not install software, run the
workload, ask for sudo, change power settings or close applications.

```bash
TASK_HOST_REPORT="$HOME/v31-host-info-$(date +%Y%m%d-%H%M%S).txt"
{
  uname -r
  uname -m
  cat /etc/os-release
  lscpu
  lscpu -e=CPU,CORE,SOCKET,ONLINE
  free -h
  stat -fc %T /sys/fs/cgroup
  cat /sys/fs/cgroup/cgroup.controllers
  python3 --version
  command -v python3 docker systemd-inhibit
  docker --version
  docker info --format 'server={{.ServerVersion}} cgroup={{.CgroupVersion}} driver={{.CgroupDriver}} security={{json .SecurityOptions}}'
  systemd-detect-virt || true
} > "$TASK_HOST_REPORT" 2>&1
cat "$TASK_HOST_REPORT"
```

Missing Docker or permission errors are useful information at this stage;
they are not experimental failures. Share the file's contents so that the
host-specific package can be prepared. The report deliberately avoids a
hostname, machine UUID, Docker container listing and full process inventory.
If Docker Engine is absent, use the official
[Docker Engine Ubuntu installation instructions](https://docs.docker.com/engine/install/ubuntu/)
for the reported release. Installation and normal-user Docker access must
finish before qualification. An unsupported installation, rootless setup or
virtual machine may need a separate apparatus qualification; do not assume
the existing ownership/cgroup checks support it.

## 2. Prepare a separate replication package before collection

This part needs implementation and qualification in the project. The current
`diagnostic/start_v31.sh` is the historical launcher: it targets
`analysis/runtime_io_v31/generation-01`, refuses attempted collection, requires
historical bundles and uses a pinned Docker image. Its service, client and
watchdog also have fixed CPU numbers. Copying the completed generation and
running that launcher is not a new replication.

The host-transfer package must:

1. Use a new host/generation identity, for example `host02/generation-01`,
   with separate design, qualification, calibration, prediction and output
   directories. Preserve the original V31 evidence and seals.
2. Include the complete dependency closure, service/client/gate/native-counter
   binaries or reproducible build inputs, and the pinned service image. A Git
   clone alone does not provide all currently untracked and retained artifacts.
   For compatible native x86-64 hosts, prefer the retained application binaries
   and imported image; record their hashes and verify actual executable identity.
   If rebuilding or using another architecture is necessary, document that
   software difference before collection.
3. Map server and client/control CPUs using actual physical-core/SMT topology.
   Preserve two server logical CPUs on distinct physical cores and put
   client/control work on other physical cores. Never assume CPU 2/4 and 0/1
   have the original relationship on an Intel or different AMD laptop. Record
   the mapping and change it consistently in startup, load generator, monitor,
   watchdog and verifiers. Affinity does not guarantee exclusive CPU use.
4. Record the new Ubuntu/kernel/CPU/Go/Docker/cgroup versions, ancestry limits,
   readable temperature sensors and stable power policy. Establish a new
   host baseline rather than importing old boot, temperature, process or
   container identities. Verify the nominal quota is actually enforced and
   that ancestor limits do not silently change it.
5. Freeze the scientific plan and source/configuration hashes before collection.
   Run software checks, independent schedule exports, the resource preflight,
   six functional cases, lifecycle/owned-cleanup checks and the fresh observer
   audit on this host. Historical test data exercise software only; they do
   not supply scientific calibration parameters.
6. Supply a documented, qualified host-specific launch command. No such
   portable host02 launcher has been implemented or qualified yet; the old
   launch command is not presented here as ready to run on the friend's PC.

## 3. Keep the original scientific contract

The primary comparison is independently recalibrated transfer to another
physical host, not reuse of the first host's fitted parameters.

| Item | Frozen V31 contract |
|---|---|
| Application work | Same Go HTTP service; 88,000 rounds of the same 32-byte SHA-256 chain |
| CPU bandwidth | 25,000 us per 100,000 us; configured burst zero |
| Service | One worker, GOMAXPROCS=1, 128 waiting slots, yielding disabled |
| Calibration | Sixteen fresh slots; no copied timing or capacity samples |
| Timing-calibration cohorts | Two 30 s cohorts each at 3.75 and 7.5 requests/s; successful observed queue<=100 us samples |
| Other calibration | Two idle slots and two steady slots each at 15/22.5/30 requests/s; four 60 s mixed slots alternating 10 s at 3.75 or 7.5 requests/s and 5 s at 42.45 requests/s |
| Validation | Eighteen 60 s trials at 5/11/19 requests/s; 20 s warmup; six blocks ABC/BCA/CAB/ACB/CBA/BAC |
| Offers | 300/660/1140 per validation profile; 12,600 total |
| Primary deadline | 10 ms, unchanged |
| Validation endpoint | All scheduled offers; unsuccessful/missing offers or full scheduled-to-client-completion time > deadline are misses; equality is timely |
| Primary models | Queue-adjusted calibration CDF versus the retained uniform-phase periodic-budget model with calibrated independent response delay |
| Scientific domain | Zero recorded measurement throttled periods; >=99% of all offers have observed worker queue wait<=100 us |
| Accuracy/improvement | CDF mean block MAE<=3 pp; positive improvement in all six blocks; lower endpoint of the declared paired six-block t interval>=5 pp |
| Decisions | Original 5% miss-budget classification at 10/12 ms, including the original per-block 12 ms pass requirement |
| Secondary deadlines | 9/9.5/10.5/11/12/20/25/50/100/500 ms; retain every comparator and result |

Other calibration qualification rules, clock bounds, dispatch checks and
accounting must also follow the retained execution design. The description
above does not replace its complete machine-readable specification.

Include the ordinary complete-response CDF as an explicitly predeclared
secondary comparator in the new host study: pool all client outcomes from the
four prescribed timing-calibration cohorts, count unsuccessful outcomes as
misses and successful full-response durations above each fixed deadline,
and freeze those probabilities with the original models before validation.
When the original successful/queue-eligible pool and the complete client pool
differ, report the counts and membership difference rather than silently
trimming the complete-response pool. This is a prospective extension to the
replication; it does not change the original V31 primary gates or retroactively
make the first host's post-hoc control prospective.

## 4. Collect once the host package is qualified

Your friend should save work and quit the applications named by the qualified
quiet-host policy, plug in the laptop, use its recorded stable power profile,
and run the provided host-specific launcher from a normal-user external
terminal. Do not run the whole campaign as root. Stay present for functional
checks and the limited read-only observer-inventory sudo prompt. The launcher
must inhibit sleep and verify cleanup of its owned containers.

Collection must proceed as fresh calibration, calibration qualification,
prediction freeze, then validation. No validation result may choose the
deadline, phase, cohort, workload size, rate or comparator. The original run
took 6,780.785 s, about 1 h 53 min; budget about two hours, with the original
3 h 30 min total upper bound including reserved cleanup. First-time host
setup/qualification is additional and has no measured completion time yet.

If calibration is unavailable, collection stops before validation and that
host outcome is retained. A faster CPU may never build the busy calibration
queue at 42.45 requests/s; a slower CPU may fail low-queue/throttle criteria.
A technically valid validation domain exit is adverse transfer evidence.
Do not retry such a scientific result or adjust parameters until it passes.
Any changed workload, rate, quota or calibration-selected deadline needs a
separately frozen follow-up plan and is not an unchanged-contract V31 run.

## 5. Return the full evidence, not only the verdict

Return the entire new-host generation and campaign outputs, protocol,
qualification receipts, software/image identities, host metadata, calibration,
prediction seal, raw request/server/cgroup/clock/monitor records, technical
attempts, cleanup and partial/interruption records. The package should include
an explicit file inventory and hashes; transfer the original paths as recorded
or document any relocation adapter rather than editing sealed records.

Run the host package's offline completion verifier. Independently recompute
all-offer miss fractions, each model's eighteen trial errors, six block means,
conditional interval and domain checks. Compare host01 and host02 separately;
do not pool their requests as independent replicates. A checksum confirms
file identity; it is not a causal or generality test.

Possible outcomes:

- Confirmation on host02 strengthens reproducibility and hardware-transfer
  evidence for this one service under the declared contract.
- Calibration/domain failure identifies a limit of the unchanged-contract
  transfer; it is not a successful predictive replication.
- In-domain prediction failure is an adverse predictive transfer result.
- Near-zero or near-100% miss fractions at the fixed deadlines can be
  nondiscriminating even with accurate forecasts. Keep the result and avoid
  claiming a model advantage from trivial endpoints.

Two hosts still do not establish broad application generality, a universal
model, a new algorithm or independent-team discovery. Describe this as a
collaborating researcher's independent-hardware replication using our protocol.

## 6. Recommended route toward the extension's contribution

First complete the second-host test with the ordinary response-CDF comparator.
The immediate contribution candidate is a reproducible empirical comparison
of where the tested approximations succeed and where they fail, including the
retained NGINX adverse result. Replication strengthens that contribution;
it does not by itself prove that the finding is absent from prior literature.

Existing work already models periodic servers and profiles latency: see
[Li, Lu and Gill, RTSS 2019](https://www.cse.wustl.edu/~cdgill/publications/rtss19.pdf),
[Cucinotta et al., TCC 2023, Section 4.2.1](https://retis.santannapisa.it/people/nino/publication/TCC23.pdf),
and [CEDULE, ICAC 2018](https://www2.cs.uh.edu/~fyan/Paper/Feng-ICAC18.pdf).
Our current code is not a matched reproduction of those full methods.

If a methodological extension is later desired, a focused candidate question
is: can calibration observations identify when a deadline forecast should be
withheld before the validation workload starts? Possible inputs include
between-calibration-cohort forecast disagreement and mass near the fixed
deadline; these are research hypotheses, not validated selection criteria.
Any rule needs a separate prior-work review, development/held-out separation,
frozen thresholds and evaluation on both successful and failing settings.
Measure accepted-forecast error, fraction of conditions accepted, false
acceptance of inaccurate forecasts, and refusal of accurate forecasts.
Compare against always using the plain CDF, always using periodic+delay,
and a simple calibration-stability check under equal collection budgets.
A rule that refuses everything has no demonstrated practical utility.

Even successful validation would require assessing whether the specific rule
adds something beyond existing prediction/abstention methods. Do not advertise
the rule as a new algorithm now. A universal model is not the simplest next
step and is not required for a worthwhile scoped empirical paper.
