"""Ordinary CDF forecasts at fresh calibration cutoffs; per-policy block scores."""
import math
from fractions import Fraction
import statistics as st
import nginx_deadline_panel_common as c
import nginx_power_confirmation_model as old

outcomes,reference,merge,reference_probability,miss_fraction=(old.outcomes,old.reference,old.merge,
    old.reference_probability,old.miss_fraction)


def cutoffs(ref):
    result=[]
    for label in c.PROTOCOL['quantiles']:
        rank=math.floor(Fraction(label)*(ref['offers']-1))
        result.append(dict(quantile=label,rank=rank,
            deadline_ns=ref['successful_samples_ns'][rank] if rank<len(ref['successful_samples_ns']) else None))
    return result


def fit(rows,schedule):
    c.require([r['config'] for r in rows]==schedule['calibration'],'Fresh exact calibration sequence required')
    cohorts={p:[] for p in c.POLICIES}
    for r in rows:
        c.require(not r['domain_exits'] and len(r['outcomes'])==400,'Incomplete or corrupt calibration')
        cohorts[r['config']['policy']].append(reference(r['outcomes']))
    refs={p:merge(*v) for p,v in cohorts.items()}
    c.require(all(r['offers']==800 for r in refs.values()),'Two fresh cohorts per policy required')
    panels={p:cutoffs(r) for p,r in refs.items()}
    available=all(d['deadline_ns'] is not None for panel in panels.values() for d in panel)
    f=dict(schema='nginx-deadline-panel-forecast-v1',references=dict(**refs,pooled=merge(*refs.values())),
        panels=panels,panel_available=available,calibration_cohorts=cohorts,validation_used=False,
        source='Only four fresh calibration cohorts; no historical outcomes used',
        historical_deadline_ns=c.PROTOCOL['historical_deadline_ns'],queue_subtraction=False)
    # Freeze every calibration-based method at every assigned-policy cutoff
    # globally before validation; warmup-based methods are sealed per cohort later.
    f['calibration_predictions']={p:[dict(**d,predictions={name:reference_probability(ref,d['deadline_ns'])
        if d['deadline_ns'] is not None else None for name,ref in
        dict(matched=refs[p],pooled=f['references']['pooled'],baseline=refs['P0']).items()})
        for d in panel] for p,panel in panels.items()}
    return f


def deadlines(forecast,cfg):
    c.require(forecast['panel_available'] and not forecast['validation_used'],'Unavailable or future-based panel')
    c.require(forecast['panels'][cfg['policy']]==cutoffs(forecast['references'][cfg['policy']]),'Cutoff rule differs')
    return sorted(set([forecast['historical_deadline_ns']]+[d['deadline_ns'] for d in forecast['panels'][cfg['policy']]]))


def predictions(forecast,cfg,warmup,deadline):
    c.require(deadline in deadlines(forecast,cfg),'Undeclared deadline')
    c.require(len(warmup)==25,'Complete all-offer warmup required')
    warm=reference(warmup);matched=forecast['references'][cfg['policy']];pooled=forecast['references']['pooled']
    return {name:reference_probability(ref,deadline) for name,ref in
        dict(matched=matched,pooled=pooled,baseline=forecast['references']['P0'],
            warmup=warm,matched_update=merge(matched,warm),pooled_update=merge(pooled,warm)).items()}


def interval(values,multiplier=3.164):
    c.require(len(values)==6,'Six complete block units required')
    mean=st.mean(values);half=multiplier*st.stdev(values)/math.sqrt(6)
    return dict(mean=mean,conditional_interval=[mean-half,mean+half],blocks=values,multiplier=multiplier)


def compare(rows,forecast,schedule):
    c.require([r['config'] for r in rows]==schedule['validation'],'Exact full validation sequence required')
    c.require(all(len(r['outcomes'])==300 and len(r['warmup_outcomes'])==25 for r in rows),'All-offer count differs')
    c.require(forecast['panel_available'] and not forecast['validation_used'],'Finite advance panel required')
    results=[]
    for r in rows:
        cfg=r['config'];panels=[]
        for point in forecast['panels'][cfg['policy']]:
            d=point['deadline_ns'];pred=predictions(forecast,cfg,r['warmup_outcomes'],d);observed=miss_fraction(r['outcomes'],d)
            panels.append(dict(**point,observed=observed,predictions=pred,
                absolute_error_pp={k:100*abs(v-observed) for k,v in pred.items()}))
        d=forecast['historical_deadline_ns'];pred=predictions(forecast,cfg,r['warmup_outcomes'],d);obs=miss_fraction(r['outcomes'],d)
        results.append(dict(config=cfg,panel=panels,historical=dict(deadline_ns=d,observed=obs,predictions=pred,
            absolute_error_pp={k:100*abs(v-obs) for k,v in pred.items()})))
    policies={}
    for p in c.POLICIES:
        subset=[r for r in results if r['config']['policy']==p];methods={}
        for name in subset[0]['panel'][0]['predictions']:
            worst=[];average=[];historical=[];pointblocks={q:[] for q in c.PROTOCOL['quantiles']}
            for b in range(1,7):
                cell=[r for r in subset if r['config']['block']==b]
                c.require(sorted(r['config']['rate_rps'] for r in cell)==[4,8],'Policy/rate block incomplete')
                bycutoff=[st.mean(r['panel'][i]['absolute_error_pp'][name] for r in cell)
                    for i in range(len(c.PROTOCOL['quantiles']))]
                worst.append(max(bycutoff));average.append(st.mean(bycutoff))
                historical.append(st.mean(r['historical']['absolute_error_pp'][name] for r in cell))
                for label,value in zip(c.PROTOCOL['quantiles'],bycutoff):pointblocks[label].append(value)
            methods[name]=dict(worst_cutoff_block_score=interval(worst,c.PROTOCOL['primary_t_multiplier']),
                panel_average=interval(average,c.PROTOCOL['descriptive_t_multiplier']),
                historical=interval(historical,c.PROTOCOL['descriptive_t_multiplier']),
                per_cutoff={label:dict(**interval(values,c.PROTOCOL['descriptive_t_multiplier']),
                    deadline_ns=forecast['panels'][p][i]['deadline_ns'])
                    for i,(label,values) in enumerate(pointblocks.items())},
                maximum_panel_error_pp=max(d['absolute_error_pp'][name] for r in subset for d in r['panel']),
                panel_errors_above_5pp=sum(d['absolute_error_pp'][name]>5 for r in subset for d in r['panel']))
        matched=methods['matched']['worst_cutoff_block_score']
        gain=interval([methods['pooled']['worst_cutoff_block_score']['blocks'][i]-matched['blocks'][i]
            for i in range(6)],c.PROTOCOL['descriptive_t_multiplier'])
        policies[p]=dict(methods=methods,matched_accuracy_supported=matched['conditional_interval'][1]<=5,
            matched_vs_pooled_gain=gain,
            descriptive_advantage=gain['mean']>=2 and gain['conditional_interval'][0]>0)
    exits=[dict(config=r['config'],exits=r['domain_exits']) for r in rows if r['domain_exits']]
    flags={p:v['matched_accuracy_supported'] for p,v in policies.items()}
    status=('technical_invalid' if exits else 'deadline_panel_accuracy_both_supported' if all(flags.values())
        else 'deadline_panel_accuracy_partly_supported' if any(flags.values()) else 'deadline_panel_accuracy_not_supported')
    return dict(status=status,policies=policies,matched_accuracy_supported=flags,errors=results,
        original_historical_deadline_ns=forecast['historical_deadline_ns'],domain_exits=exits,
        family_inference=c.PROTOCOL['primary_family'],calibration_uncertainty_propagated=False,
        pointwise_intervals='Descriptive95%; no ten-cutoff simultaneous guarantee or new per-cutoff acceptance decisions',
        cohort_observations=[{k:r[k] for k in ('config','offers','successful','observations','warmup_counter_delta',
            'measurement_counter_delta','unsuccessful_counts','failure_categories','cpu_per_offer_us','mean_stages_ns',
            'maximum_client_response_overlap','response_ns') if k in r} for r in rows],
        comparison_information='Every method receives the same four calibration cohorts, known policy and 25-offer warmup; ordinary matched-policy CDF is the main method under test. Full1600-offer calibration acquisition is charged for all methods.',
        equal_acquisition_for_methods=True,failure_mass_retained=True,novelty_established=False,
        fixed_frequency=False,independent_host_replication=False,causal_mechanism_identified=False,
        all_deadline_population_guarantee=False,
        inference_limit='Six chronological blocks; per-policy worst-cutoff score tests conditional average block adequacy, not every cohort or all finite deadlines. Normal block-score approximation and independence unverified; source-matched stock service, policy readback not actual frequency. Fresh evidence selected after known development outcomes; no new method.')
