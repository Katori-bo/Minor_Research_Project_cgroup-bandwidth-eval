#!/usr/bin/env python3
"""Independent offline entry point: verify frozen seals and recompute from raw files."""
import argparse
from pathlib import Path
import sys

import kernel_observer_common as c
import kernel_observer_analysis as analysis


def verify_completion(session):
    # Deliberately does not import or trust the collection runner/completion flags.
    c.verify_seal(session/'preparation'); manifest=c.read(session/'preparation/manifest.json')
    if manifest['matrix']!=c.matrix() or manifest['workload']!=c.WORKLOAD: raise ValueError('frozen experiment differs')
    preflight=session/'preparation/resource_preflight'
    observed=c.read(preflight/'observed.json'); cleanup=c.read(preflight/'cleanup.json')
    if observed['baseline']!=manifest['resource_baseline'] or observed['gate_released']:
        raise ValueError('prepared resource-default observation differs')
    if cleanup['returncode'] or not cleanup['cgroup_removed']: raise ValueError('preparation cleanup unverified')
    for name,key in {'loadgen':'loadgen_sha256','gate':'gate_sha256','kernel_observer.bt':'collector_sha256',
                     'original.server':'server_sha256','image.server':'server_sha256'}.items():
        if c.digest(session/'preparation'/name)!=manifest[key]: raise ValueError('frozen executable/collector identity differs')
    for name,sha in manifest['sources'].items():
        if c.digest(session/'preparation/source'/name)!=sha: raise ValueError('source seal differs')
        if c.digest(c.ROOT/name)!=sha: raise ValueError('offline verifier requires frozen implementation sources')
    c.verify_seal(session/'qualification'); qualification=c.read(session/'qualification/result.json')
    if not qualification['passed'] or (session/'qualification/capacity_failure.json').exists() or qualification['preparation_seal']!=c.digest(session/'preparation/seal.json'):
        raise ValueError('preparation not qualified')
    if qualification['environment_sha256']!=c.digest(session/'environment.json'): raise ValueError('qualified environment baseline changed')
    for arm in ('off','on'):
        ref=qualification['rehearsals'][arm]; d=resolve_reference(session,ref['path'])
        if c.read(d/'initial.json')['resource_baseline']!=manifest['resource_baseline']:
            raise ValueError('rehearsal resource defaults differ from preparation')
        if c.digest(d/'seal.json')!=ref['seal'] or analysis.replay(d)!=c.read(d/'derived.json'):
            raise ValueError('rehearsal replay mismatch')
    latest=c.read(session/'latest_analysis.json'); out=resolve_reference(session,latest['path']); c.verify_seal(out)
    if c.digest(out/'seal.json')!=latest['seal']: raise ValueError('analysis seal changed')
    report=c.read(out/'report.json'); rows=[]; vectors={}; requests=[]
    if report['preparation_seal']!=c.digest(session/'preparation/seal.json'): raise ValueError('report preparation identity differs')
    if set(report['attempts'])!={v['trial'] for v in c.matrix()}: raise ValueError('twelve valid trials required')
    for config in c.matrix():
        ref=report['attempts'][config['trial']]; d=resolve_reference(session,ref['path'])
        if c.read(d/'config.json')!=config or c.digest(d/'seal.json')!=ref['seal']: raise ValueError('trial identity/seal mismatch')
        derived=analysis.replay(d)
        if derived!=c.read(d/'derived.json'): raise ValueError('trial raw replay mismatch')
        initial=c.read(d/'initial.json'); identity=c.read(d/'identity.json')
        if initial['resource_baseline']!=manifest['resource_baseline']: raise ValueError('resource defaults differ from preparation')
        if any(identity[k]!=manifest[k] for k in ('image','server_sha256','loadgen_sha256')):
            raise ValueError('trial differs from frozen inputs')
        if c.read(d/'environment.json')!=c.read(session/'environment.json'): raise ValueError('thermal/power baseline differs')
        rows.append(derived['summary']); vectors[config['trial']]=c.arrival_vector(c.read(d/'loadgen.json'))
        requests.extend(dict(trial=config['trial'],pair=config['pair'],arm=config['arm'],**r) for r in derived['requests'])
    for pair in range(1,7):
        if vectors[f'p{pair}_off']!=vectors[f'p{pair}_on']: raise ValueError('pair arrivals differ')
    expected=analysis.compare(rows)
    if any(report[k]!=v for k,v in expected.items()) or report['pair_gaps']:
        raise ValueError('practical-screen replay mismatch')
    if report['decision']=='incomplete_evidence': raise ValueError('finite metrics required')
    # Export contents must match raw recomputation, not merely their own hashes.
    import csv
    for name,data in (('trials.csv',rows),('requests.csv',requests),('pairs.csv',expected['pairs'])):
        with (out/name).open() as f: exported=list(csv.DictReader(f))
        if exported!=[{k:str(v) if v is not None else '' for k,v in r.items()} for r in data]:
            raise ValueError(name+' export differs from raw replay')
    return report


def resolve_reference(session,name):
    path=Path(name)
    if path.is_absolute() or '..' in path.parts: raise ValueError('unsafe evidence reference')
    result=(session/path).resolve()
    if session.resolve() not in result.parents: raise ValueError('evidence reference escapes session')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('directory',type=Path); args=p.parse_args()
    try: print(verify_completion(args.directory)['decision'])
    except Exception as e: print(str(e),file=sys.stderr); sys.exit(1)
