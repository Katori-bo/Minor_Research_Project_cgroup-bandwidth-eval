# V20 execution-delay factorial probe

**Decision: guardrail_tradeoff_requires_review**

Four independent blocks are an exploratory factorial probe, not confirmation or equivalence. Next-job starts bound prior publication only because there is exactly one worker. Exact publication, handler runnable readiness and CPU availability remain unobserved. Neither factor identifies an exclusive cause or proves a scheduler defect. No A/A arm or kernel observation is included; V19 repeatability does not qualify V20.

Mechanism primary: completion-to-resume mean across all offered requests, assessable only with complete timing coverage.
All offers remain in requests.csv. Unknown next-start publication bounds are never zero delay.

| Block | Yield at 100 ms: gap reduction | Yield at 20 ms: gap reduction | Period without yield: gap reduction | Period with yield: gap reduction | Guardrails vs A |
|---|---:|---:|---:|---:|---|
| 1 | 99.78% | unknown | unknown | unknown | False |
| 2 | 99.66% | unknown | unknown | unknown | False |
| 3 | 99.58% | unknown | unknown | unknown | False |
| 4 | 99.65% | unknown | unknown | unknown | False |

The independent verifier checks raw joins, exports, decision rules and all sealed attempt references.

Interrupted blocks: []

![Factorial effects](factorial_effects.png)

![Burst stages](burst_stages.png)
