# V26 low-load qualification pilot

**Decision: both_low_rates_qualified**

Two on recordings per rate qualify only fixed steady windows. They do not establish future mixed-state eligibility, deadline equivalence, causality or statistical uncertainty. No follow-on collection is launched.

Recording validity and low-state qualification are separate. Busy-delivery check is inapplicable.

| Trial | Rate jobs/s | CPU/completion bounds ms | Queue maximum | Throttled-period bounds | Low state | Misses % (descriptive) |
|---|---:|---|---:|---|---|---:|
| low15_r1 | 15 | 4.5189–4.5458 | 1 | [0, 0] | True | 0.000 |
| low30_r1 | 30 | 4.5616–4.5773 | 1 | [0, 0] | True | 0.000 |
| low30_r2 | 30 | 4.5462–4.5618 | 1 | [0, 0] | True | 0.000 |
| low15_r2 | 15 | 4.5734–4.6041 | 1 | [0, 0] | True | 0.000 |

Raw records, completion and CPU bounds, acquisition diagnostics and trial seals are retained in report.json.
No automatic mixture experiment follows this pilot.
