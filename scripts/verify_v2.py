#!/usr/bin/env python3
"""Short Docker smoke checks, clearly separated from scientific measurements."""
import datetime as dt
import json
from pathlib import Path
import experiment as exp


def main():
    session = exp.ROOT / 'results/verification' / dt.datetime.now().strftime('%Y%m%d-%H%M%S')
    exp.initialize(session, True)
    reports = []
    for label, cfg in [
        ('unlimited', exp.config(40000, 40, period=0)),
        ('limited_steady', exp.config(40000, 80, period=10000, workers=4)),
        ('limited_burst', exp.config(40000, 80, period=100000, workers=4, pattern='bursty')),
        ('overload', exp.config(40000, 200, period=100000, workers=4)),
    ]:
        r = exp.trial(session, 'pilot', label, cfg, duration=10, warmup=2)
        reports.append(r)
        assert r['monitor_samples'] >= 7, 'Missing monitor samples'
        assert r['loadgen_metrics']['total_completed'] == r['loadgen_metrics']['total_dispatched']
        if label == 'unlimited':
            assert r['cgroup_metrics']['delta'].get('nr_throttled', 0) == 0
        if label == 'overload':
            assert r['cgroup_metrics']['delta'].get('nr_throttled', 0) > 0
            assert r['loadgen_metrics']['elapsed_including_drain_sec'] > 10
    exp.write_json(session / 'verification.json', {'passed': True, 'trials': len(reports)})
    print(f'Verification passed. Diagnostic output: {session}')


if __name__ == '__main__':
    main()
