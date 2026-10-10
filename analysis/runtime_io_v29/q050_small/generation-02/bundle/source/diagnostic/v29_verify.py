"""Independent V29 composition asset, raw-record, counter-bound and completion replay."""
import datetime
import sys
import v29_common as c
import v29_raw as raw
import v29_model as model
import v24r3_software as software
import v24r3_counter as native
import leftover_observer_review as observer
import v29_monitor_control as monitor_control
from verify_execution_delay import verify_environment


def verify_bundle(session,current=True):
    p=session/'bundle';c.verify_seal(p);m=c.read(p/'manifest.json');c.design()
    if m['schema']!=29 or m['matrix']!=c.matrix() or not m['software_checks_passed'] or m['runtime_qualified'] or m['performance_run']:
        raise ValueError('V29 bundle incomplete')
    if m['design_seal']!=c.digest(c.DESIGN/'seal.json'):raise ValueError('design seal changed')
    c.verify_seal(c.HISTORY/'bundle')
    history=c.read(c.HISTORY/'bundle/manifest.json')
    if m['historical_bundle_seal']!=c.digest(c.HISTORY/'bundle/seal.json'):raise ValueError('retained history changed')
    prior=c.resolve(c.HISTORY,c.read(c.HISTORY/'latest_analysis.json')['path']);c.verify_seal(prior)
    if c.digest(prior/'seal.json')!=m['historical_analysis_seal'] or m['historical_analysis_seal']!=c.design()['historical_analysis_seal']:
        raise ValueError('historical result reference changed')
    for key in ('image','server_sha256','gate_sha256','loadgen_sha256','resource_baseline','counter_sha256'):
        if m[key]!=history[key]:raise ValueError('retained resource/binary differs')
    c.verify_client_build();c.verify_seal(p/'client_build')
    if c.digest(p/'client_build/seal.json')!=m['client_build_seal']:raise ValueError('client build receipt changed')
    for filename,key in [('gate','gate_sha256'),('loadgen','loadgen_sha256'),('image.server','server_sha256'),('counter','counter_sha256')]:
        if c.digest(p/filename)!=m[key]:raise ValueError('bundled binary differs')
    for name,h in c.read(c.DESIGN/'seal.json')['files_sha256'].items():
        if c.digest(p/'scientific_design'/name)!=h:raise ValueError('design snapshot differs')
    for name,h in m['sources'].items():
        if c.digest(p/'source'/name)!=h or (current or name.endswith('.py')) and c.digest(c.ROOT/name)!=h:
            raise ValueError('source changed; new generation required')
    if current and c.source_hashes()!=m['sources']:raise ValueError('source set changed')
    expected={}
    for cfg in c.matrix()+[c.warmup_config(x) for x in c.matrix() if x['traffic_pattern']!='idle']+c.functional_configs():
        if cfg['traffic_pattern']=='idle':continue
        key=cfg['trial']+('_warmup' if cfg['duration_sec']==20 else '_measurement')
        expected[key]=cfg
    if set(expected)!=set(m['compiled_exports']):raise ValueError('compiled export inventory differs')
    for key,cfg in expected.items():
        path=p/'compiled_vectors'/(key+'.json');receipt=m['compiled_exports'][key]
        if c.digest(path)!=receipt['sha256'] or c.read(path)!=c.schedule(cfg) or receipt['count']!=len(c.schedule(cfg)):
            raise ValueError('compiled schedule receipt differs')
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
        if cfg['traffic_pattern']!='idle':
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
        raise ValueError('all six functional cases required')
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


def verify_predictions(session):
    out=session/'predictions';c.verify_seal(out);manifest=c.read(out/'manifest.json')
    if manifest['validation_outcomes_used'] is not False:raise ValueError('forecast leakage declared')
    if (manifest['preparation_seal']!=c.digest(session/'preparation/seal.json')
            or manifest['environment_seal']!=c.digest(session/'environment_seal.json')
            or manifest['design_seal']!=c.digest(c.DESIGN/'seal.json')):raise ValueError('forecast provenance differs')
    wanted={cfg['trial'] for cfg in c.calibration_configs()}
    if set(manifest['calibration_refs'])!=wanted:raise ValueError('forecast calibration reference inventory differs')
    values=[];prep=c.read(session/'preparation/manifest.json')
    for trial,ref in manifest['calibration_refs'].items():
        d=c.resolve(session,ref['path']);c.verify_seal(d)
        if c.digest(d/'seal.json')!=ref['seal'] or c.read(d/'config.json')['trial']!=trial:
            raise ValueError('forecast calibration reference changed')
        verify_trial(session,d,prep);values.append(c.read(d/'phase_accounting.json'))
        if c.read(d/'complete.json')['finished_monotonic_ns']>=manifest['frozen_monotonic_ns']:
            raise ValueError('calibration did not precede forecast seal')
    values.sort(key=lambda r:r['order']);cal=model.calibrate(values,c.design())
    if cal!=c.read(out/'calibration.json'):raise ValueError('fitted parameters differ from calibration replay')
    summary,per_id=model.forecast(cal,c.validation_configs())
    if summary!=c.read(out/'summary.json') or per_id!=c.read(out/'per_offer.json'):
        raise ValueError('frozen forecasts differ from independent simulation')
    review=session/'calibration_review';c.verify_seal(review)
    if c.digest(review/'seal.json')!=manifest['calibration_review_seal'] or c.read(review/'report.json')!=dict(calibration=cal,trial_refs=manifest['calibration_refs']):
        raise ValueError('calibration review changed')
    for cfg in c.validation_configs():
        for d in attempts(session,cfg):
            if c.read(d/'started.json')['monotonic_ns']<=manifest['frozen_monotonic_ns']:raise ValueError('validation attempt preceded freeze')
    return dict(calibration=cal,summary=summary)


def verify_completion(session):
    m=verify_preparation(session,current=False);verify_environment(session);verify_observer(session,current=False)
    values,refs=rows(session,m);cal=[r for r in values if r['role']!='validation'];val=[r for r in values if r['role']=='validation']
    calibration=model.calibrate(cal,c.design()) if len(cal)==len(c.calibration_configs()) else dict(usable=False,decision='calibration_incomplete')
    predictions=verify_predictions(session)['summary'] if (session/'predictions').exists() else {}
    report=model.report(val,calibration,predictions,c.design(),(session/'collection_receipt.json').exists() and len(val)==len(c.validation_configs()))
    if len(cal)!=len(c.calibration_configs()):report['decision']='comparison_incomplete'
    latest=c.read(session/'latest_analysis.json');out=c.resolve(session,latest['path']);c.verify_seal(out)
    if c.digest(out/'seal.json')!=latest['seal']:raise ValueError('analysis seal differs')
    saved=c.read(out/'report.json')
    if any(saved[key]!=value for key,value in dict(result=report,calibration=calibration,trial_refs=refs,trial_accounting=values,
        preparation_seal=c.digest(session/'preparation/seal.json'),prediction_seal=c.digest(session/'predictions/seal.json') if (session/'predictions/seal.json').exists() else None,
        collection_receipt_sha256=c.digest(session/'collection_receipt.json') if (session/'collection_receipt.json').exists() else None,
        measurement_lifetime_sha256=c.digest(session/'measurement_lifetime.json')).items()):raise ValueError('saved report/provenance differs from replay')
    failures=[str(p.relative_to(session)) for cfg in c.matrix() for p in attempts(session,cfg) if not (p/'complete.json').exists()]
    if saved['technical_failures']!=failures or len(failures)>2 or report['complete'] and len(failures)>1:raise ValueError('retry accounting differs')
    if (session/'collection_receipt.json').exists():
        receipt=c.read(session/'collection_receipt.json');lifetime=c.read(session/'measurement_lifetime.json')
        if (any(receipt[k]!=v for k,v in lifetime.items()) or receipt['completed_slots']!=len(values)
                or receipt['validation_launched']!=(session/'predictions/seal.json').exists()
                or abs(receipt['deadline_monotonic']-receipt['started_monotonic']-c.design()['measurement_bound_sec'])>1e-6
                or receipt['boot']!=m['baseline']['boot_id'] or receipt['collection_finished_monotonic']>receipt['deadline_monotonic']):raise ValueError('collection bound/receipt differs')
        for cfg in c.matrix():
            for d in attempts(session,cfg):
                start=c.read(d/'started.json')['monotonic_ns']
                if start<receipt['started_monotonic']*1e9 or start>receipt['collection_finished_monotonic']*1e9:raise ValueError('attempt outside collection bound')
                if (d/'complete.json').exists() and c.read(d/'complete.json')['finished_monotonic_ns']>receipt['collection_finished_monotonic']*1e9:raise ValueError('completion outside collection bound')
        if not calibration.get('usable') and val:raise ValueError('validation followed failed calibration')
        if calibration.get('usable') and not report['complete']:raise ValueError('collection receipt missing validation trials')
    elif report['complete']:raise ValueError('complete comparison lacks receipt')
    return report
