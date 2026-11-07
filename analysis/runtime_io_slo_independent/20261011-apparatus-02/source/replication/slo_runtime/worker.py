#!/usr/bin/env python3
"""Fresh single-attempt qualification, calibration, barrier and all-slot ledger."""
import argparse
import json
import os
from pathlib import Path
import signal
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/p) for p in ('runtime','diagnostic','scripts','analysis','slo')]
import common as r
import collectors as a
import report as reporting
import cost


class Stage:
    def __init__(self,directory,name,planned_offers=0,planned_warmups=0):
        self.directory,self.name=Path(directory),name
        self.planned_offers,self.planned_warmups=planned_offers,planned_warmups
    def __enter__(self):
        self.started=time.monotonic_ns()
        r.write(self.directory/'ledger'/(self.name+'_start.json'),dict(started_ns=self.started,
            planned_measurement_offers=self.planned_offers,planned_warmup_offers=self.planned_warmups))
        return self
    def __exit__(self,kind,exc,tb):
        r.write(self.directory/'ledger'/(self.name+'_end.json'),dict(finished_ns=time.monotonic_ns(),
            elapsed_sec=(time.monotonic_ns()-self.started)/1e9,error=None if exc is None else str(exc)))


class TimedProcess:
    def __init__(self,process,directory,phase,before_ns,returned_ns):
        self.process,self.directory,self.phase=process,Path(directory),phase
        self.recorded=False
        r.write(self.directory/(phase+'_supervisor_spawn.json'),dict(
            before_popen_ns=before_ns,popen_returned_ns=returned_ns,pid=process.pid,
            timestamps_are_supervisor_boundaries=True,absolute_http_completion_not_observed=True))
    def __getattr__(self,name):return getattr(self.process,name)
    def poll(self):
        result=self.process.poll()
        if result is not None and not self.recorded:
            self.recorded=True
            r.write(self.directory/(self.phase+'_supervisor_exit.json'),dict(
                exit_observed_ns=time.monotonic_ns(),returncode=result,
                timestamp_is_parent_observation=True))
        return result


class TimedHook(a.ForecastHook):
    def spawn(self,directory,cfg,phase,popen,*args,**kwargs):
        def timed(*arguments,**options):
            before=time.monotonic_ns()
            child=popen(*arguments,**options)
            try:return TimedProcess(child,directory,phase,before,time.monotonic_ns())
            except BaseException:self.stop_child(child);raise
        return super().spawn(directory,cfg,phase,timed,*args,**kwargs)


def wait_for_registration(directory,phase):
    path=directory/'workers'/(phase+'.json');until=time.monotonic()+10
    while not path.exists():
        r.require(time.monotonic()<until,'supervisor registration unavailable; no traffic released')
        time.sleep(.02)
    r.require(r.read(path)==r.identity(os.getpid()),'worker is not the registered supervisor child')


def run(directory,phase):
    directory=Path(directory);wait_for_registration(directory,phase)
    package=r.verify_package(ROOT);plan=r.read(ROOT/'scientific/plan.json')
    alloc=r.read(directory/'allocation.json');life=r.read(directory/'lifetime.json')
    r.require(life['boot_id']==r.identity(os.getpid())['boot_id'],'supervisor boot differs')
    r.require(alloc['host']==package['host'] and directory==ROOT/'runs'/package['host']['id']/alloc['application'],
              'foreign campaign directory/allocation')
    def interrupted(signum,frame):raise InterruptedError('owned worker interrupted; preserve all records')
    for sig in (signal.SIGTERM,signal.SIGINT):signal.signal(sig,interrupted)
    preflight=r.check_host(ROOT)
    r.write(directory/('preflight_'+phase+'.json'),preflight)
    os.sched_setaffinity(0,set(package['host']['control_cpus']))
    if alloc['application']=='Go':from go_backend import Backend
    else:from nginx_backend import Backend
    backend=Backend(ROOT,directory)
    if phase=='prepare':
        try:
            with Stage(directory,'runtime_preparation'):backend.prepare()
        finally:
            r.write(directory/'preparation_cost.json',dict(raw_acquisitions=cost.acquired(directory),
                control=cost.control_calls(),partial_is_not_zero=True))
        return
    barrier=a.DurableBarrier(directory/'decisions',r.sha(ROOT/'scientific/plan.json'),
        alloc['campaign']['id'],life['boot_id'])
    budget=a.CampaignBudget(alloc['application'],life['started_ns'])
    def stop_child(child):
        import kernel_service_bridge
        kernel_service_bridge.stop_known(child)
    hook=TimedHook(barrier,backend.reader,backend.configs('validation'),budget,
        lambda:r.identity(os.getpid())['boot_id'],stop_child)
    records={};cohorts=[];failure=None;stopped_stage='begin'
    try:
        with Stage(directory,'environment_and_qualification_setup'):backend.begin(hook)
        for role in (['qualification','calibration'] if alloc['application']=='NGINX' else ['calibration']):
            for cfg in backend.configs(role):
                stopped_stage=role+'_'+str(cfg.get('trial',cfg.get('index')))
                budget.check(480 if alloc['application']=='Go' else 250)
                if alloc['application']=='Go':
                    count=len(backend.reader.ns['c'].schedule(cfg));warm=len(backend.reader.ns['c'].schedule(backend.reader.ns['c'].warmup_config(cfg)))
                else:count,warm=cfg['count'],cfg['warmup_count']
                with Stage(directory,stopped_stage,count,warm):value=backend.collect(cfg)
                if role=='calibration':cohorts.append(value)
                if alloc['application']=='NGINX':r.require(not value['domain_exits'],'NGINX '+role+' applicability exit; no replacement')
                else:r.require(not value['dispatch_exit'],'Go calibration dispatch exit; no replacement')
        stopped_stage='calibration_freeze'
        with Stage(directory,stopped_stage):
            reference=backend.reference(cohorts,plan)
            provenance=[]
            for row in cohorts:
                case=backend.case(row['config']);file=case/('loadgen.json' if alloc['application']=='Go' else 'measurement.json')
                provenance.append(dict(config=row['config'],raw_sha256=r.sha(file) if file.exists() else None,
                    case=str(case.relative_to(directory))))
            r.write(directory/'calibration_provenance.json',dict(cohorts=provenance,
                complete_all_calibration_slots=True,qualification_used_as_calibration=False,
                source_seal_sha256=r.sha(ROOT/'runtime_seal.json')))
            barrier.freeze_calibration(reference,plan['fixed_deadlines_ns'][alloc['application']],
                dict(acquisition_ledger='ledger',calibration_provenance_sha256=r.sha(directory/'calibration_provenance.json'),
                    selected_reference_offers=len(reference),full_acquisition_charged=True))
        for cfg in backend.configs('validation'):
            key=hook.key(cfg);stopped_stage=key
            count=len(backend.reader.ns['c'].schedule(cfg)) if alloc['application']=='Go' else cfg['count']
            warm=len(backend.reader.ns['c'].schedule(backend.reader.ns['c'].warmup_config(cfg))) if alloc['application']=='Go' else cfg['warmup_count']
            with Stage(directory,key,count,warm):value=backend.collect(cfg)
            case=backend.case(cfg)
            cells=a.replay_window(barrier.directory,backend.target_values(case,cfg),cfg,case,
                                 barrier.plan_hash,barrier.campaign_id,barrier.boot_id)
            records[key]=dict(status='applicability_exit' if value['domain_exits'] else 'primary_domain',
                config=cfg,cells=cells,domain_exits=value['domain_exits'],case=str(case.relative_to(directory)))
            r.write(directory/'decisions'/(key+'_score.json'),records[key])
            r.require(not value['domain_exits'],'target applicability exit; complete adverse window retained, no replacement')
    except BaseException as exc:
        failure=str(exc)
        r.write(directory/'collection_failure.json',dict(stage=stopped_stage,error=failure))
        raise
    finally:
        cid=alloc['campaign']['id']
        r.write(directory/'campaign_report.json',reporting.report(plan,{cid:records}))
        # Counts are observed as recorded; partial/corrupt JSON is reported as
        # unavailable, never padded into a complete-window scientific outcome.
        r.write(directory/'acquisition_cost.json',dict(raw_acquisitions=cost.acquired(directory),
            control=cost.control_calls(),preparation_control_cost_file='preparation_cost.json',stopped_stage=stopped_stage,
            error=failure,stage_ledger='ledger',finished_ns=time.monotonic_ns(),
            selected_samples_do_not_replace_acquired_offers=True,missing_future_offers_imputed=False))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--directory',type=Path,required=True)
    p.add_argument('--phase',choices=['prepare','collect'],required=True);args=p.parse_args();run(args.directory,args.phase)
