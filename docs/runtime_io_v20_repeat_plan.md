# One faithful V20 repeat after the period-cost reversal

Prepared 2026-10-06. This is a new, bounded repeat explicitly requested after the
period-cost pilot reversed V20's CPU/job and capacity contrast. It does not
overwrite generation-03, replace an adverse accepted trial, or resume the cost
pilot. The [audit](runtime_io_period_reversal_audit.md) found no implementation or
arithmetic mismatch explaining the discrepancy; attribution remains unresolved.

## Frozen scope and question

Repeat the exact V20 source, original binaries/image, workload, resource
contract, four full-duration qualification rehearsals and sixteen trials in
the original four-block order. Generation-04's 115 source hashes, binary hashes,
matrix, workload, kernel/boot/topology and resource baseline match generation-03.
The original protocol, guardrails and analysis remain unchanged.

The diagnostic question is: **does the shorter-period penalty return when the
original V20 collection path is restored?** This repeat is not by itself a
causal test of temperature, power commands or helper overhead. Actual host
conditions remain measured rather than guaranteed equal across sessions.

Preparation passed 36 tests, four resource preflights and six short functional
checks. A/B/C/D each retained 114 successful offers. Cancellation controls
retained all 453 offers and exercised missing handler evidence. These are
functional checks, not performance results. At preparation completion the new
generation has zero rehearsals and zero benchmark trials.

Before interpreting performance, retain every trial and inspect CPU/job,
500/1,000 ms outcomes, capacity using the same fixed busy windows, warmup
outcomes, queue/processing/handler stages, temperature, desktop CPU, power,
affinity and client dispatch records. Keep per-block effects and exploratory
block uncertainty. The whole-service CPU denominator remains all completed
computations, with rejected work preserved separately. Do not rerun until a
desired sign appears, pool the two sessions as independent request replications,
or change thresholds after seeing the repeat. Interpretation of CPU-period
repeatability supplements the original V20 report; it does not redefine its
completion-to-handler primary.

Possible outcomes, declared before collection:

- **V20-like penalty returns:** the pilot path or differing conditions become
  candidates for a targeted comparison. Similar host summaries would strengthen
  the harness candidate, without proving it caused the result.
- **Pilot-like improvement persists:** the pilot-only collector is unnecessary
  for the reversal. Investigate what changed across V20 sessions; narrow the
  earlier shorter-period claim instead of assuming a universal penalty.
- **Contrast is inconsistent or uncertain:** period effects are not stable
  enough under this design for a cost-mechanism explanation.

No branch automatically launches another experiment. A later controlled
comparison must state the intervention, competing predictions and an adequacy
check for the host/harness variable it intends to alter.

## External launch

Use the original app-close method. The profile is read and checked, not set.
Save work first; plug into AC, keep the external terminal open and the app fully
closed. Keep the display, desktop and other activity consistent with the earlier
manual procedure. Do not launch performance from the app or alongside another
benchmark. The runner records its new thermal baseline using the original
policy; it does not force V20's 48.5 C baseline.

```bash
(
  set -e
  cd /home/Aditya/Desktop/Research_project/cpu-quota-tail-latency
  TASK_REPEAT="$PWD/analysis/runtime_io_v20_execution_delay/generation-04"

  python3 diagnostic/execution_delay_study.py verify-preparation --directory "$TASK_REPEAT"

  if command -v powerprofilesctl >/dev/null 2>&1; then
    if [[ "$(powerprofilesctl get)" != balanced ]]; then
      echo "Balanced is required. No profile setting was changed; launch stopped."
      exit 1
    fi
  fi

  pkill -TERM -u "$(id -u)" -x ChatGPT || true
  sleep 5
  if pgrep -a -x ChatGPT; then
    echo "ChatGPT is still running; fully quit it before measurement."
    exit 1
  fi

  bash diagnostic/start_execution_delay.sh run "$TASK_REPEAT"
)
```

No sudo is needed. Allow roughly 75-100 minutes, longer if cooling takes time.
The original design has a minimum of 56 minutes 40 seconds for initial idle and
20 × (60 s settling + 20 s warmup + 60 s arrivals), before startup, drain,
additional cooling, plots and raw verification. This is an estimate, not a
guaranteed finish time. Preserve an interrupted attempt for review.

Status after collection:

```bash
cd /home/Aditya/Desktop/Research_project/cpu-quota-tail-latency
python3 diagnostic/execution_delay_study.py status \
  --directory "$PWD/analysis/runtime_io_v20_execution_delay/generation-04"
```

The runner automatically analyzes and independently verifies completed results.
The generation's `latest_analysis.json` identifies the saved report. Bring back
that report or the retained interruption instead of restarting generation-04.
