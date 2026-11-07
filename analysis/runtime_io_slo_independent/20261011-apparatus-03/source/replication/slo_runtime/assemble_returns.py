#!/usr/bin/env python3
"""Read-only assembly of all four closed allocations; no Docker or host probes."""
import argparse
from fractions import Fraction
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/p) for p in ('runtime','slo')]
import common as r
import collectors as a
import report as reporting
import evaluation as e
import cost as acquisition_cost


def verify_return(directory,package_root):
    directory=Path(directory);seal=r.read(directory/'return_seal.json')
    r.require(seal['package_seal_sha256']==r.sha(Path(package_root)/'runtime_seal.json'),'return source package differs')
    actual={str(p.relative_to(directory)) for p in directory.rglob('*') if p.is_file() and p!=directory/'return_seal.json'}
    r.require(actual==set(seal['files_sha256']),'returned evidence inventory differs')
    for name,h in seal['files_sha256'].items():
        path=directory/name
        r.require(not path.is_symlink() and r.sha(path)==h,'returned evidence changed: '+name)
    return seal


def assemble(roots):
    r.require(len(roots)==2,'the two frozen host packages are required')
    hosts={};plan=None;records={};closed=[];cost=[];bound=sum_elapsed=0
    for root in map(Path,roots):
        package=r.verify_package(root);host=package['host']['id']
        r.require(host not in hosts,'duplicate returned host');hosts[host]=root
        current=r.read(root/'scientific/plan.json')
        if plan is None:plan=current
        r.require(current==plan,'host packages use different scientific plans')
        for app in package['host']['order']:
            directory=root/'runs'/host/app;seal=verify_return(directory,root)
            alloc=r.read(directory/'allocation.json');finish=r.read(directory/'supervisor_finished.json')
            cid=next(x['id'] for x in plan['campaigns'] if x['host']==host and x['application']==app)
            r.require(seal['planned_campaign_id']==cid and alloc['campaign']['id']==cid and finish['allocation_closed'],
                      'foreign or unclosed allocation')
            r.require(alloc['cap_sec']==(12600 if app=='Go' else 2700),'campaign cap changed')
            closed.append(dict(campaign_id=cid,summary=finish))
            bound+=alloc['cap_sec'];sum_elapsed+=finish['elapsed_sec'];rows={}
            # Numerical/receipt replay is independent of live host and paths.
            # Full retained raw/resource replay occurred in the sealed worker;
            # this assembler does not relabel its complete/adverse classification.
            if (directory/'campaign_report.json').exists():
                saved=r.read(directory/'campaign_report.json')
                for row in saved['windows']:
                    if row['campaign_id']!=cid or row['status']=='unavailable':continue
                    cfg=row['config'];key=row['window_id'];case=directory/row['case']
                    raw_name='loadgen.json' if app=='Go' else 'measurement.json'
                    def values(raw,warmup=False):
                        if app=='Go':
                            configs=r.read(root/'scientific/go/design.json')
                            expected=next(x for x in configs['validation_configs'] if x['trial']==cfg['trial'])
                            r.require(cfg==expected,'returned Go target configuration differs')
                            suffix='_warmup' if warmup else '_measurement'
                            vector=r.read(root/'scientific/go/schedules'/(key+suffix+'.json'))
                            r.require(raw['total_scheduled']==len(vector),'returned Go offer count differs')
                            found={x['ID']:x for x in raw['requests']}
                            r.require(len(found)==len(raw['requests']) and all(type(i)is int and 0<=i<len(vector) for i in found),
                                      'returned Go IDs differ')
                            r.require(len(vector)-len(found)==raw['client_dropped'],'returned Go drop accounting differs')
                            r.require(all(x['ScheduledOffsetNs']==vector[i] for i,x in found.items()),'returned Go schedule differs')
                            return [found[i]['EndToEndLatencyNs'] if i in found and not found[i]['Error'] and found[i]['StatusCode']==200
                                    else None for i in range(len(vector))]
                        # Retained complete-body arithmetic without live imports.
                        count=cfg['warmup_count'] if warmup else cfg['count'];prefix='warmup' if warmup else 'measurement'
                        r.require(raw['Schema']=='nginx-client-v1' and raw['Count']==count and raw['IntervalNs']==cfg['interval_ns'] and
                                  len(raw['Rows'])==count,'returned NGINX schedule differs')
                        result=[]
                        for i,x in enumerate(raw['Rows']):
                            r.require(x['ID']==f'{prefix}-{i}' and x['ScheduledNs']==i*cfg['interval_ns'],'returned NGINX offer differs')
                            success=(not x['Error'] and not x['DecodeError'] and x['Status']==200 and x['EchoID']==x['ID'] and
                                x['ContentEncoding']=='gzip' and x['ContentType']=='application/x-ndjson' and
                                x['DecodedBytes']==1048576 and x['DecodedSHA256']==plan['NGINX']['input_sha256'] and 0<x['BodyBytes']<=2097152)
                            r.require(not (not success and (x['DecodeError'] or x['Status']>0 and not x['Error'])),'returned NGINX integrity differs')
                            result.append(x['BodyDoneNs']-x['ScheduledNs'] if success else None)
                        return result
                    reader=type('Reader',(),dict(application=app,values=lambda self,raw,config,warmup=False:values(raw,warmup)))()
                    replay=a.replay_window(directory/'decisions',reader,cfg,case,r.sha(root/'scientific/plan.json'),cid,
                        r.read(directory/'lifetime.json')['boot_id'])
                    r.require(replay==row['cells'],'returned decision replay differs')
                    rows[key]={k:v for k,v in row.items() if k not in ('campaign_id','window_id')}
            records[cid]=rows
            cost.append(dict(campaign_id=cid,elapsed_sec=finish['elapsed_sec'],
                acquisition=r.read(directory/'acquisition_cost.json') if (directory/'acquisition_cost.json').exists() else None,
                preparation=r.read(directory/'preparation_cost.json') if (directory/'preparation_cost.json').exists() else None,
                independently_parsed_acquisitions=acquisition_cost.acquired(directory),
                preparation_raw_snapshot_is_subset_not_additive=True,
                raw_outcomes_retained=True,partial_cost_is_not_zero=True))
    r.require(set(hosts)=={'host01','host02'} and bound==30600 and len(closed)==4,'fixed study allocation inventory differs')
    result=reporting.report(plan,records)
    available=sum(row['status']=='primary_domain' and next(cell for cell in row['cells'] if cell['label']=='q/39/40')['deadline_ns'] is not None
                  for row in result['windows'] if row['status']!='unavailable')
    primary=len(result['primary_event_windows'])
    verdict=('independent_hardware_recurrence' if result['independent_hardware_event_observed'] else
             'fresh_same_host_recurrence_only' if primary else 'not_reproduced_in_available_windows' if available else 'unavailable')
    result.update(study_closed=True,closed_allocations=closed,acquisition_cost=cost,
        allocated_cap_sec=bound,observed_campaign_elapsed_sec=sum_elapsed,
        all_campaigns_within_hard_cap=all(x['summary']['within_hard_cap'] for x in closed),
        primary_available_windows=available,primary_verdict=verdict,population_guarantee=False)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--host-package',type=Path,action='append',required=True)
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();r.write(args.output,assemble(args.host_package))
