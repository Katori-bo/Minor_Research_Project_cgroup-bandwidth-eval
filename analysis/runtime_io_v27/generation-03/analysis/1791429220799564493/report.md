# V27r3 controlled load-composition screen

**Decision: composition_inconclusive**

This is a bounded single-service composition screen. Model-based intervals require independent approximately normal block contrasts. No universal equivalence, runtime mechanism, deadline-sampler neutrality, estimator superiority or novelty is established. No follow-on collection is launched.

| Trial | Low jobs/s | Sampler | Whole CPU/job ms | Busy capacity rps | Busy queue | All offers successful |
|---|---:|---|---:|---|---|---|
| b1_low15_on | 15 | on | 3.5197 | 150.000–150.000 | True | True |
| b1_low30_off | 30 | off | 3.6458 | 150.083–150.083 | True | True |
| b1_low15_off | 15 | off | 3.5200 | 149.500–149.500 | True | True |
| b1_low30_on | 30 | on | 3.6448 | 149.167–149.167 | True | True |
| b2_low30_on | 30 | on | 3.6427 | 149.833–149.833 | True | True |
| b2_low15_off | 15 | off | 3.5313 | 150.000–150.000 | True | True |
| b2_low30_off | 30 | off | 3.6427 | 149.500–149.500 | True | True |
| b2_low15_on | 15 | on | 3.5120 | 149.833–149.833 | True | True |
| b3_low15_off | 15 | off | 3.5158 | 150.083–150.250 | True | True |
| b3_low15_on | 15 | on | 3.5179 | 149.583–149.583 | True | True |
| b3_low30_on | 30 | on | 3.6276 | 149.750–149.750 | True | True |
| b3_low30_off | 30 | off | 3.6160 | 150.083–150.083 | True | True |
| b4_low30_off | 30 | off | 3.6460 | 149.917–149.917 | True | True |
| b4_low30_on | 30 | on | 3.6415 | 150.333–150.333 | True | True |
| b4_low15_on | 15 | on | 3.5258 | 149.667–149.667 | True | True |
| b4_low15_off | 15 | off | 3.5331 | 149.667–149.667 | True | True |

| Sampler | Cost contrast mean % [95% interval] | Busy contrast mean % [95% interval] |
|---|---|---|
| off | 3.194 [2.720, 3.669] | 0.042 [-0.475, 0.559] |
| on | 3.419 [2.989, 3.849] | 0.000 [-0.662, 0.662] |

Intervals use four independent blocks with three degrees of freedom and include accounting bounds.
They assume approximately normal independent block contrasts. State, cohort and observer checks remain separate.

Raw records, all failed screens, phase bounds, interactions, descriptive deadlines and seals are retained in report.json.
No automatic calibration, deadline validation or next generation follows.
