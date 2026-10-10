# Short GC / quota-period screen

short_screen_inconclusive

Two opposite-order blocks are a prioritization screen. They cannot establish equivalence or exclude GC from the historical reversal. A signal requires at least 2% interaction in the same direction in both blocks; it is not confirmation. GC-off changes object lifetime and cache/page behavior as well as collector work.

| Cell | Period | GOGC | CPU/job ms | Busy jobs/s | 500 ms success |
|---|---:|---|---:|---:|---:|
| A | 100 | 100 | 3.664 | 147.95 | 72.02% |
| B | 100 | off | 3.659 | 147.85 | 72.78% |
| C | 20 | 100 | 3.607 | 151.51 | 84.09% |
| D | 20 | off | 3.592 | 152.11 | 86.39% |

Block CPU interactions: -0.58%, 0.04%

GC hypothesis ruled out: **False**. This screen alone cannot explain the earlier session.
