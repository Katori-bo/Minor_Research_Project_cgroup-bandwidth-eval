"""Independent V27 composition asset, raw-record, counter-bound and completion replay."""
import datetime
import sys
import v27_common as c
import v27_raw as raw
import v27_model as model
import v24r3_software as software
import v24r3_counter as native
import leftover_observer_review as observer
from verify_execution_delay import verify_environment


def verify_software_receipt():
    return software.verify_receipt(c.REPAIR,c)


def verify_bundle(session,current=True):
    verify_software_receipt()
    client=c.verify_client_build()
    p=session/'bundle';c.verify_seal(p);m=c.read(p/'manifest.json')
    if (m['schema']!=1 or m['matrix']!=c.matrix() or not m['software_checks_passed']
            or m['runtime_qualified'] or m['performance_run']):
        raise ValueError('offline bundle incomplete')
    if m['design_seal']!=c.digest(c.DESIGN/'seal.json'):
        raise ValueError('design seal differs')
    build=software.verify_build(c)
    if (m.get('counter_sha256')!=build['binary_sha256'] or m.get('native_build_seal')!=c.digest(c.BUILD/'seal.json')
            or c.digest(p/'counter')!=m['counter_sha256']):raise ValueError('bundled native collector differs')
    c.verify_seal(p/'native_build')
    if c.digest(p/'native_build/seal.json')!=m['native_build_seal']:raise ValueError('native build receipt differs')
    old=c.read(c.ORIGINAL/'manifest.json')
    for key in ('image','server_sha256','gate_sha256','resource_baseline'):
        if m[key]!=old[key]:raise ValueError('retained asset/resource identity changed')
    if m['original_preparation_seal']!=c.digest(c.ORIGINAL/'seal.json'):
        raise ValueError('original preparation seal changed')
    if (m.get('sampler_revision')!='v24r3-native'
            or m.get('software_receipt_seal')!=c.digest(c.REPAIR/'seal.json')
            or m.get('previous_bundle_seal')!=c.digest(c.PREVIOUS/'bundle/seal.json')):
        raise ValueError('sampler repair provenance differs')
    if (m.get('client_build_seal')!=c.digest(c.CLIENT_BUILD/'seal.json')
            or m['loadgen_sha256']!=client['binary_sha256']):raise ValueError('new client build identity differs')
    c.verify_seal(p/'client_build')
    if c.digest(p/'client_build/seal.json')!=m['client_build_seal']:raise ValueError('bundled client build differs')
    prerequisite=c.read(c.PREVIOUS/'latest_analysis.json')
    prior=c.resolve(c.PREVIOUS,prerequisite['path']);c.verify_seal(prior)
    if (c.digest(prior/'seal.json')!=c.design()['prerequisite_analysis_seal']
            or c.read(prior/'report.json')['result']['decision']!='both_low_rates_qualified'):
        raise ValueError('V26 qualified prerequisite changed')
    # The completed V26 generation and all its inherited sources remain readable.
    c.verify_seal(c.PREVIOUS/'bundle')
    for name,h in c.read(c.PREVIOUS/'bundle/manifest.json')['sources'].items():
        if c.digest(c.ROOT/name)!=h:raise ValueError('retained V26 source changed')
    for filename,key in [('gate','gate_sha256'),('loadgen','loadgen_sha256'),('image.server','server_sha256')]:
        if c.digest(p/filename)!=m[key]:raise ValueError('bundled binary changed')
    for name,h in c.read(c.DESIGN/'seal.json')['files_sha256'].items():
        if c.digest(p/'scientific_design'/name)!=h:raise ValueError('design snapshot changed')
    for name,h in m['sources'].items():
        if c.digest(p/'source'/name)!=h:raise ValueError('frozen source changed')
        if (current or name.endswith('.py')) and c.digest(c.ROOT/name)!=h:
            raise ValueError('loaded source differs; use a new generation')
    copied=p/'software_check'
    c.verify_seal(copied)
    if c.digest(copied/'seal.json')!=m['software_receipt_seal']:
        raise ValueError('bundled software receipt differs')
    if current and c.source_hashes()!=m['sources']:raise ValueError('source set differs')
    return m


def attempts(session,cfg):
    return sorted((session/'slots'/cfg['trial']).glob('attempt-*'))


def accepted(session,cfg):
    valid=[]
    for p in attempts(session,cfg):
        c.verify_seal(p)
        if (p/'complete.json').exists():
            if c.read(p/'complete.json').get('valid') is not True:raise ValueError('invalid completion marker')
            valid.append(p)
    if len(valid)>1:raise ValueError('accepted replacement/duplication prohibited')
    return valid[0] if valid else None


def counter_input(session,directory,cfg):
    path=directory/'counter.json'
    if not cfg['counter_probe']:
        if any((directory/n).exists() for n in ('counter.json','counter.raw.json','counter.ready.json','counter_readiness.json','counter_process.json','counter_argv.json')):
            raise ValueError('counter present in off treatment')
        return None
    probe=c.read(path);initial=c.read(directory/'initial.json');expected=initial['cgroup']+'/cpu.stat'
    argv=[str(session/'preparation/counter'),'--path',expected,'--output',str(directory/'counter.raw.json')]
    decoded=native.decode(c.read(directory/'counter.raw.json'))
    decoded['raw_sha256']=c.digest(directory/'counter.raw.json')
    if decoded!=probe:raise ValueError('saved native decoding differs')
    if c.read(directory/'counter_argv.json')!=argv:raise ValueError('counter command differs')
    model.validate_samples(probe,expected)
    stop=c.read(directory/'observations.json')['measurement_stop']['after_ns']
    if probe['finished_ns']<stop or probe['finished_ns']-probe['started_ns']>110_100_000_000:
        raise ValueError('native capture does not cover full drain within its110-second limit')
    if c.read(directory/'counter.ready.json')!=probe['samples'][0]:raise ValueError('counter readiness differs')
    readiness=c.read(directory/'counter_readiness.json')
    if (readiness['token']!='READY' or not probe['samples'][0]['after_ns']<=readiness['received_monotonic_ns']<=probe['finished_ns']):
        raise ValueError('native readiness receipt differs')
    identity=c.read(directory/'counter_process.json')
    if probe['pid']!=identity['pid'] or probe['uid']!=identity['uid']:raise ValueError('native process identity differs')
    if identity['uid']!=c.read(directory/'ownership.json')['owner']['uid']:
        raise ValueError('counter user differs from normal-user owner')
    return probe


def verify_trial(session,directory,manifest,functional=False):
    c.verify_seal(directory);cfg=c.read(directory/'config.json');c.validate_config(cfg,functional)
    complete=c.read(directory/'complete.json')
    if complete.get('valid') is not True or complete.get('functional') is not functional:
        raise ValueError('completion kind differs')
    derived=raw.replay(directory,functional)
    if derived!=c.read(directory/'derived.json'):raise ValueError('saved derivation differs from raw replay')
    identity=c.read(directory/'identity.json')
    if any(identity[k]!=manifest[k] for k in ('image','server_sha256','loadgen_sha256','gate_sha256')):
        raise ValueError('trial asset identity differs')
    if c.read(directory/'initial.json')['resource_baseline']!=manifest['resource_baseline']:
        raise ValueError('resource baseline differs')
    counter_input(session,directory,cfg)
    if not functional:
        for name in ('loadgen','warmup'):c.technical_client(c.read(directory/(name+'.json')))
        if c.read(directory/'environment.json')!=c.read(session/'environment.json'):
            raise ValueError('trial environment differs')
        expected=model.trial(derived,c.read(directory/'server_metrics.json'),
            c.read(directory/'host_server_anchors.json'),counter_input(session,directory,cfg),cfg,c.design(),
            c.read(directory/'initial.json')['cgroup']+'/cpu.stat')
        if expected!=c.read(directory/'phase_accounting.json'):
            raise ValueError('saved phase accounting differs from independent replay')
    return derived


def verify_preparation(session,current=True):
    bundle=verify_bundle(session,current);prep=session/'preparation';c.verify_seal(prep);m=c.read(prep/'manifest.json')
    if c.digest(prep/'counter')!=bundle['counter_sha256'] or m['counter_sha256']!=bundle['counter_sha256']:raise ValueError('runtime native collector differs')
    if (m['bundle_seal']!=c.digest(session/'bundle/seal.json') or m['matrix']!=c.matrix()
            or not m['functional_passed'] or m['performance_run'] or (prep/'preparation_failure.json').exists()):
        raise ValueError('runtime preparation incomplete')
    for key in ('image','server_sha256','loadgen_sha256','gate_sha256','resource_baseline','sources','design_seal'):
        if m[key]!=bundle[key]:raise ValueError('runtime preparation differs from bundle')
    if current and c.baseline()!=m['baseline']:raise ValueError('boot/kernel/topology changed')
    for filename,key in [('gate','gate_sha256'),('loadgen','loadgen_sha256'),('image.server','server_sha256')]:
        if c.digest(prep/filename)!=m[key]:raise ValueError('runtime binary differs')
    if c.read(prep/'image.json')['Id']!=m['image']:raise ValueError('actual image differs')
    d=prep/'resource_preflight';initial=c.read(d/'initial.json');container=c.read(d/'container.json')['inspect']
    c.validate_resources(initial['initial_limits'],container['HostConfig'],m['resource_baseline'],c.functional_configs()[0])
    cleanup=c.read(d/'cleanup.json');observed=c.read(d/'observed.json')
    if (cleanup['errors'] or not cleanup['container_removed'] or not cleanup['cgroup_removed']
            or cleanup['watchdog_intervened'] or observed['gate_released'] or observed['performance_run']
            or observed['limits']!=initial['initial_limits'] or container['Image']!=m['image']
            or c.digest(d/'container.server')!=m['server_sha256']):
        raise ValueError('unreleased resource preflight failed')
    if set(m['functional'])!={cfg['trial'] for cfg in c.functional_configs()}:
        raise ValueError('all four functional cases required')
    for cfg in c.functional_configs():
        ref=m['functional'][cfg['trial']];d=c.resolve(prep,ref['path'])
        if c.digest(d/'seal.json')!=ref['seal']:raise ValueError('functional reference changed')
        sm=verify_trial(session,d,m,True)['summary']
        if cfg['timeout_sec']<1:
            if not sm['failure_fraction'] or not sm['completed_computations'] or not sm['missing_handler_count']:
                raise ValueError('functional cancellation not exercised')
        elif sm['failure_fraction']:raise ValueError('functional success failed')
    return m


def verify_observer(session,current=True):
    directory=session/'observer_review';c.verify_seal(directory);receipt=c.read(directory/'receipt.json')
    reviewed=observer.review(receipt['audit_path']);audit=c.read(directory/'audit.json')
    baseline=c.read(session/'preparation/manifest.json')
    if (reviewed!=c.read(directory/'review.json') or c.digest(directory/'audit.json')!=reviewed['audit_sha256']
            or reviewed['boot_id'].strip()!=baseline['baseline']['boot_id'] or audit['kernel']!=baseline['baseline']['kernel']
            or datetime.datetime.fromisoformat(audit['at']).timestamp()<baseline['created']
            or audit['configuration_changed'] or audit['observation_started']
            or audit['tracefs']['root_controls_before']!=audit['tracefs']['root_controls_after']):
        raise ValueError('observer review provenance/boot differs')
    if current and reviewed['boot_id'].strip()!=c.baseline()['boot_id']:raise ValueError('observer review from another boot')
    return reviewed


def rows(session,manifest):
    result=[];refs={}
    for cfg in c.matrix():
        d=accepted(session,cfg)
        if d is None:continue
        verify_trial(session,d,manifest)
        result.append(c.read(d/'phase_accounting.json'))
        refs[cfg['trial']]=dict(path=str(d.relative_to(session)),seal=c.digest(d/'seal.json'))
    return result,refs


def verify_completion(session):
    m=verify_preparation(session,current=False);verify_environment(session);verify_observer(session,current=False)
    values,refs=rows(session,m)
    report=model.report(values,c.design(),collection_complete=(session/'collection_receipt.json').exists())
    latest=c.read(session/'latest_analysis.json');out=c.resolve(session,latest['path']);c.verify_seal(out)
    if c.digest(out/'seal.json')!=latest['seal']:raise ValueError('analysis seal differs')
    saved=c.read(out/'report.json')
    if saved['result']!=report or saved['trial_refs']!=refs or saved.get('trial_accounting')!=values:
        raise ValueError('report differs from raw replay')
    if saved['preparation_seal']!=c.digest(session/'preparation/seal.json'):raise ValueError('report preparation identity differs')
    receipt_hash=c.digest(session/'collection_receipt.json') if (session/'collection_receipt.json').exists() else None
    if (saved['collection_receipt_sha256']!=receipt_hash
            or saved['measurement_lifetime_sha256']!=c.digest(session/'measurement_lifetime.json')):
        raise ValueError('report collection-bound provenance differs')
    failures=[str(p.relative_to(session)) for cfg in c.matrix() for p in attempts(session,cfg) if not (p/'complete.json').exists()]
    if (saved['technical_failures']!=failures or len(failures)>2
            or (report['complete'] and len(failures)>1)):
        raise ValueError('technical retry accounting differs')
    if (session/'collection_receipt.json').exists():
        receipt=c.read(session/'collection_receipt.json')
        lifetime=c.read(session/'measurement_lifetime.json')
        starts=[c.read(c.resolve(session,ref['path'])/'started.json')['monotonic_ns'] for ref in refs.values()]
        ends=[c.read(c.resolve(session,ref['path'])/'complete.json')['finished_monotonic_ns'] for ref in refs.values()]
        if (not report['complete'] or any(receipt[k]!=v for k,v in lifetime.items()) or receipt['completed_slots']!=len(c.matrix())
                or abs(receipt['deadline_monotonic']-receipt['started_monotonic']-c.design()['measurement_bound_sec'])>1e-6
                or receipt['boot']!=m['baseline']['boot_id']
                or receipt['collection_finished_monotonic']>receipt['deadline_monotonic']
                or any(t<receipt['started_monotonic']*1e9 for t in starts)
                or any(t>receipt['collection_finished_monotonic']*1e9 for t in ends)):
            raise ValueError('collection exceeded bound')
    elif report['complete']:raise ValueError('complete report lacks bounded collection receipt')
    return report
