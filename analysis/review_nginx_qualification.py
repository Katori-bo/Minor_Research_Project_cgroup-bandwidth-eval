#!/usr/bin/env python3
"""Read-only evidence replay, with a separate review artifact on first invocation."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'diagnostic'))
import nginx_qualify as q


def main():
    replay = q.replay()
    n = q.n
    pilot = n.BASE / 'pilot'
    n.require(replay == n.read(pilot / 'replay.json'), 'Saved replay differs')
    summary = n.read(pilot / 'summary.json')
    n.require(not summary['original_fifo_queue_domain_established'], 'Unsupported queue claim')
    out = ROOT / 'analysis/runtime_io_nginx_qualification_review/20261009-generation02'
    if out.exists():
        for name, digest in n.read(out / 'evidence-seal.json')['files_sha256'].items():
            n.require(n.sha(ROOT / name) == digest, 'Review changed: ' + name)
        print('Qualification and saved review verify:', out / 'report.md')
        return
    report = dict(replay, elapsed_sec=summary['elapsed_sec'],
        warmup_offers=3 * n.PROTOCOL['warmup_offers'],
        measurement_throttled_periods=sum(r['measurement_counter_delta']['nr_throttled'] for r in summary['rows']),
        measurement_throttled_usec=sum(r['measurement_counter_delta']['throttled_usec'] for r in summary['rows']),
        cohort_median_e2e_ms=[r['median_e2e_ns'] / 1e6 for r in summary['rows']],
        cohort_dispatch_max_ms=[r['dispatch_max_ns'] / 1e6 for r in summary['rows']],
        all_runtime_identity_and_cleanup_verified=True,
        original_fifo_queue_domain_established=False,
        prediction_accuracy_tested=False, independent_host_replication=False,
        novelty_established=False, ready_for_scientific_collection=False,
        next_step='Freeze and qualify a fresh complete-response prediction protocol; use new calibration and held-out trials.')
    out.mkdir(parents=True, exist_ok=False)
    n.save(out / 'report.json', report)
    (out / 'report.md').write_text('''# Stock NGINX qualification: verified pass

Generation 02 completed the predeclared three stock cohorts at 5 requests/s
in 168.746 seconds. All 600 measured responses and 75 warmup responses passed
full compressed-body decoding, input-hash and request-ID checks. Each cohort
passed dispatch, stock request conservation, stable process/thread identity,
resource/runtime provenance and owned cleanup checks. All measurement increments
of both nr_throttled and throttled_usec were zero. Raw evidence, the preparation
bundle, root observer inventory and saved analysis replay verify.

The three cohort medians were 20.572, 20.522 and 20.471 ms; maximum dispatch
delays were 1.103, 1.175 and 1.179 ms. These are qualification observations,
not a scientific calibration or a test of a deadline forecast. No pilot sample
may be promoted into the future calibration or held-out validation sets.

Stock NGINX is now qualified for the declared complete-response measurements.
Its internal queue is unobserved. A maximum of one overlapping client response
window does not establish the original FIFO queue domain. This successful
qualification does not reverse the preserved imgproxy or gzip failures.

Next, declare a new full-response CDF prediction study, including all waiting.
Retain unchanged application/input settings, fresh calibration, sealed forecasts,
held-out rates, block-level inference, all-offer outcomes and explicit technical
and applicability exits. Do not import V31's queue subtraction or paired-stage
periodic/residual comparator. The scientific runner needs separate implementation
and qualification before collection. Accuracy, application transfer and novelty
remain untested; this same-host study cannot establish hardware independence.

The inherited "Selection seal verifies; service implementation/qualification
remain pending" console line comes from the historical gzip selection verifier.
The authoritative current NGINX status is stock_full_response_measurement_qualified.
''')
    inventory = Path(n.read(pilot / 'observer-inventory.json')['path'])
    paths = [Path(__file__).resolve(), out / 'report.json', out / 'report.md',
             n.BASE / 'bundle-seal.json', pilot / 'evidence-seal.json', inventory]
    n.save(out / 'evidence-seal.json', dict(files_sha256={str(p.relative_to(ROOT)): n.sha(p) for p in paths}))
    print(out / 'report.md')


if __name__ == '__main__':
    main()
