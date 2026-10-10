# Work dispatched ahead of delayed HTTP handlers

All 24 previously matched pre-handler examples use the audited original-time traces. The intervals overlap; counts must not be added across examples.

| Trial | HTTP G | Next request | Ready wait ms | Dispatches | Worker | HTTP | Other/unclassified | Worker-reply handoffs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| fairness_b1_patched_on | 1769 | 467 | 2820.776 | 1654 | 376 | 814 | 464 | 349 |
| fairness_b1_patched_on | 1771 | 470 | 2820.510 | 1601 | 376 | 797 | 428 | 349 |
| fairness_b1_patched_on | 1767 | 473 | 2820.482 | 1599 | 376 | 795 | 428 | 349 |
| fairness_b1_stock_on | 1713 | 1750 | 2112.476 | 1311 | 285 | 635 | 391 | 261 |
| fairness_b1_stock_on | 1649 | 1751 | 2112.462 | 1309 | 285 | 634 | 390 | 261 |
| fairness_b1_stock_on | 1667 | 1752 | 2112.448 | 1307 | 285 | 633 | 389 | 261 |
| fairness_b2_patched_on | 1710 | 653 | 2200.029 | 1182 | 288 | 595 | 299 | 263 |
| fairness_b2_patched_on | 1830 | 673 | 2100.447 | 1153 | 274 | 577 | 302 | 250 |
| fairness_b2_patched_on | 1826 | 681 | 2081.446 | 1235 | 264 | 604 | 367 | 241 |
| fairness_b2_stock_on | 1936 | 1852 | 2615.006 | 1465 | 352 | 740 | 373 | 329 |
| fairness_b2_stock_on | 2283 | 1855 | 2610.706 | 1458 | 350 | 737 | 371 | 328 |
| fairness_b2_stock_on | 2295 | 1871 | 2604.917 | 1436 | 346 | 729 | 361 | 324 |
| fairness_b3_patched_on | 1825 | 572 | 2208.919 | 1311 | 302 | 639 | 370 | 276 |
| fairness_b3_patched_on | 1805 | 579 | 2208.147 | 1249 | 301 | 618 | 330 | 276 |
| fairness_b3_patched_on | 1806 | 567 | 2207.957 | 1256 | 301 | 623 | 332 | 278 |
| fairness_b3_stock_on | 1688 | 683 | 1281.325 | 662 | 164 | 337 | 161 | 150 |
| fairness_b3_stock_on | 1801 | 608 | 1209.133 | 700 | 166 | 354 | 180 | 151 |
| fairness_b3_stock_on | 1661 | 613 | 1204.517 | 693 | 166 | 354 | 173 | 153 |
| fairness_b4_patched_on | 1693 | 1749 | 2021.530 | 1211 | 270 | 591 | 350 | 250 |
| fairness_b4_patched_on | 2479 | 1753 | 2008.602 | 1115 | 268 | 558 | 289 | 250 |
| fairness_b4_patched_on | 1917 | 1766 | 1921.813 | 1237 | 257 | 598 | 382 | 238 |
| fairness_b4_stock_on | 2061 | 1671 | 2521.705 | 1502 | 344 | 736 | 422 | 318 |
| fairness_b4_stock_on | 1654 | 1673 | 2518.691 | 1493 | 342 | 731 | 420 | 316 |
| fairness_b4_stock_on | 2277 | 1695 | 2513.279 | 1474 | 339 | 723 | 412 | 312 |

The JSON retains every dispatch timestamp, G, M, P and source line, plus per-goroutine counts and same-P handoff examples. Roles come from request-task associations and runtime/HTTP stacks; unmatched goroutines stay unclassified.

Dispatch means Runnable→Running, not continuous CPU execution. Work can already be running when the target wakes. These traces show what got turns, but do not record the pending flag or global/local/runnext selection branch. The v10 aggregate counters cannot be joined retrospectively to these v9 requests.

A separate bounded decision recorder is needed to associate an actual fairness selection with a delayed HTTP G in the untraced workload. No correction, qualification gate or new performance collection is introduced.
