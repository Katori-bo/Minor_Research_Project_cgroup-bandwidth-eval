"""Independent V23 raw replay, calibration-only prediction and completion verifier."""
import json
import time
import datetime

import v23_common as c
import v23_raw as raw
import v23_model as model
import leftover_observer_review as observer
from verify_execution_delay import verify_environment


def attempts(session, cfg):
    return sorted((session/'slots'/cfg['trial']).glob('attempt-*'))


def accepted(session, cfg):
    result=[]
    for p in attempts(session,cfg):
        c.verify_seal(p)
        if (p/'complete.json').exists():
            if c.read(p/'complete.json').get('valid') is not True:
                raise ValueError('invalid completion marker')
            result.append(p)
    if len(result)>1:raise ValueError('accepted trial replacement/duplication prohibited')
    return result[0] if result else None


def verify_trial(session, directory, manifest, functional=False):
    c.verify_seal(directory)
    cfg=c.read(directory/'config.json');c.validate_config(cfg,functional)
    complete=c.read(directory/'complete.json')
    if complete.get('valid') is not True or complete.get('functional') is not functional:
        raise ValueError('completion kind differs')
    derived=raw.replay(directory,functional)
    if derived!=c.read(directory/'derived.json'):raise ValueError('saved derivation differs from raw replay')
    identity=c.read(directory/'identity.json')
    if any(identity[k]!=manifest[k] for k in ('image','server_sha256','loadgen_sha256','gate_sha256')):
        raise ValueError('trial asset identity differs')
    if c.read(directory/'initial.json')['resource_baseline']!=manifest['resource_baseline']:
        raise ValueError('trial resource defaults differ')
    if not functional:
        for label in ('loadgen','warmup'):c.technical_client(c.read(directory/(label+'.json')))
        if c.read(directory/'environment.json')!=c.read(session/'environment.json'):
            raise ValueError('trial environment changed')
    if cfg['role']=='validation':
        authorization=c.read(directory/'validation_authorization.json')
        prediction=c.read(session/'predictions/manifest.json')
        if (authorization['prediction_seal']!=c.digest(session/'predictions/seal.json')
                or authorization['monotonic_ns']<prediction['sealed_before_validation_monotonic_ns']
                or c.read(directory/'started.json')['monotonic_ns']<authorization['monotonic_ns']):
            raise ValueError('validation lacks prior frozen prediction authorization')
    return derived


def verify_preparation(session, current=True):
    prep=session/'preparation';c.verify_seal(prep);m=c.read(prep/'manifest.json')
    if (m['schema']!=1 or m['matrix']!=c.matrix() or not m['tests_passed'] or not m['functional_passed']
            or m['performance_run'] or (prep/'preparation_failure.json').exists()):
        raise ValueError('V23 preparation incomplete/invalid')
    s=c.design();old=c.read(c.ORIGINAL/'manifest.json')
    for key in ('image','server_sha256','loadgen_sha256','gate_sha256','resource_baseline'):
        if m[key]!=old[key]:raise ValueError('retained V20 asset/resource identity changed')
    if m['original_preparation_seal']!=c.digest(c.ORIGINAL/'seal.json'):
        raise ValueError('original provenance seal changed')
    for filename,key in (('gate','gate_sha256'),('loadgen','loadgen_sha256'),('image.server','server_sha256')):
        if c.digest(prep/filename)!=m[key]:raise ValueError('retained binary changed')
    if m['design_seal']!=c.digest(c.DESIGN/'seal.json'):raise ValueError('design seal changed')
    for name,h in c.read(c.DESIGN/'seal.json')['files_sha256'].items():
        if c.digest(prep/'scientific_design'/name)!=h:raise ValueError('design snapshot differs')
    for name,h in m['sources'].items():
        if c.digest(prep/'source'/name)!=h:raise ValueError('frozen implementation changed')
        if (current or name.endswith('.py')) and c.digest(c.ROOT/name)!=h:
            raise ValueError('loaded implementation changed; use frozen sources or a new generation')
    if current and (c.baseline()!=m['baseline'] or c.source_hashes()!=m['sources']):
        raise ValueError('boot/kernel/topology/source set changed')
    if c.read(prep/'image.json')['Id']!=m['image']:raise ValueError('actual image differs')
    proof=c.read(prep/'publication_build.json')
    if (c.digest(prep/'publication_source.go')!=proof['prepared_sha256']['service/main.go']
            or proof['images']['service']!=m['image']):
        raise ValueError('retained publication source proof differs')
    d=prep/'resource_preflight';initial=c.read(d/'initial.json');container=c.read(d/'container.json')['inspect']
    c.validate_resources(initial['initial_limits'],container['HostConfig'],m['resource_baseline'],c.functional_configs()[0])
    cleanup=c.read(d/'cleanup.json')
    if cleanup['errors'] or not cleanup['container_removed'] or not cleanup['cgroup_removed'] or cleanup['watchdog_intervened']:
        raise ValueError('preflight cleanup unverified')
    if container['Image']!=m['image'] or c.digest(d/'container.server')!=m['server_sha256']:
        raise ValueError('preflight actual server differs')
    observed=c.read(d/'observed.json')
    if observed['gate_released'] or observed['performance_run'] or observed['limits']!=initial['initial_limits']:
        raise ValueError('unreleased resource preflight receipt differs')
    if set(m['functional'])!={cfg['trial'] for cfg in c.functional_configs()}:
        raise ValueError('all eight functional/cancellation cases required')
    for cfg in c.functional_configs():
        ref=m['functional'][cfg['trial']];directory=c.resolve(prep,ref['path'])
        if c.digest(directory/'seal.json')!=ref['seal']:raise ValueError('functional evidence seal changed')
        derived=verify_trial(session,directory,m,True)
        sm=derived['summary']
        if cfg['timeout_sec']<1:
            if not sm['failure_fraction'] or not sm['completed_computations'] or not sm['missing_handler_count']:
                raise ValueError('functional cancellation not exercised')
        elif sm['failure_fraction']:raise ValueError('functional success check failed')
    return m


def verify_observer(session, current=True):
    directory=session/'observer_review';c.verify_seal(directory)
    receipt=c.read(directory/'receipt.json')
    reviewed=observer.review(receipt['audit_path'])
    audit=c.read(directory/'audit.json');baseline=c.read(session/'preparation/manifest.json')
    if (reviewed!=c.read(directory/'review.json')
            or c.digest(directory/'audit.json')!=reviewed['audit_sha256']
            or reviewed['boot_id'].strip()!=baseline['baseline']['boot_id']
            or audit['kernel']!=baseline['baseline']['kernel']
            or datetime.datetime.fromisoformat(audit['at']).timestamp()<baseline['created']
            or audit['configuration_changed'] or audit['observation_started']
            or audit['tracefs']['root_controls_before']!=audit['tracefs']['root_controls_after']):
        raise ValueError('observer review identity/boot differs')
    if current and reviewed['boot_id'].strip()!=c.baseline()['boot_id']:
        raise ValueError('observer review is from another boot')
    return reviewed


def verify_qualification(session,current=True):
    m=verify_preparation(session,current);verify_environment(session)
    verify_observer(session,current)
    for cfg in c.matrix():
        if cfg['role']!='qualification':continue
        directory=accepted(session,cfg)
        if directory is None:raise ValueError('new-boot qualification incomplete')
        verify_trial(session,directory,m)
    return m


def calibration_inputs(session,manifest,size):
    derived=[];servers=[];refs={}
    for cfg in c.matrix():
        if cfg['role']!='calibration' or cfg['size']!=size:continue
        p=accepted(session,cfg)
        if p is None:raise ValueError('two independent calibration trials required for '+size)
        derived.append(verify_trial(session,p,manifest));servers.append(c.read(p/'server_metrics.json'))
        refs[cfg['trial']]=dict(path=str(p.relative_to(session)),seal=c.digest(p/'seal.json'))
    return derived,servers,refs


def make_forecast(session,manifest):
    sizes={};refs={};summary={'by_size':{}};requests={};design=c.design()
    for size in ('small','large'):
        derived,servers,selected=calibration_inputs(session,manifest,size)
        sizes[size]=model.calibration(derived,servers,design,size);refs.update(selected)
    cal=dict(passed=all(v['passed'] for v in sizes.values()),sizes=sizes,
             decision='adequate_stable' if all(v['passed'] for v in sizes.values()) else 'inadequate_or_unstable_calibration')
    if not cal['passed']:return cal,None,None,refs
    for size in sizes:
        patterns={a:c.read(c.DESIGN/(size+'_'+a+'_offsets_ns.json')) for a in ('A','B')}
        summary['by_size'][size],requests[size]=model.predictions(sizes[size],patterns,{a:design['patterns'][a]['period_sec'] for a in ('A','B')})
    return cal,summary,requests,refs


def verify_predictions(session,recompute=False,current=True):
    m=verify_qualification(session,current);p=session/'predictions';c.verify_seal(p)
    pm=c.read(p/'manifest.json')
    if (pm['preparation_seal']!=c.digest(session/'preparation/seal.json')
            or pm['environment_seal']!=c.digest(session/'environment_seal.json')
            or pm['design_seal']!=m['design_seal']
            or set(pm['calibration_refs'])!=set(c.design()['calibration']['trial_ids']) or not c.read(p/'calibration.json')['passed']):
        raise ValueError('prediction provenance/calibration-only gate failed')
    for name,ref in pm['calibration_refs'].items():
        directory=c.resolve(session,ref['path'])
        if c.read(directory/'config.json')['trial']!=name or c.digest(directory/'seal.json')!=ref['seal']:
            raise ValueError('prediction calibration identity changed')
    if recompute:
        cal,summary,requests,refs=make_forecast(session,m)
        if (cal!=c.read(p/'calibration.json') or summary!=c.read(p/'summary.json')
                or requests!=c.read(p/'per_id.json') or refs!=pm['calibration_refs']):
            raise ValueError('frozen forecasts differ from calibration-only recomputation')
    return c.read(p/'summary.json')


def validation_rows(session,manifest,prediction):
    result=[];refs={}
    for cfg in c.matrix():
        if cfg['role']!='validation':continue
        p=accepted(session,cfg)
        if p is None:continue
        derived=verify_trial(session,p,manifest)
        observed=model.trial_metrics(derived,c.read(p/'server_metrics.json'),cfg)
        estimates={name:model.evaluate(observed,prediction['by_size'][cfg['size']]['point'][name][cfg['arm']],cfg['arm']) for name in ('M_busy','M_cpu')}
        # Residuals use observed-only matching records; missing/rejected predictions are never zero delay.
        resid={}
        predicted=c.read(session/'predictions/per_id.json')[cfg['size']]['M_busy'][cfg['arm']]
        for key in ('worker_start','completion','e2e'):
            errors=[]
            for r,pr in zip(derived['requests'],predicted):
                if pr['rejected'] or not r['worker_observed']:continue
                if key=='e2e':
                    actual=r['e2e_ns']
                    if not r['success']:continue
                else:
                    actual=(r['completion_after_offered_lower_ns']+r['completion_after_offered_upper_ns'])/2
                    if key=='worker_start':actual-=r['processing_wall_ns']
                expected=(pr['start_sec']-r['scheduled_offset_ns']/1e9)*1e9 if key=='worker_start' else pr['latency_sec']*1e9
                errors.append((expected-actual)/1e6)
            resid[key]=dict(coverage=len(errors),residual_distribution_ms=raw.distribution(errors),
                           absolute_residual_distribution_ms=raw.distribution(abs(e) for e in errors))
        result.append(dict(trial=cfg['trial'],size=cfg['size'],arm=cfg['arm'],block=cfg['block'],observed=observed,models=estimates,stage_residuals=resid))
        refs[cfg['trial']]=dict(path=str(p.relative_to(session)),seal=c.digest(p/'seal.json'))
    return result,refs


def verify_completion(session):
    prediction=verify_predictions(session,recompute=True,current=False)
    m=verify_preparation(session,current=False)
    rows,refs=validation_rows(session,m,prediction);report=model.report(rows,prediction)
    latest=c.read(session/'latest_analysis.json');out=c.resolve(session,latest['path']);c.verify_seal(out)
    if c.digest(out/'seal.json')!=latest['seal']:raise ValueError('analysis seal changed')
    saved=c.read(out/'report.json')
    if saved['result']!=report or saved['validation_refs']!=refs:
        raise ValueError('report differs from independent raw replay')
    if saved['prediction_seal']!=c.digest(session/'predictions/seal.json'):
        raise ValueError('report prediction identity differs')
    return report
