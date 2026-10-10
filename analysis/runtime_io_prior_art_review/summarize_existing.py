#!/usr/bin/env python3
"""Re-read existing follow-up results; collect no new performance data."""
import csv
import hashlib
import json
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "results/followup/all-in-one-v2/full"
OUT = Path(__file__).resolve().parent
INPUTS = [
    SOURCE / "analysis/trials.csv", SOURCE / "analysis/validation.json",
    SOURCE / "matrix.json", SOURCE / "build.json", SOURCE / "metadata.json",
    SOURCE / "source/followup/service/Dockerfile",
]


def hashes():
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in INPUTS}


def main():
    before = hashes()
    validation = json.loads(INPUTS[1].read_text())
    if validation.get("passed") is not True or validation.get("issues"):
        raise ValueError("Historical validation did not pass")
    rows = list(csv.DictReader(INPUTS[0].open(newline="")))
    matrix = json.loads(INPUTS[2].read_text())
    by_id = {c["run_id"]: c for c in matrix}
    if len(rows) != 50 or len(by_id) != 50 or {r["run_id"] for r in rows} != set(by_id):
        raise ValueError("Expected complete 50-trial follow-up")
    selected = [r for r in rows if r["study"] == "A"]
    metrics = ["p99_e2e_ms", "successful_rps", "rejection_fraction",
               "timeout_fraction", "other_error_fraction",
               "cpu_usec_per_completed_work", "cpu_cores", "throttled_period_fraction"]
    groups = {}
    for g in (1, 2):
        group = [r for r in selected if int(r["gomaxprocs"]) == g]
        if len(group) != 5 or {int(r["rep"]) for r in group} != set(range(1, 6)):
            raise ValueError("Expected five distinct replicates per setting")
        for r in group:
            c = by_id[r["run_id"]]
            expected = {"period_us": 100000, "quota_us": 50000, "workers": 4,
                        "gomaxprocs": g, "pattern": "steady", "rate": 176.41,
                        "iterations": 44000, "duration_sec": 60, "warmup_sec": 20}
            if any(c[k] != v for k, v in expected.items()):
                raise ValueError(f"Unexpected configuration: {r['run_id']}")
        groups[str(g)] = {
            "trials": [r["run_id"] for r in group],
            "metrics": {m: {"median": median(float(r[m]) for r in group),
                            "min": min(float(r[m]) for r in group),
                            "max": max(float(r[m]) for r in group)} for m in metrics},
        }
    untested = [c["run_id"] for c in matrix if c["pattern"] == "bursty" and c["gomaxprocs"] == 1]
    if untested:
        raise ValueError("The asserted missing bursty comparison is present")
    ratios = {m: groups["1"]["metrics"][m]["median"] / groups["2"]["metrics"][m]["median"]
              for m in metrics if groups["2"]["metrics"][m]["median"] != 0}
    after = hashes()
    if after != before:
        raise ValueError("An input changed during analysis")
    result = {"review_date": "2026-10-03", "historical_validation_passed": True,
              "input_sha256": before, "inputs_unchanged": True,
              "total_trials": len(rows), "groups_by_gomaxprocs": groups,
              "gomaxprocs_1_over_2_ratio_of_trial_medians": ratios,
              "bursty_gomaxprocs_1_trials_in_this_matrix": untested,
              "limitations": ["Descriptive trial summaries, not paired causal estimates.",
                              "Historical steady overload differs from the diagnostic bursty workload.",
                              "Lower CPU cost changes effective capacity; not a fairness-only intervention.",
                              "No new benchmark or runtime change was performed."]}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "existing_followup_summary.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"input_hashes_unchanged": True, "selected_trials": len(selected),
                      "ratios": ratios}, indent=2))


if __name__ == "__main__":
    main()
