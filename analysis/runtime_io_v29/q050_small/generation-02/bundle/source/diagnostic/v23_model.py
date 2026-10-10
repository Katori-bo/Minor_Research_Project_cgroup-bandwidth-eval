"""Calibration-only FIFO forecasts and shared-clock queue diagnostics (no collector)."""
import bisect
import collections
import math
import statistics as st


def series(admissions, starts):
    changes = collections.Counter(admissions)
    changes.subtract(starts)
    times, values, count = [], [], 0
    for t, step in sorted(changes.items()):
        count += step
        if count < 0:
            raise ValueError('negative logical queue')
        times.append(t); values.append(count)
    if count:
        raise ValueError('open queue at drain')
    return times, values


def at(q, t):
    i = bisect.bisect_right(q[0], t)-1
    return q[1][i] if i>=0 else 0


def min_window(q, a, b):
    return min([at(q,a)] + q[1][bisect.bisect_right(q[0],a):bisect.bisect_left(q[0],b)])


def recover(q, boundary, horizon=5e9):
    """Last return below six jobs in a half-open horizon; times in ns."""
    end = boundary+horizon
    left = bisect.bisect_left(q[0], end)-1
    if left>=0 and q[1][left]>5:
        return None
    result = 0.0
    previous = at(q,boundary)
    for i in range(bisect.bisect_right(q[0],boundary),bisect.bisect_left(q[0],end)):
        if previous>5 and q[1][i]<=5:
            result = (q[0][i]-boundary)/1e9
        previous = q[1][i]
    return result


def recovery_bounds(q, origins, switches=(10,20,30,40,50), horizon_sec=5):
    """Exact piecewise event-boundary search with one shared origin, not per-event shifts."""
    lo,hi = origins
    critical = {lo,hi,(lo+hi)/2}
    for sec in switches:
        for boundary in (sec*1e9,(sec+horizon_sec)*1e9):
            i=bisect.bisect_left(q[0],lo+boundary)
            j=bisect.bisect_right(q[0],hi+boundary)
            critical.update(t-boundary for t in q[0][i:j])
    points=set(critical)
    for x in critical:
        for toward in (-math.inf,math.inf):
            y=math.nextafter(float(x),toward)
            if lo<=y<=hi: points.add(y)
    ordered=sorted(critical)
    points.update((x+y)/2 for x,y in zip(ordered,ordered[1:]))
    means=[];censored=False
    for origin in sorted(points):
        rr=[recover(q,origin+sec*1e9,horizon_sec*1e9) for sec in switches]
        if any(r is None for r in rr):censored=True
        else:means.append(st.mean(rr))
    midpoint=[recover(q,(lo+hi)/2+sec*1e9,horizon_sec*1e9) for sec in switches]
    return dict(lower_sec=min(means) if means else None,upper_sec=max(means) if means else None,
        midpoint_cycles_sec=midpoint,possibly_censored=censored,shared_origins_evaluated=len(points))


def simulate(offsets_ns, mu, period_sec=10):
    if not math.isfinite(mu) or mu<=0:
        raise ValueError('invalid model capacity')
    if not offsets_ns:raise ValueError('empty offered cohort')
    end=0.0;pending=collections.deque();rows=[]
    for rid,ns in enumerate(offsets_ns):
        t=ns/1e9
        while pending and pending[0]<=t:pending.popleft()
        if len(pending)>=129:
            rows.append(dict(id=rid,rejected=True,start_sec=None,start_ns=None,completion_sec=None,
                             latency_sec=None,timely_100=False,timely_500=False,timely_1000=False))
        else:
            start=max(t,end);end=start+1/mu;pending.append(end)
            start_ns=ns if start==t else max(ns,start*1e9)
            rows.append(dict(id=rid,rejected=False,start_sec=start,start_ns=start_ns,completion_sec=end,
                latency_sec=end-t,timely_100=end-t<=.1,timely_500=end-t<=.5,timely_1000=end-t<=1))
    q=series([offsets_ns[r['id']] for r in rows if not r['rejected']],
             [r['start_ns'] for r in rows if not r['rejected']])
    switches=tuple(range(period_sec,60,period_sec));horizon=period_sec*5e8
    ordinary=[recover(q,k*1e9,horizon) for k in switches]
    last=q[0][-1] if q[0] else 60e9
    latencies=sorted(r['latency_sec'] for r in rows if not r['rejected'])
    summary=dict(offers=len(rows),capacity_rps=mu,miss_pct=100*sum(not r['timely_500'] for r in rows)/len(rows),
        miss_1000_pct=100*sum(not r['timely_1000'] for r in rows)/len(rows),
        miss_100_pct=100*sum(not r['timely_100'] for r in rows)/len(rows),burst_period_sec=period_sec,
        rejections=sum(r['rejected'] for r in rows),queue_peak=max(q[1],default=0),
        recovery_cycles_sec=ordinary,recovery_mean_sec=st.mean(ordinary) if all(r is not None for r in ordinary) else None,
        final_drain_below6_sec=recover(q,60e9,max(1,last-60e9+1)),
        successful_after1000ms=sum(not r['rejected'] and not r['timely_1000'] for r in rows),
        successful_p99_ms=latencies[max(0,math.ceil(.99*len(latencies))-1)]*1000 if latencies else None,
        queue_grid_100ms=[at(q,i*1e8) for i in range(601)])
    return rows,summary


def trial_metrics(derived, server, cfg):
    jobs=server['events'];mapping=derived['clocks']
    q=series([j['admission_ns'] for j in jobs],[j['worker_start_ns'] for j in jobs])
    lo=mapping['client_test_start_ns']+mapping['server_minus_client_lower_ns']
    hi=mapping['client_test_start_ns']+mapping['server_minus_client_upper_ns']
    mid=(lo+hi)//2
    rows=derived['requests'];n=len(rows);summary=derived['summary']
    last=q[0][-1] if q[0] else mid+60e9
    return dict(offers=n,miss_pct=100*sum(not r['timely_500'] for r in rows)/n,
        miss_1000_pct=100*sum(not r['timely_1000'] for r in rows)/n,
        rejections=server['rejected'],queue_peak=max(q[1],default=0),
        recovery=recovery_bounds(q,(lo,hi),tuple(range(cfg['burst_period_sec'],60,cfg['burst_period_sec'])),cfg['burst_period_sec']/2),
        miss_100_pct=100*sum(not r['success'] or r['e2e_ns']>100_000_000 for r in rows)/n,
        final_drain_below6_midpoint_sec=recover(q,mid+60e9,max(1,last-mid-60e9+1)),
        successful_after1000ms=sum(r['success'] and not r['timely_1000'] for r in rows),
        queue_grid_100ms=[at(q,mid+i*1e8) for i in range(601)],
        cpu_usec_per_job=summary['cpu_usec_per_completed_work'],
        delivered_cpu_fraction=summary['counter_window']['delta']['usage_usec']/1e6 /
            ((summary['counter_window']['after_ns']-summary['counter_window']['before_ns'])/1e9),
        stage_coverage=dict(worker=n-summary['missing_worker_count'],handler=n-summary['missing_handler_count']),
        outcome_counts=summary['outcome_counts'],
        successful_p99_ms=summary['p99_e2e_ms'])


def calibration(derived_trials, servers, design, size):
    if len(derived_trials)!=2 or len(servers)!=2:
        raise ValueError('exactly two calibration inputs required')
    results=[]
    allowed=set(design['calibration']['trial_ids_by_size'][size])
    for derived,server in zip(derived_trials,servers):
        if derived['summary']['trial'] not in allowed:
            raise ValueError('non-calibration input prohibited')
        m=derived['clocks'];lo=m['client_test_start_ns']+m['server_minus_client_lower_ns']
        hi=m['client_test_start_ns']+m['server_minus_client_upper_ns'];mid=(lo+hi)//2
        jobs=server['events'];q=series([j['admission_ns'] for j in jobs],[j['worker_start_ns'] for j in jobs])
        ends=sorted(j['completion_ns'] for j in jobs)
        def count(a,b):return bisect.bisect_left(ends,b)-bisect.bisect_left(ends,a)
        windows=design['calibration']['fixed_half_open_windows_sec']
        valid=all(min_window(q,lo+a*1e9,hi+b*1e9)>5 for a,b in windows)
        c=sum(count(mid+a*1e9,mid+b*1e9) for a,b in windows)
        lower=sum(count(hi+a*1e9,lo+b*1e9) for a,b in windows)
        upper=sum(count(lo+a*1e9,hi+b*1e9) for a,b in windows)
        results.append(dict(trial=derived['summary']['trial'],backlogged_windows_valid=valid,
            completions=c,count_lower=lower,count_upper=upper,capacity_rps=c/18,
            cpu_sec_per_job=derived['summary']['cpu_usec_per_completed_work']/1e6
                if derived['summary']['cpu_usec_per_completed_work'] is not None else None))
    if {r['trial'] for r in results}!=allowed:
        raise ValueError('duplicate calibration IDs')
    rates=[r['capacity_rps'] for r in results]
    stable=all(r>0 and math.isfinite(r) for r in rates)
    disagreement=abs(rates[0]-rates[1])/st.mean(rates) if stable else None
    adequate=all(r['backlogged_windows_valid'] for r in results)
    costs=[r['cpu_sec_per_job'] for r in results]
    valid_cost=all(c is not None and math.isfinite(c) and c>0 for c in costs)
    passed=adequate and stable and disagreement<=.05 and valid_cost
    return dict(passed=passed,decision='adequate_stable' if passed else 'inadequate_backlog' if not adequate else 'unstable_or_invalid_calibration',
        trials=results,relative_disagreement=disagreement,
        mu_busy=st.mean(rates) if stable else None,mu_cpu=.5/st.mean(costs) if valid_cost else None,
        sensitivity_lower=.95*min(r['count_lower']/18 for r in results),
        sensitivity_upper=1.05*max(r['count_upper']/18 for r in results))


def predictions(cal, patterns, periods):
    if not cal['passed']:
        raise ValueError('inadequate/unstable calibration cannot produce validation permission')
    point={};per_id={}
    for model,key in (('M_busy','mu_busy'),('M_cpu','mu_cpu')):
        point[model]={};per_id[model]={}
        for arm,vec in patterns.items():
            per_id[model][arm],point[model][arm]=simulate(vec,cal[key],periods[arm])
    lo,hi=cal['sensitivity_lower'],cal['sensitivity_upper']
    rates=sorted({lo+(hi-lo)*i/100 for i in range(101)}|{cal['mu_busy']})
    sensitivity={arm:[simulate(vec,mu,periods[arm])[1] for mu in rates] for arm,vec in patterns.items()}
    return dict(point=point,sensitivity=sensitivity),per_id


def evaluate(observed, forecast, arm):
    errors=dict(miss_error_pp=forecast['miss_pct']-observed['miss_pct'],
        queue_peak_error=forecast['queue_peak']-observed['queue_peak'],
        rejection_error_pp=100*(forecast['rejections']-observed['rejections'])/observed['offers'])
    rec=observed['recovery'];pred=forecast['recovery_mean_sec']
    assessable=pred is not None and not rec['possibly_censored'] and rec['lower_sec'] is not None
    worst=max(abs(pred-rec['lower_sec']),abs(pred-rec['upper_sec'])) if assessable else None
    errors.update(recovery_worst_error_sec=worst)
    checks=dict(primary=abs(errors['miss_error_pp'])<=3,
        queue=abs(errors['queue_peak_error'])<=10,rejection=abs(errors['rejection_error_pp'])<=.5,
        recovery=worst is not None and worst<=.25)
    diagnostic={}
    for name,key in (('miss_100_error_pp','miss_100_pct'),('miss_1000_error_pp','miss_1000_pct'),
                     ('successful_after1000ms_error_count','successful_after1000ms'),
                     ('successful_p99_error_ms','successful_p99_ms')):
        if key in observed:
            diagnostic[name]=forecast[key]-observed[key] if forecast[key] is not None and observed[key] is not None else None
    if 'final_drain_below6_midpoint_sec' in observed:
        actual=observed['final_drain_below6_midpoint_sec'];expected=forecast['final_drain_below6_sec']
        diagnostic['final_drain_midpoint_error_sec']=expected-actual if actual is not None and expected is not None else None
    return dict(errors=errors,checks=checks,diagnostic_errors=diagnostic)


def report(trials, prediction):
    by_id={t['trial']:t for t in trials}
    if len(by_id)!=len(trials):raise ValueError('duplicate validation trial')
    blocks=[];size_results={}
    for size in ('small','large'):
        selected=[t for t in trials if t['size']==size];pairs=[]
        for b in range(1,5):
            a=by_id.get(f'b{b}_{size}_A');other=by_id.get(f'b{b}_{size}_B')
            complete=a is not None and other is not None
            block=dict(block=b,size=size,complete=complete)
            if complete:
                actual=other['observed']['miss_pct']-a['observed']['miss_pct']
                point=prediction['by_size'][size]['point']['M_busy']
                expected=point['B']['miss_pct']-point['A']['miss_pct']
                scores={m:st.mean(abs(t['models'][m]['errors']['miss_error_pp']) for t in (a,other)) for m in ('M_busy','M_cpu')}
                block.update(observed_long_minus_short_pp=actual,predicted_long_minus_short_pp=expected,
                    contrast_error_pp=expected-actual,primary_contrast_pass=abs(expected-actual)<=3,baseline_scores=scores)
            pairs.append(block);blocks.append(block)
        complete=len(selected)==8 and all(b['complete'] for b in pairs)
        primary=complete and all(t['models']['M_busy']['checks']['primary'] for t in selected) and all(b['primary_contrast_pass'] for b in pairs)
        advantage=complete and all(b['baseline_scores']['M_busy']<b['baseline_scores']['M_cpu'] for b in pairs) and st.mean(b['baseline_scores']['M_cpu']-b['baseline_scores']['M_busy'] for b in pairs)>=1
        size_results[size]=dict(complete=complete,primary_pass=primary,baseline_advantage=advantage)
    complete=len(trials)==16 and all(r['complete'] for r in size_results.values())
    primary=complete and all(r['primary_pass'] for r in size_results.values())
    queue=complete and all(all(v is True for k,v in t['models']['M_busy']['checks'].items() if k!='primary') for t in trials)
    return dict(decision='incomplete_validation' if not complete else 'primary_transfer_pass' if primary else 'primary_transfer_fail',
        complete=complete,primary_pass=primary,supporting_queue_pass=queue,
        baseline_advantage=complete and all(r['baseline_advantage'] for r in size_results.values()),
        by_size=size_results,trials=trials,blocks=blocks,novelty_established=False,
        limits='One host/boot/service/hash algorithm; two work sizes and burst cycles; no universal transfer or new estimator.')
