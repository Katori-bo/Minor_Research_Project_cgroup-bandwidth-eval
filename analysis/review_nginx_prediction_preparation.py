#!/usr/bin/env python3
"""Verify sealed scientific preparation and retain its engineering-only review."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'diagnostic'))
import nginx_prediction_common as c
import nginx_prediction_study as s


def main():
    c.verify()
    parent = c.BASE / 'preparation'
    c.verify_evidence(parent)
    summary = c.read(parent / 'summary.json')
    rows = [s.replay_case(parent / f"cohort-{cfg['index']}", cfg) for cfg in c.configs('preparation')]
    c.require(summary['passed'] and summary['rows'] == rows, 'Preparation summary differs')
    c.require(sum(r['offers'] for r in rows) == 60 and all(r['successful'] == 20 for r in rows),
              'Preparation full-body outcomes differ')
    refusal = c.BASE / 'preparation-sandbox-refusal'
    c.verify_evidence(refusal)
    review = c.read(c.BASE / 'sandbox-refusal-review.json')
    c.require(review['no_container_created'] and review['no_workload_collected'] and
        review['refused_evidence_seal_sha256'] == c.sha(refusal / 'evidence-seal.json'), 'Sandbox refusal review differs')
    out = ROOT / 'analysis/runtime_io_nginx_prediction_preparation_review/20261009-generation01'
    if out.exists():
        for name, digest in c.read(out / 'evidence-seal.json')['files_sha256'].items():
            c.require(c.sha(ROOT / name) == digest, 'Preparation review changed')
        print('Preparation review verifies:', out / 'report.md'); return
    out.mkdir(parents=True)
    c.save(out / 'report.json', dict(status='sealed_scientific_runner_preparation_verified',
        services=3, measurement_offers=60, warmup_offers=75, tests=17,
        elapsed_sec=summary['elapsed_sec'], all_raw_replays_match=True,
        all_runtime_identity_and_cleanup_verified=True, rows=rows,
        sandbox_refusal_preserved=True, new_rate_performance_qualification_pending=True,
        scientific_collection=False, prediction_accuracy_tested=False, novelty_established=False))
    (out / 'report.md').write_text('''# NGINX scientific runner preparation: verified

The separate generation-01 prospective protocol and runner are sealed in 108
files. Seventeen failure-focused tests passed. Three real stock services exercised
the exact 4, approximately 6 and 8 requests/s schedules: 60 measured and 75 warmup
responses were correct. Body endpoints, schedules, request counts, runtime/source
identity, single-CPU process/thread snapshots, counters, owned cleanup and raw
replay verify. Preparation took 27.543 seconds with the desktop open; it does not
qualify performance or contribute scientific observations.

The earlier sandbox Docker-access refusal collected no requests and created no
container. Its refused raw evidence and exact source snapshot are preserved;
normal-host engineering preparation then passed. All original application
qualification bundles and failed candidate histories remain frozen.

The external launcher first runs three 100-offer new-rate performance checks,
then four fresh 400-offer calibration cohorts at 5 requests/s. It seals the exact
lower-median deadline, full-response CDF and miss forecasts before eighteen
300-offer held-out trials in six balanced blocks. Expected duration is about
30 minutes, capped at 45. Collection stops at its first technical/applicability
exit; the campaign cannot resume, repeat or overwrite this generation.

The primary analysis conditions on the frozen forecast and reports a block-level
model-based interval against a declared five-point accuracy tolerance, together
with per-rate errors and calibration-cohort sensitivity. Calibration uncertainty
is not converted into an unconditional population guarantee. Server queue is
unobserved and never subtracted. Prediction accuracy, scientific application
transfer, novelty and independent-host replication remain untested.
''')
    paths = [Path(__file__).resolve(), out / 'report.json', out / 'report.md', c.BASE / 'bundle-seal.json']
    c.save(out / 'evidence-seal.json', dict(files_sha256={str(p.relative_to(ROOT)): c.sha(p) for p in paths}))
    print(out / 'report.md')


if __name__ == '__main__': main()
