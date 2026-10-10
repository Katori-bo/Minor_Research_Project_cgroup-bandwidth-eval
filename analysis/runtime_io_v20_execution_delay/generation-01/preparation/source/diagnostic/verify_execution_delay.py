#!/usr/bin/env python3
"""Independent V20 preparation/qualification/completion checks from retained raw data."""
import argparse
import csv
from pathlib import Path
import sys

import execution_delay_common as c
import execution_delay_analysis as analysis
from environment_controls import POLICY, comparable_power, window_summary


def verify_preparation(session, current=True):
    prep = session/'preparation'
    c.verify_seal(prep)
    manifest = c.read(prep/'manifest.json')
    if (manifest['schema'] != 1 or manifest['matrix'] != c.matrix()
            or manifest['workload'] != c.WORKLOAD or not manifest['tests_passed']
            or not manifest['functional_passed'] or manifest['performance_run']
            or (prep/'preparation_failure.json').exists()):
        raise ValueError('preparation/protocol/test receipt differs')
    if c.read(prep/'arrivals.json') != c.arrivals():
        raise ValueError('prepared offered schedule differs')
    expected = {'gate': 'gate_sha256', 'loadgen': 'loadgen_sha256',
                'original.server': 'server_sha256', 'image.server': 'server_sha256'}
    for name, key in expected.items():
        if c.digest(prep/name) != manifest[key]:
            raise ValueError('prepared input hash differs: '+name)
    for name, sha in manifest['sources'].items():
        if c.digest(prep/'source'/name) != sha:
            raise ValueError('frozen source differs: '+name)
        if name.endswith('.py') and c.digest(c.ROOT/name) != sha:
            raise ValueError('loaded Python implementation differs from snapshot: '+name)
    previous = c.read(c.V19/'preparation/manifest.json')
    if (manifest['v19_preparation_seal'] != c.digest(c.V19/'preparation/seal.json')
            or any(manifest[k] != previous[k] for k in ('image', 'server_sha256', 'loadgen_sha256', 'gate_sha256', 'resource_baseline'))):
        raise ValueError('original V19 provenance/resource contract differs')
    proof = c.read(prep/'publication_build.json')
    if (c.digest(prep/'publication_build.json') != manifest['publication_build_sha256']
            or c.digest(prep/'publication_source.go') != manifest['publication_source_sha256']
            or proof['prepared_sha256']['service/main.go'] != manifest['publication_source_sha256']
            or proof['images']['service'] != manifest['image']):
        raise ValueError('original single-worker publication proof differs')
    if c.read(prep/'image.json')['Id'] != manifest['image']:
        raise ValueError('actual image inspection differs')
    for arm in c.ARMS:
        preflight = prep/'resource_preflight'/arm
        observed = c.read(preflight/'observed.json')
        if (observed['baseline'] != manifest['resource_baseline'] or observed['gate_released']
                or observed['config'] != c.fixture(arm)):
            raise ValueError('resource preflight differs')
        inspect = c.read(preflight/'container.json')['inspect']
        initial = c.read(preflight/'initial.json')
        if observed['limits'] != initial['initial_limits']:
            raise ValueError('resource preflight observation differs')
        c.validate_resources(observed['limits'], inspect['HostConfig'], manifest['resource_baseline'], c.fixture(arm))
        if inspect['Image'] != manifest['image'] or c.digest(preflight/'container.server') != manifest['server_sha256']:
            raise ValueError('preflight actual executable differs')
        cleanup = c.read(preflight/'cleanup.json')
        if (cleanup['errors'] or not cleanup['container_removed'] or not cleanup['cgroup_removed']
                or cleanup['tracing_used'] or cleanup['watchdog_intervened']):
            raise ValueError('resource preflight cleanup failed')
    if set(manifest['functional']) != set(c.ARMS) | {'A_cancel','D_cancel'}:
        raise ValueError('six functional compatibility checks required')
    for label, ref in manifest['functional'].items():
        d = c.resolve(prep, ref['path'])
        actual = verify_trial(session, d, manifest, functional=True)
        if c.digest(d/'seal.json') != ref['seal'] or actual != c.read(d/'derived.json'):
            raise ValueError('functional raw replay differs')
        if c.read(d/'initial.json')['resource_baseline'] != manifest['resource_baseline']:
            raise ValueError('functional resource contract differs')
        if label.endswith('cancel'):
            if not actual['summary']['failure_fraction'] or not actual['summary']['completed_computations'] or not actual['summary']['missing_handler_count']:
                raise ValueError('cancellation functional check did not exercise cancellation')
        elif actual['summary']['failure_fraction']:
            raise ValueError('functional success control failed')
    if current:
        if c.source_hashes() != manifest['sources']:
            raise ValueError('sources changed; prepare a new generation')
        if c.baseline() != manifest['baseline']:
            raise ValueError('kernel/boot/topology changed')
    return manifest


def verify_environment(session):
    receipt = c.read(session/'environment_seal.json')
    for name, sha in receipt['files_sha256'].items():
        if c.digest(c.resolve(session, name)) != sha:
            raise ValueError('sealed thermal/power baseline changed')
    env = c.read(session/'environment.json')
    thermal = c.read(session/'initial-settling.json')
    if env['policy'] != POLICY or thermal['policy'] != POLICY or not thermal['accepted']:
        raise ValueError('wrong/unaccepted initial thermal policy')
    samples = thermal['samples']
    elapsed = samples[-1]['elapsed_sec']
    i = 0
    while i+1 < len(samples) and samples[i+1]['elapsed_sec'] <= elapsed-POLICY['window_sec']:
        i += 1
    summary = window_summary(samples[i:])
    if (elapsed < POLICY['initial_idle_sec'] or not summary or not summary['stable']
            or env['baseline_c'] != {k: v['mean_c'] for k, v in summary['sensors'].items()}
            or any(s['power_settings'] != comparable_power(env['power_settings']) for s in samples)):
        raise ValueError('baseline does not match accepted idle evidence')
    return env


def verify_trial(session, directory, manifest, functional=False):
    complete = c.read(directory/'complete.json')
    config = c.read(directory/'config.json')
    if (complete.get('valid') is not True or complete.get('functional') is not functional
            or complete.get('performance_run') is not (not functional and config['block'] > 0)):
        raise ValueError('completion marker kind differs')
    result = analysis.replay(directory, functional)
    if result != c.read(directory/'derived.json'):
        raise ValueError('saved derivation differs from raw replay')
    initial, identity = c.read(directory/'initial.json'), c.read(directory/'identity.json')
    if initial['resource_baseline'] != manifest['resource_baseline']:
        raise ValueError('trial resource defaults differ')
    if any(identity[k] != manifest[k] for k in ('image', 'server_sha256', 'loadgen_sha256', 'gate_sha256')):
        raise ValueError('trial frozen-input identity differs')
    if not functional and c.read(directory/'environment.json') != c.read(session/'environment.json'):
        raise ValueError('trial environment baseline differs')
    return result


def verify_qualification(session, current=True):
    manifest = verify_preparation(session, current)
    verify_environment(session)
    qdir = session/'qualification'
    c.verify_seal(qdir)
    q = c.read(qdir/'result.json')
    if (not q['passed'] or q['preparation_seal'] != c.digest(session/'preparation/seal.json')
            or q['environment_seal'] != c.digest(session/'environment_seal.json')
            or (qdir/'capacity_failure.json').exists()):
        raise ValueError('qualification not accepted for this generation')
    if set(q['rehearsals']) != set(c.ARMS):
        raise ValueError('four complete full-duration rehearsals required')
    for config in c.rehearsals():
        ref = q['rehearsals'][config['arm']]
        d = c.resolve(session, ref['path'])
        if c.read(d/'config.json') != config or c.digest(d/'seal.json') != ref['seal']:
            raise ValueError('rehearsal identity changed')
        verify_trial(session, d, manifest)
        client = c.read(d/'loadgen.json')
        # Capacity checks do not select a favorable service/treatment result.
        if client['client_dropped'] or client['missed_arrivals'] or client['dispatch_lag_summary']['p99_ms'] > 2:
            raise ValueError('rehearsal client capacity failed')
    return q


def verify_completion(session):
    manifest = verify_preparation(session, current=False)
    verify_qualification(session, current=False)
    latest = c.read(session/'latest_analysis.json')
    out = c.resolve(session, latest['path'])
    c.verify_seal(out)
    if c.digest(out/'seal.json') != latest['seal']:
        raise ValueError('latest analysis identity changed')
    report = c.read(out/'report.json')
    if report['preparation_seal'] != c.digest(session/'preparation/seal.json'):
        raise ValueError('report preparation identity differs')
    if set(report['attempts']) != {v['trial'] for v in c.matrix()}:
        raise ValueError('sixteen complete accepted trials required')
    rows, requests, groups = [], [], []
    interruptions = []
    for config in c.matrix():
        parent = session/'trials'/config['trial']
        accepted = []
        for d in sorted(parent.glob('attempt-*')):
            c.verify_seal(d)
            if (d/'complete.json').exists():
                accepted.append(d)
            if (d/'interruption.json').exists():
                interruptions.append(dict(trial=config['trial'], block=config['block'],
                    path=str(d.relative_to(session)), **c.read(d/'interruption.json')))
        if len(accepted) != 1:
            raise ValueError('exactly one accepted attempt required for '+config['trial'])
        ref = report['attempts'][config['trial']]
        d = c.resolve(session, ref['path'])
        if d != accepted[0] or c.read(d/'config.json') != config or c.digest(d/'seal.json') != ref['seal']:
            raise ValueError('trial reference/configuration differs')
        derived = verify_trial(session, d, manifest)
        rows.append(derived['summary'])
        requests.extend(dict(trial=config['trial'], block=config['block'], arm=config['arm'], **r) for r in derived['requests'])
        groups.extend(derived['phase_groups'])
    interrupted = sorted({r['block'] for r in interruptions})
    expected = analysis.compare(rows, interrupted)
    if (any(report[k] != v for k, v in expected.items()) or report['trial_gaps']
            or report['interruptions'] != interruptions or report['interrupted_blocks'] != interrupted):
        raise ValueError('block effects/decision/interruption replay differs')
    for name, data in [('trials.csv', rows), ('requests.csv', requests), ('blocks.csv', expected['blocks']), ('phases.csv', groups)]:
        verify_export(out/name, data)
    return report


def verify_export(path, data):
    with path.open() as f:
        exported = list(csv.DictReader(f))
    if exported != [{k: str(v) if v is not None else '' for k, v in r.items()} for r in data]:
        raise ValueError('raw replay differs from export: '+path.name)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('directory', type=Path)
    args = p.parse_args()
    try:
        print(verify_completion(args.directory.resolve())['decision'])
    except Exception as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)
