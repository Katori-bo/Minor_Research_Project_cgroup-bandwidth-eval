"""Fixed-slot decision report; no target-based selection or inferred missing labels."""
import evaluation as e


def report(plan, records):
    """Records keyed by campaign then window, after raw and apparatus replay.

    Each status is unavailable, primary_domain or applicability_exit. Complete
    records supply the receipt replay's cells; unavailable records preserve their
    reason/raw counts and have no complete-window score. Missing slots remain
    explicitly unobserved. This function does not itself certify resource replay.
    """
    campaigns = {c['id']: c for c in plan['campaigns']}
    e.require(set(records) <= set(campaigns), 'foreign campaign')
    output = []
    all_windows = []
    for cid, campaign in campaigns.items():
        app = campaign['application']
        # Go retained trial IDs use the same block/profile order as NGINX.
        keys = [('v31_' if app == 'Go' else '') + 'b%d_%s' % (b, p)
                for b, order in enumerate(('ABC','BCA','CAB','ACB','CBA','BAC'),1) for p in order]
        labels = ['q/'+q for q in plan['quantiles']] + ['fixed/'+str(d) for d in plan['fixed_deadlines_ns'][app]]
        supplied = records.get(cid, {})
        e.require(set(supplied) <= set(keys), 'foreign window slot')
        rows = []
        for key in keys:
            value = supplied.get(key, dict(status='unavailable', reason='unobserved'))
            e.require(value['status'] in ('unavailable','primary_domain','applicability_exit'), 'unknown availability')
            if value['status'] == 'unavailable':
                e.require(not value.get('cells'), 'unavailable window cannot have complete decisions')
            else:
                e.require([cell['label'] for cell in value['cells']] == labels, 'all deadline labels required')
                for cell in value['cells']:
                    e.require(set(cell['methods']) == (set(plan['methods']) if cell['deadline_ns'] is not None else set()),
                              'missing method or unavailable deadline mislabelled')
            row=dict(campaign_id=cid, window_id=key, **value)
            rows.append(row);all_windows.append(row)
        for view in ('complete_trusted','primary_domain'):
            selected = [r for r in rows if r['status'] != 'unavailable' and
                        (view == 'complete_trusted' or r['status'] == 'primary_domain')]
            for label in labels:
                for method in plan['methods']:
                    for procedure in ('point','dkw'):
                        counts = dict(meets=0,exceeds=0,inconclusive=0,unavailable_deadline=0,
                            false_assurance=0,unnecessary_rejection=0,observed_compliant=0)
                        for row in selected:
                            cell = next(c for c in row['cells'] if c['label'] == label)
                            if cell['deadline_ns'] is None:
                                counts['unavailable_deadline'] += 1;continue
                            value=cell['methods'][method];f,s=value['forecast'],value['score']
                            decision=f[procedure+'_decision']
                            counts[decision]+=1
                            counts['observed_compliant']+=s['observed_decision']=='meets'
                            prefix='' if procedure=='point' else 'interval_'
                            counts['false_assurance']+=s[prefix+'false_assurance']
                            counts['unnecessary_rejection']+=s[prefix+'unnecessary_rejection']
                        output.append(dict(campaign_id=cid,view=view,label=label,method=method,
                            procedure=procedure,counts=counts,
                            rates=e.rates(counts,18,len(selected))))
    primary = [r for r in all_windows if r['status']=='primary_domain' and
        next(c for c in r['cells'] if c['label']=='q/39/40')['deadline_ns'] is not None and
        next(c for c in r['cells'] if c['label']=='q/39/40')['methods']['reference']['score']
            ['positive_slack_small_error_false_assurance']]
    return dict(planned_windows=72,windows=all_windows,tables=output,
        primary_event_windows=[dict(campaign_id=r['campaign_id'],window_id=r['window_id']) for r in primary],
        independent_hardware_event_observed=any(campaigns[r['campaign_id']]['host']=='host02' for r in primary),
        missing_windows_assumed_safe=False,population_risk_certified=False)
