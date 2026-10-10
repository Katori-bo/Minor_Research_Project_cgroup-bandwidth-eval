#!/usr/bin/env python3
"""Read-only independent V22 completion review; retain a new interpretation receipt."""
import datetime
import statistics
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'diagnostic'))
import v22_study as runner


def main():
    c=runner.c;session=c.PARENT/'generation-02'
    result=runner.verify.verify_completion(session)
    latest=c.read(session/'latest_analysis.json');out=ROOT/'analysis/runtime_io_v22_result_review/20261007'
    if out.exists():raise ValueError('keep the existing receipt; use a new review directory if revising')
    out.mkdir(parents=True)
    trials=result['trials'];burst=[t for t in trials if t['arm']=='A'];even=[t for t in trials if t['arm']=='B']
    cpu_ratios=[next(t for t in even if t['block']==a['block'])['observed']['cpu_usec_per_job']/a['observed']['cpu_usec_per_job'] for a in burst]
    value=dict(schema=1,at=datetime.datetime.now(datetime.timezone.utc).isoformat(),raw_completion_verified=True,
        generation=str(session),analysis_path=latest['path'],analysis_seal=latest['seal'],
        prediction_seal=c.digest(session/'predictions/seal.json'),review_script_sha256=c.digest(Path(__file__)),
        decision=result['decision'],completed_validation_trials=len(trials),paired_blocks=len(result['blocks']),
        primary_checks_passed=sum(t['models']['M_busy']['checks']['primary'] for t in trials)+sum(b['primary_contrast_pass'] for b in result['blocks']),
        calibration=c.read(session/'predictions/calibration.json'),
        metrics=dict(burst_miss_range_pct=[min(t['observed']['miss_pct'] for t in burst),max(t['observed']['miss_pct'] for t in burst)],
            mean_burst_miss_pct=statistics.mean(t['observed']['miss_pct'] for t in burst),
            max_primary_abs_error_pp=max(abs(t['models']['M_busy']['errors']['miss_error_pp']) for t in trials),
            max_queue_abs_error=max(abs(t['models']['M_busy']['errors']['queue_peak_error']) for t in trials),
            max_recovery_worst_error_ms=1000*max(t['models']['M_busy']['errors']['recovery_worst_error_sec'] for t in burst),
            even_all_offer_500ms_misses=sum(t['observed']['offers']*t['observed']['miss_pct']/100 for t in even),
            successful_after1000ms=sum(t['observed']['successful_after1000ms'] for t in trials),
            rejections=sum(t['observed']['rejections'] for t in trials),
            even_cpu_job_paired_ratio=cpu_ratios,mean_even_cpu_job_increase_pct=100*(statistics.mean(cpu_ratios)-1),
            max_individual_burst_response_abs_error_ms=max(t['stage_residuals']['e2e']['absolute_residual_distribution_ms']['maximum'] for t in burst)),
        supporting_queue_pass=result['supporting_queue_pass'],even_screen_pass=result['even_screen_pass'],baseline_advantage=result['baseline_advantage'],
        performance_run=False,settings_changed=False,novelty_established=False,
        limits='V22 validates one host/boot/service/work size. CPU/job and wall busy capacity are distinct; their causal difference is not isolated. Yielding off; no cross-workload generalization.')
    c.save(out/'report.json',value);c.seal(out)
    print('V22 verified result review:',out/'report.json')
    print('Primary checks:',value['primary_checks_passed'],'of12; largest error:',value['metrics']['max_primary_abs_error_pp'],'pp')


if __name__=='__main__':main()
