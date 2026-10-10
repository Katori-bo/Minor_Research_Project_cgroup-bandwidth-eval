"""Offline stage and publication-bound review; never invokes Docker or benchmarks."""
import collections
import hashlib
import json
from pathlib import Path
import statistics as st
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'diagnostic'))
import worker_control_common as c
import verify_worker_control as verify


def publication_bounds(config, jobs, handlers, rows):
    # Sole worker: send(result_i) returns before start(job_i+1). This is a
    # source/program-order upper bound, never a directly observed send timestamp.
    if config['workers'] != 1:
        raise ValueError('publication inference requires exactly one worker')
    ordered = sorted(jobs, key=lambda j: j['worker_start_ns'])
    if any(a['completion_ns'] > b['worker_start_ns'] for a, b in zip(ordered, ordered[1:])):
        raise ValueError('overlapping single-worker computation intervals')
    hh = {h['id']: h for h in handlers}
    rr = {r['id']: r for r in rows}
    out = []
    for job, nxt in zip(ordered, ordered[1:]):
        handler, row = hh.get(job['id']), rr[job['id']]
        if handler is None or not row['success']:
            continue
        bound = nxt['worker_start_ns']
        if bound >= handler['resume_ns']:
            continue  # Bound is uninformative; never replace unknown delay by zero.
        out.append(dict(id=job['id'], next_job_id=nxt['id'],
            publication_upper_bound_server_ns=bound,
            available_to_resume_lower_bound_ns=handler['resume_ns']-bound,
            publication_before_500ms_certain=(row['completion_after_offered_upper_ns']
                +bound-job['completion_ns'] <= 500_000_000),
            deadline_class=row['deadline_class']))
    return out


def self_check():
    config={'workers':1}
    jobs=[dict(id=0,worker_start_ns=0,completion_ns=100),
          dict(id=1,worker_start_ns=200,completion_ns=300)]
    handler=[dict(id=0,resume_ns=400)]
    rows=[dict(id=0,success=True,completion_after_offered_upper_ns=499_999_850,
               deadline_class='computed_before_handler_resumed_after')]
    result=publication_bounds(config,jobs,handler,rows)
    assert result[0]['available_to_resume_lower_bound_ns']==200
    assert result[0]['publication_before_500ms_certain']
    rows[0]['completion_after_offered_upper_ns']=499_999_901
    assert not publication_bounds(config,jobs,handler,rows)[0]['publication_before_500ms_certain']
    assert not publication_bounds(config,jobs,[dict(id=0,resume_ns=200)],rows)
    assert not publication_bounds(config,jobs,[],rows)
    assert not publication_bounds(config,jobs[:1],handler,rows)
    for cfg, jj in [({'workers':4},jobs), (config,[dict(jobs[0],completion_ns=201),jobs[1]])]:
        try:
            publication_bounds(cfg,jj,handler,rows)
        except ValueError:
            pass
        else:
            raise AssertionError('invalid inference accepted')


def main():
    self_check()
    session=c.PARENT/'generation-03'
    verified=verify.verify_completion(session)
    analysis=session/'analysis/1791186642269289872'
    assert c.read(analysis/'report.json')==verified
    build=ROOT/'analysis/runtime_io_v12_parallelism_build'
    source=build/'prepared/service/main.go'
    build_manifest=c.read(build/'build.json')
    assert c.digest(source)==build_manifest['prepared_sha256']['service/main.go']
    manifest=c.read(session/'preparation/manifest.json')
    assert build_manifest['images']['service']==manifest['image']
    text=source.read_text()
    assert text.count('j.reply <- answer')==1
    assert text.count('for j := range s.queue')==1
    assert 's.runJob(j, nil)' in text
    trials=[]; bounded=[]
    stage_fields=('scheduled_to_entry_upper_ns','queue_ns','processing_wall_ns',
                  'completion_to_resume_ns','resume_to_client_upper_ns','e2e_ns')
    for trial, ref in verified['attempts'].items():
        d=session/ref['path']; c.verify_seal(d)
        derived=c.read(d/'derived.json'); config=c.read(d/'config.json')
        raw=c.read(d/'server_metrics.json'); rows=derived['requests']
        assert len(rows)==6793 and all(r['success'] for r in rows)
        classes=collections.Counter(r['deadline_class'] for r in rows)
        item=dict(trial=trial,block=config['block'],arm=config['arm'],offered=len(rows),
            stage_mean_ms={k:st.mean(r[k] for r in rows)/1e6 for k in stage_fields},
            deadline_counts=dict(classes),
            phase_timely={p:st.mean(r['timely_500'] for r in rows if r['phase']==p) for p in ('low','high')})
        if config['workers']==1:
            assert raw['workers']==1 and raw['instrument'] and not raw['worker_yield']
            bound=publication_bounds(config,raw['events'],raw['handler_events'],rows)
            crosses=[b for b in bound if b['deadline_class']=='computed_before_handler_resumed_after']
            assert len(crosses)==classes['computed_before_handler_resumed_after']
            assert all(b['publication_before_500ms_certain'] for b in crosses)
            lower=[b['available_to_resume_lower_bound_ns']/1e6 for b in crosses]
            item['residual_crossings']=dict(n=len(crosses),publication_before_deadline_certain=len(crosses),
                post_publication_lower_bound_median_ms=st.median(lower),
                post_publication_lower_bound_p99_ms=sorted(lower)[__import__('math').ceil(.99*len(lower))-1])
            bounded.extend(dict(trial=trial,block=config['block'],**b) for b in bound)
        trials.append(item)
    arms={}
    for arm in c.ARMS:
        selected=[t for t in trials if t['arm']==arm]
        arms[arm]=dict(n_trials=len(selected),stage_mean_ms={k:st.mean(t['stage_mean_ms'][k] for t in selected) for k in stage_fields},
            deadline_counts=dict(sum((collections.Counter(t['deadline_counts']) for t in selected),collections.Counter())),
            phase_timely={p:st.mean(t['phase_timely'][p] for t in selected) for p in ('low','high')})
    cross_trials=[t['residual_crossings'] for t in trials if t['arm']=='one']
    result=dict(schema=1,analysis='exploratory offline V19 residual review',
        measurement_launched=False,v19_verified_decision=verified['decision'],
        trials=trials,arms=arms,
        one_worker_crossings=sum(t['n'] for t in cross_trials),
        one_worker_publication_before_deadline_certain=sum(t['publication_before_deadline_certain'] for t in cross_trials),
        block_median_post_publication_lower_bound_ms=st.median(t['post_publication_lower_bound_median_ms'] for t in cross_trials),
        source_proof='With exactly one worker, its buffered reply send returns before its next job starts. The next job start is an upper bound on previous publication, not an observed send or runnable-readiness timestamp.',
        limitations=['No inference of exact runnable readiness, CPU availability, runqueue residence or scheduler defect.',
            'Inferences apply only to the conserved single-worker sequence; never apply this bound to four-worker events.',
            'Uninformative next-start bounds and final jobs remain unknown, not zero.',
            'Stage upper bounds share clock uncertainty and must not be added as exact durations.',
            'Arm distributions do not identify individual requests causally recovered by the intervention.'],
        provenance=dict(v19_report_sha256=c.digest(analysis/'report.json'),
            preparation_seal_sha256=c.digest(session/'preparation/seal.json'),
            original_image=manifest['image'],original_server_sha256=manifest['server_sha256'],
            original_build_manifest_sha256=c.digest(build/'build.json'),
            original_prepared_main_sha256=c.digest(source)))
    out=Path(sys.argv[1]); out.mkdir(parents=True,exist_ok=False)
    c.save(out/'summary.json',result); c.save(out/'publication_bounds.json',bounded)
    (out/'analyze_residual.py').write_bytes(Path(__file__).read_bytes())
    (out/'original_prepared_main.go').write_bytes(source.read_bytes())
    c.seal(out); c.verify_seal(out)
    print(json.dumps({k:result[k] for k in ('one_worker_crossings','one_worker_publication_before_deadline_certain','block_median_post_publication_lower_bound_ms')},indent=2))
    print(out)


if __name__=='__main__':
    main()
