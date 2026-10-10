"""One bounded retrospective alternative: latency envelopes, not scalar pp padding.

All inputs and deadlines were already seen. This is development, NOT a fresh
validation, a probabilistic guarantee, or a reproduction of prior algorithms.
"""
from fractions import Fraction
from math import ceil
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'diagnostic'))
import v28_common as c
from deadline_capacity_guard import fifo, diagnose


def read(p):
    return json.loads(p.read_text())


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def latencies(offsets, mu):
    service = Fraction(1_000_000_000)/Fraction(str(mu))
    last = Fraction(0)
    result = []
    for stamp in offsets:
        last = max(stamp, last)+service
        result.append(last-stamp)
    return result


def main():
    out = ROOT/'analysis/runtime_io_deadline_guard_exploration/20261008-timing-envelope'
    if out.exists():
        raise ValueError('preserve the existing exploratory result')
    session = c.PARENT/'generation-01'
    original = c.resolve(session, read(session/'latest_analysis.json')['path'])
    c.verify_seal(original)
    report = read(original/'report.json')
    window_path = ROOT/'analysis/runtime_io_deadline_guard_exploration/20261008-window-transfer/report.json'
    window_report = read(window_path)
    inputs = {str(window_path.relative_to(ROOT)):sha(window_path),
              str((original/'report.json').relative_to(ROOT)):sha(original/'report.json')}
    heldout = [x for x in report['trial_accounting'] if x['role']=='mixed' and x['block']==2]
    configs = {x['trial']:x for x in c.calibration_configs()}
    margins = {}; scalar_margins = {}
    for duration in ('1.0','1.8'):
        lo,hi = window_report['duration_envelopes_rps'][duration]
        lower_shift = upper_shift = Fraction(0)
        scalar_margin = 0
        per_trial = []
        for row in heldout:
            cfg = configs[row['trial']]; offsets = c.schedule(cfg)
            trial = c.resolve(session, report['trial_refs'][row['trial']]['path'])
            c.verify_seal(trial)
            path = trial/'loadgen.json';client = read(path)
            inputs[str(path.relative_to(ROOT))] = sha(path)
            c.validate_client(client,cfg)
            requests = {r['ID']:r for r in client['requests']}
            if len(requests)!=len(offsets) or any(r['Error'] or r['StatusCode']!=200 for r in requests.values()):
                raise ValueError('exact successful calibration cohort required')
            slow,fast = latencies(offsets,lo),latencies(offsets,hi)
            if fifo(offsets,lo,system_slots=None)['system_peak']>129:
                raise ValueError('reference calibration may reject')
            a = max([Fraction(0)]+[fast[i]-requests[i]['EndToEndLatencyNs'] for i in range(len(offsets))])
            b = max([Fraction(0)]+[requests[i]['EndToEndLatencyNs']-slow[i] for i in range(len(offsets))])
            lower_shift=max(lower_shift,a);upper_shift=max(upper_shift,b)
            per_trial.append(dict(trial=row['trial'], early_shift_ns=ceil(a),late_shift_ns=ceil(b)))
            scalar_margin=max(scalar_margin,max(abs(row['miss_pct']-fifo(offsets,mu)['miss_pct']) for mu in (lo,hi)))
        margins[duration]=dict(early_shift_ns=ceil(lower_shift),late_shift_ns=ceil(upper_shift),trials=per_trial)
        scalar_margins[duration]=scalar_margin
    # Produce every rule decision without consulting the observed validation rows.
    decisions=[]
    for cfg in c.validation_configs():
        duration='1.0' if cfg['burst_period_sec']==6 else '1.8'
        offsets=c.schedule(cfg);lo,hi=window_report['duration_envelopes_rps'][duration]
        slow,fast=latencies(offsets,lo),latencies(offsets,hi)
        reject_free=fifo(offsets,lo,system_slots=None)['system_peak']<=129
        m=margins[duration]
        lower=100*sum(max(0,x-m['early_shift_ns'])>500_000_000 for x in fast)/len(offsets)
        upper=100*sum(x+m['late_shift_ns']>500_000_000 for x in slow)/len(offsets)
        for method,value in report['calibration']['methods'].items():
            forecast=fifo(offsets,value['capacity_rps'])['miss_pct']
            bound=max(abs(forecast-lower),abs(forecast-upper)) if reject_free else None
            scalar=diagnose(offsets,value['capacity_rps'],[lo,hi],scalar_margins[duration])
            decisions.append(dict(trial=cfg['trial'],method=method,period_sec=cfg['burst_period_sec'],
                                  predicted_miss_pct=forecast,reference_miss_envelope_pct=[lower,upper] if reject_free else None,
                                  conditional_error_bound_pp=bound,
                                  decision=('insufficient_model_support' if bound is None else
                                            'accept_conditional' if bound<=3 else 'flag_for_recalibration'),
                                  scalar_margin_decision=scalar['decision']))
    observed={r['trial']:r for r in report['trial_accounting'] if r['role']=='validation'}
    summaries={}
    for method in report['calibration']['methods']:
        selected=[r for r in decisions if r['method']==method]
        for r in selected:
            r['observed_error_pp']=abs(r['predicted_miss_pct']-observed[r['trial']]['miss_pct'])
            envelope=r['reference_miss_envelope_pct']
            r['observed_miss_within_envelope']=envelope is not None and envelope[0]<=observed[r['trial']]['miss_pct']<=envelope[1]
        accepted=[r for r in selected if r['decision']=='accept_conditional']
        flagged=[r for r in selected if r['decision']=='flag_for_recalibration']
        summaries[method]=dict(accepted=len(accepted),flagged=len(flagged),abstained=len(selected)-len(accepted)-len(flagged),
                               inaccurate_accepted=sum(r['observed_error_pp']>3 for r in accepted),
                               inaccurate_flagged=sum(r['observed_error_pp']>3 for r in flagged),
                               accurate_flagged=sum(r['observed_error_pp']<=3 for r in flagged),
                               observed_envelope_coverage=sum(r['observed_miss_within_envelope'] for r in selected),
                               wider_range_scalar_margin_accepts=sum(r['scalar_margin_decision']=='accept_conditional' for r in selected))
    result=dict(prospective_validation=False,novelty_established=False,scientific_collection_started=False,
                reference_capacity_rps=window_report['duration_envelopes_rps'],timing_margins=margins,
                global_scalar_margins_pp=scalar_margins,summaries=summaries,decisions=decisions,
                input_sha256=inputs,source_sha256=sha(Path(__file__)),
                conditional_on='Future offered-cohort miss fraction lies within the timing envelope; empirical calibration does not guarantee this.',
                limits=['All V28 outcomes previously known; development choices are retrospective.',
                        'Two discrepancy-calibration runs and correlated windows do not give statistical future coverage.',
                        'Backlogged probes are required; no measurement saving established.',
                        'Per-offer envelopes and deterministic FIFO sensitivity have substantial prior art.'])
    out.mkdir(parents=True)
    (out/'report.json').write_text(json.dumps(result,indent=2)+'\n')
    if any(sha(ROOT/p)!=digest for p,digest in inputs.items()):
        raise ValueError('historical input changed')
    (out/'seal.json').write_text(json.dumps(dict(files_sha256={'report.json':sha(out/'report.json')}),indent=2)+'\n')
    print(json.dumps(dict(timing_margins=margins,global_scalar_margins_pp=scalar_margins,summaries=summaries),indent=2))


if __name__=='__main__':
    main()
