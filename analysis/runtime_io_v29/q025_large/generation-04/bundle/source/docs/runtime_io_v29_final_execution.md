# Fresh final V29 condition

Run only **q025_large**: quota 25000 us per 100000 us, request work 88000
iterations, retained worker, queue, CPU affinity, traffic and deadline rules.
The new session is `analysis/runtime_io_v29/q025_large/generation-04`; supervisor
records go to `analysis/runtime_io_v29_campaign/generation-04-final`.

Collect all 16 calibration trials afresh. Freeze all five estimators and their
per-offer predictions before the 16 validation trials in four balanced blocks.
Six functional cases qualify the runtime first. Existing binary exports and
the sealed q025_large scientific design are retained exactly. No estimates,
validation outcomes or calibration records from the partial run enter this run.

Generation-03 remains preserved: three fully verified contexts and the separate
partial q025_large context. For the complete matrix, report the first three
generation-03 contexts and the new generation-04 context; disclose the interrupted
run separately. Do not pool the two q025_large runs or erase the interrupted
attempts. Across-day/context order is confounded with time; this remains a
within-service, single-host robustness study rather than universal generality.

The follow-up uses separate runner and verifier modules, preserving the original
generation-03 sources and their reproducibility. The runner fixes signal handling:
an intentional interruption ends collection and cannot trigger a technical retry.
The lifetime is checked before each new attempt and before any technical retry.
The original one-retry allowance for ordinary technical failures remains.

Expected duration is about two hours (the completed contexts previously took
105–109 minutes for measurement before analysis). The supervisor permits a hard
three-hour maximum including preparation, authentication, measurement, analysis
and a 120 s cleanup reserve. Original per-context bounds remain: preparation
600 s, measurement 7200 s, analysis 600 s, active container watchdog 360 s.
Scientific qualification rules are unchanged. Failure stops or marks the run
incomplete; do not resume an attempted generation automatically.

Save open work, connect external power, retain the balanced power profile and
fully quit Codex/ChatGPT. In an external interactive terminal as your normal user:

```bash
cd /home/Aditya/Desktop/Research_project/cpu-quota-tail-latency
bash diagnostic/start_v29_final.sh
```

The launcher verifies the new frozen offline bundle and inhibits sleep. Stay at
the terminal for functional checks (about one minute), authenticate if sudo
prompts for the fresh read-only observer audit, then wait for
`Starting independent context q025_large`. No further password prompt is needed
by the campaign. Leave the terminal open and Codex closed until it finishes.

The supervisor saves `summary.json` on successful collection and verified analysis,
or `interruption.json` on failure. A successful collection can still fail a
scientific accuracy screen; report that outcome unchanged.

After the terminal reports completion or returns to the shell, status is:

```bash
RESEARCH_V29_CONTEXT=q025_large python3 -B diagnostic/v29r4_campaign.py status \
  --directory analysis/runtime_io_v29_campaign/generation-04-final
```

Full scientific verification after completion is:

```bash
RESEARCH_V29_CONTEXT=q025_large python3 -B diagnostic/v29r4_study.py verify-completion \
  --directory analysis/runtime_io_v29/q025_large/generation-04
```
