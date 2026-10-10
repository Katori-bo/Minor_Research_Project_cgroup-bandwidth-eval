#!/usr/bin/env python3
"""Create and seal only the separate NGINX scientific runner preparation."""
import argparse
from pathlib import Path
import nginx_prediction_common as c
import nginx_prediction_study as s


def initialize():
    c.n.verify(False)
    c.require(s.q.replay()['passed'], 'Prior qualification unavailable')
    c.BASE.mkdir(parents=True, exist_ok=False)
    c.save(c.BASE / 'protocol.json', c.PROTOCOL)
    c.save(c.BASE / 'lineage.json', dict(prior_bundle_sha256=c.sha(c.n.BASE / 'bundle-seal.json'),
        prior_pilot_evidence_sha256=c.sha(c.n.BASE / 'pilot/evidence-seal.json'),
        client_sha256=c.sha(c.n.SOFTWARE / 'client'), application_unchanged=True,
        new_client_binary=False, old_scientific_records_reused=False))
    print('Fresh NGINX study identity created; no scientific collection.')


def seal():
    c.n.verify(False)
    c.require(s.q.replay()['passed'], 'Prior qualification unavailable')
    c.require(not (c.BASE / 'bundle-seal.json').exists(), 'Study bundle already sealed')
    c.require(c.read(c.BASE / 'protocol.json') == c.PROTOCOL, 'Study protocol changed')
    parent = c.BASE / 'preparation'; c.verify_evidence(parent)
    rows = [s.replay_case(parent / f"cohort-{cfg['index']}", cfg) for cfg in c.configs('preparation')]
    summary = c.read(parent / 'summary.json')
    c.require(summary['passed'] and rows == summary['rows'] and summary['elapsed_sec'] <= 420,
              'Study preparation unavailable')
    c.require(all(v['successful'] == 20 for v in rows), 'Study preparation outcome failure')
    c.require((c.BASE / 'tests.log').read_text().rstrip().endswith('OK'), 'Study failure-focused tests unavailable')
    paths = [c.ROOT / name for name in c.FILES]
    paths += [c.BASE / 'protocol.json', c.BASE / 'lineage.json', c.BASE / 'tests.log',
        c.n.BASE / 'bundle-seal.json', c.n.BASE / 'pilot/evidence-seal.json']
    paths += [p for p in parent.rglob('*') if p.is_file()]
    c.save(c.BASE / 'bundle-seal.json', dict(protocol=c.PROTOCOL, baseline=s.h.common.baseline(),
        files_sha256={str(p.relative_to(c.ROOT)): c.sha(p) for p in paths}))
    c.verify()
    print('NGINX prospective protocol and separately qualified runner sealed; fresh collection pending.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=('initialize', 'seal', 'verify'))
    args = parser.parse_args()
    if args.phase == 'verify': c.verify()
    else: globals()[args.phase]()
