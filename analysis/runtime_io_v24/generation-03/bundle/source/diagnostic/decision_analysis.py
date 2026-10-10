#!/usr/bin/env python3
"""Join scheduler selections, first dispatches, and HTTP request identities."""
import argparse
import bisect
from collections import Counter, defaultdict
from pathlib import Path

import build_decision_probe as build
import run

SOURCES={i+1: name for i,name in enumerate(build.REASONS)}
SOURCES.update({14:'runnext',15:'regular_local',16:'sole_runnext'})


def clock_map(anchors):
    if [a['label'] for a in anchors] != ['start','stop']:
        raise ValueError('missing scheduler clock anchors')
    low=max(a['runtime_ns']-a['after_ns'] for a in anchors)
    high=min(a['runtime_ns']-a['before_ns'] for a in anchors)
    if low>high or high-low>1_000_000:
        raise ValueError('scheduler clock anchors disagree')
    return dict(offset_low_ns=low,offset_high_ns=high,uncertainty_ns=high-low)


def validate_capture(server, status, enabled):
    if server.get('scheduler_observation_enabled') is not enabled:
        raise ValueError('scheduler observer image mode mismatch')
    c=server.get('scheduler_capture',{})
    if (c.get('schema')!=1 or c.get('capacity')!=262144 or
        c.get('window')!='trace_start_to_drained_trace_stop' or
        type(c.get('stopped_ns')) is not int or c['stopped_ns']<=0):
        raise ValueError('scheduler capture schema/window invalid')
    reserved=c.get('reserved');events=c.get('events')
    if type(reserved) is not int or reserved<0 or not isinstance(events,list):
        raise ValueError('scheduler capture count schema invalid')
    if reserved>c['capacity'] or len(events)!=reserved:
        raise ValueError('scheduler capture overflow or unpublished slots')
    if not enabled and (reserved or events):
        raise ValueError('disabled scheduler observer recorded events')
    for seq,e in enumerate(events,1):
        fields=('sequence','time_ns','kind','g','actor_g','m','p','source','schedtick','request','start_pc')
        if any(type(e.get(f)) is not int for f in fields):
            raise ValueError('scheduler event numeric schema invalid')
        if (e['sequence']!=seq or e['kind'] not in range(1,6) or e['g']<=0 or
            not 0<e['time_ns']<=c['stopped_ns'] or e['p'] < -1 or
            not isinstance(e.get('function'),str) or
            any(type(e.get(f)) is not bool for f in ('pending','fair','inherit','network'))):
            raise ValueError('scheduler event schema/order invalid')
        if e['kind']==2 and (e['source'] not in SOURCES or e['source']==4):
            raise ValueError('selection source unresolved')
        if e['kind']!=2 and e['source']!=0:
            raise ValueError('nonselection event has a source')
    mapping=clock_map(status.get('scheduler_clock_anchors',[]))
    if enabled:
        for kind,ids in ((4,{e['request'] for e in status['io_events'] if e['kind']=='handler_entry'}),
                         (5,{e['id'] for e in server['events']})):
            markers=[e['request'] for e in events if e['kind']==kind]
            if len(markers)!=len(set(markers)) or set(markers)!=ids:
                raise ValueError('request/worker identity markers incomplete or duplicated')
        # Start/stop bracket the observed capture; include control/drain events explicitly.
        starts=[e['time_ns'] for e in events]
        if not starts:
            raise ValueError('enabled scheduler capture empty')
    return mapping


def classify(events):
    known={}
    for e in events:
        if e['kind'] in (4,5):
            role='http' if e['kind']==4 else 'worker'
            if e['g'] in known and known[e['g']]!=role:
                raise ValueError('goroutine has conflicting workload identities')
            known[e['g']]=role
    for e in events:
        if e['g'] not in known:
            f=e.get('function','')
            known[e['g']]=('http' if 'net/http.(*conn).serve' in f else
                'http_background_reader' if 'net/http.(*connReader).backgroundRead' in f or 'net/http.(*connReader).startBackgroundRead' in f else
                'listener' if 'net/http.(*Server).Serve' in f else
                'gc_worker' if 'runtime.gcBgMarkWorker' in f else
                'trace_background' if 'trace' in f else
                'runtime_background' if f.startswith('runtime.') else 'unclassified')
    return known


def join(events):
    # Reservation order is not a global causal clock; hooks are timed independently.
    rows=sorted(events,key=lambda e:(e['time_ns'],e['sequence']))
    selections={};pending={};dispatches=[];waits=[]
    by_g=defaultdict(list)
    for e in rows:
        by_g[e['g']].append(e)
        if e['kind']==1:
            if e['g'] in pending:
                raise ValueError('second wake before first dispatch')
            pending[e['g']]=e
        elif e['kind']==2:
            selections[e['m']]=e
        elif e['kind']==3:
            s=selections.pop(e['m'],None)
            if s is not None and (s['g']!=e['g'] or s['p']!=e['p']):
                s=None  # Locked-M transfer or other direct execute: no source claim.
            d=dict(**e,selection=s,selection_source=SOURCES[s['source']] if s else 'unmatched_direct_execute')
            dispatches.append(d)
            wake=pending.pop(e['g'],None)
            if wake:
                waits.append(dict(g=e['g'],wake=wake,dispatch=d,wait_ns=e['time_ns']-wake['time_ns']))
    return rows,by_g,dispatches,waits,list(pending.values())


def analyze_capture(server, status, client, enabled):
    clock=validate_capture(server,status,enabled)
    if not enabled:
        return dict(observation_enabled=False,clock_mapping=clock,examples=[],eligible_for_full=False)
    events=server['scheduler_capture']['events']
    roles=classify(events)
    rows,by_g,dispatches,waits,unresolved=join(events)
    executed={e['selection']['sequence']:e for e in dispatches if e['selection']}
    choices=[e for e in rows if e['kind']==2]
    choice_times=[e['time_ns'] for e in choices]
    outcomes={q['ID']:('timeout' if q['TimedOut'] else 'error' if q['Error'] else
        'success' if q['StatusCode']==200 else 'rejected' if q['StatusCode']==503 else 'other') for q in client['requests']}
    all_starts=[e['time_ns'] for e in dispatches]
    entries={e['request']:e for e in status['io_events'] if e['kind']=='handler_entry'}
    connections=defaultdict(list)
    for e in status['io_events']:
        connections[e['conn']].append(e)
    eligible=[];unlinked=0;cleanup_ambiguous=[]
    for wait in waits:
        wake,dispatch=wait['wake'],wait['dispatch']
        if not wake['network'] or roles.get(wait['g'])!='http': continue
        # Require the handler marker in this first running segment. A later
        # network read/reawakening must not be attributed to the earlier wake.
        future=[e for e in by_g[wait['g']] if (e['time_ns'],e['sequence'])>
                (dispatch['time_ns'],dispatch['sequence']) and e['kind'] in (1,3,4)]
        if not future or future[0]['kind']!=4:
            unlinked+=1;continue
        marker=future[0]
        if marker['request'] not in outcomes: raise ValueError('marker for unplanned request')
        begin,end=wake['time_ns'],dispatch['time_ns']
        entry=entries[marker['request']]
        previous=sorted((e for e in connections[entry['conn']] if e['kind']=='handler_entry'
                         and e['start_ns']<entry['start_ns']),key=lambda e:e['start_ns'])
        if previous:
            prev=previous[-1]
            done=[e for e in connections[entry['conn']] if e['kind'] in ('conn_idle','conn_closed')
                  and e['request_known'] and e['request']==prev['request']
                  and prev['start_ns']<=e['start_ns']<entry['start_ns']]
            if not done or min(e['start_ns'] for e in done)+clock['offset_high_ns']>=begin:
                cleanup_ambiguous.append(dict(g=wait['g'],request_id=marker['request'],wait_ns=wait['wait_ns']))
                continue
        a,b=bisect.bisect_left(all_starts,begin),bisect.bisect_left(all_starts,end)
        ahead=dispatches[a:b]
        # Equal timestamp cross-P observations cannot establish ordering.
        equal=sum(e['time_ns']==begin for e in ahead)+sum(e['time_ns']==end for e in dispatches[b:bisect.bisect_right(all_starts,end)])
        definitely=[e for e in ahead if begin<e['time_ns']<end]
        counts=Counter(roles.get(e['g'],'unclassified') for e in definitely)
        sources=Counter(e['selection_source'] for e in definitely)
        ca,cb=bisect.bisect_right(choice_times,begin),bisect.bisect_left(choice_times,end)
        selected=choices[ca:cb]
        forced=[e for e in selected if e['fair']]
        eligible.append(dict(g=wait['g'],request_id=marker['request'],outcome=outcomes[marker['request']],
            wake_ns=begin,dispatch_ns=end,wait_ns=wait['wait_ns'],wake_p=wake['p'],wake_m=wake['m'],
            final_selection=dispatch['selection'],final_selection_source=dispatch['selection_source'],
            dispatches_ahead=len(definitely),by_role=dict(counts),by_source=dict(sources),
            equal_boundary_timestamps=equal,
            selections_ahead=len(selected),
            selection_counts_by_source=dict(Counter(SOURCES[e['source']] for e in selected)),
            pending_selections_ahead=sum(e['pending'] for e in selected),
            forced_selections_ahead=len(forced),
            forced_dispatches_ahead=sum(bool(e['selection'] and e['selection']['fair']) for e in definitely),
            forced_selected_goroutines=[dict(g=e['g'],role=roles.get(e['g'],'unclassified'),
                time_ns=e['time_ns'],source=SOURCES[e['source']],selection=e,
                matched_dispatch_ns=executed[e['sequence']]['time_ns'] if e['sequence'] in executed else None) for e in forced],
            handler_mark_ns=marker['time_ns'],
            dispatch_evidence=[dict(g=e['g'],role=roles.get(e['g'],'unclassified'),time_ns=e['time_ns'],
                p=e['p'],m=e['m'],source=e['selection_source'],sequence=e['sequence'],
                selection_sequence=e['selection']['sequence'] if e['selection'] else None) for e in definitely]))
    values=sorted(e['wait_ns'] for e in eligible)
    import math
    return dict(observation_enabled=True,clock_mapping=clock,events=len(events),dispatches=len(dispatches),
        selected_sources=dict(Counter(SOURCES[e['source']] for e in rows if e['kind']==2)),
        unmatched_dispatches=sum(e['selection'] is None for e in dispatches),
        unresolved_wakes=unresolved,unlinked_http_network_waits=unlinked,
        cleanup_ambiguous=cleanup_ambiguous,
        matched_prehandler_network_waits=len(eligible),
        ready_wait_p99_ms=values[math.ceil(.99*len(values))-1]/1e6 if values else None,
        all_matched_waits=[{k:v for k,v in e.items() if k not in ('dispatch_evidence','forced_selected_goroutines')} for e in eligible],
        examples=sorted(eligible,key=lambda e:e['wait_ns'],reverse=True)[:10],eligible_for_full=False,
        limitations='Recorder hook timestamps measure observed wake-to-dispatch, not CPU execution. '
        'Only first running segments reaching a handler marker are linked. Selections before execute '
        'may be diverted; unmatched dispatches have no queue-source claim. Queue residence and the '
        'origin of preemption signals are not recorded. Equal boundary timestamps are ambiguous. '
        'Counts include capture control and drain, and examples can overlap.')


def analyze_attempt(attempt, enabled):
    return analyze_capture(run.read(attempt/'server_metrics.json'),run.read(attempt/'trace_status.json'),
                           run.read(attempt/'loadgen.json'),enabled)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('attempt',type=Path);parser.add_argument('--control',action='store_true')
    args=parser.parse_args();run.put(args.attempt/'scheduler_attribution.json',analyze_attempt(args.attempt,not args.control))
