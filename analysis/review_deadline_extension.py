"""Reviewer-style assessment: saved-data comparator check, not fresh confirmation.

Reads the open manuscript and preserved V31/NGINX evidence without editing them.
"""
import argparse
import hashlib
import json
from pathlib import Path
import statistics as st
import sys

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'analysis/runtime_io_deadline_extension_reviewer_assessment/20261010'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(ok, message):
    if not ok: raise ValueError(message)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify',action='store_true')
    args=parser.parse_args()
    if args.verify:
        seal=json.loads((OUT/'evidence-seal.json').read_text())['files_sha256']
        for name,digest in seal.items(): require(sha(ROOT/name)==digest,'Review package changed: '+name)
        inputs=json.loads((OUT/'inputs_sha256.json').read_text())
        for name,digest in inputs.items(): require(sha(ROOT/name)==digest,'Consumed evidence changed: '+name)
        print('Reviewer assessment package and consumed evidence verify.');return
    require(not OUT.exists(),'Preserve existing review; use --verify')
    inputs={}
    def read(path):
        path=ROOT/path if isinstance(path,str) else path
        inputs[str(path.relative_to(ROOT))]=sha(path)
        return json.loads(path.read_text())
    def verify_local_seal(directory):
        for name,digest in read(directory/'seal.json')['files_sha256'].items():
            require(sha(directory/name)==digest,'Calibration trial seal mismatch: '+name)
    for name in ['paper/deadline_resolution_extension.md','paper/deadline_resolution_extension.tex',
                 'paper/deadline_resolution_supporting_material.md','paper/deadline_resolution_reproducibility.md',
                 'analysis/finalize_deadline_extension.py','analysis/verify_deadline_extension.py',
                 'diagnostic/v31_model.py','diagnostic/v31_raw.py','tools/loadgen/main.go',
                 'diagnostic/nginx_prediction_model.py','diagnostic/nginx_client/main.go',
                 'docs/runtime_io_deadline_boundary_prior_work_review_20261010.md',
                 'analysis/runtime_io_deadline_boundary_prior_work_review/20261010/sources.json']:
        inputs[name]=sha(ROOT/name)
    completed=read('analysis/runtime_io_deadline_extension_finalization/20261010/report.json')
    for name,digest in completed['documents_and_tools_sha256'].items():
        require(sha(ROOT/name)==digest,'Finalized manuscript/tool changed: '+name)
    base=ROOT/'analysis/runtime_io_v31/generation-01'
    fit=read(base/'predictions/calibration.json')
    saved=read(base/'analysis/1791544686930410674/report.json')
    frozen_review=read('analysis/runtime_io_v31_result_review/20261009-generation01/report.json')
    cohort_names=list(fit['timing_cohorts']); require(len(cohort_names)==4,'Exactly four timing cohorts required')
    full=[]; selected_full=[]; queues=[]; cohorts=[]
    fitted={(x['trial'],x['id']):x for x in fit['paired_samples']}
    for name in cohort_names:
        directory=base/saved['trial_refs'][name]['path'];verify_local_seal(directory)
        clients=read(directory/'loadgen.json')['requests']
        jobs={r['id']:r for r in read(directory/'server_metrics.json')['events']}
        require(all(not r['Error'] and r['StatusCode']==200 for r in clients),'Unavailable complete-client calibration cohort')
        values=[]
        for row in clients:
            e2e=row['EndToEndLatencyNs'];job=jobs[row['ID']];queue=job['queue_wait_ns']
            values.append(e2e);full.append(e2e);queues.append(queue)
            if queue<=100000:
                sample=fitted[(name,row['ID'])]
                require(e2e-queue==sample['total_ns']==sample['worker_ns']+sample['residual_ns'],
                        'Queue-adjusted CDF identity differs')
                selected_full.append(e2e)
        cohorts.append(dict(trial=name,offers=len(values),miss_pct_10ms=100*sum(v>10000000 for v in values)/len(values)))
    require(len(full)==len(selected_full)==len(fitted)==676,'Expected all 676 offers eligible')
    rows=[];grid={}
    deadlines=list(frozen_review['deadline_grid']['joint_calibration_cdf'])
    for deadline in deadlines:
        threshold=float(deadline)*1000000
        predicted=100*sum(v>threshold for v in full)/len(full)
        errors=[dict(trial=r['trial'],block=r['block'],profile=r['profile'],
                     observed_miss_pct=r['observed_miss_pct'][deadline],forecast_miss_pct=predicted,
                     absolute_error_pp=abs(predicted-r['observed_miss_pct'][deadline]))
                for r in frozen_review['validation']]
        blocks=[dict(block=b,mae_pp=st.mean(e['absolute_error_pp'] for e in errors if e['block']==b)) for b in range(1,7)]
        grid[deadline]=dict(forecast_miss_pct=predicted,mae_pp=st.mean(b['mae_pp'] for b in blocks),
                            maximum_trial_error_pp=max(e['absolute_error_pp'] for e in errors),blocks=blocks)
        if deadline=='10':rows=errors
    primary=grid['10'];frozen_mae=frozen_review['deadline_grid']['joint_calibration_cdf']['10']['mae_pp']
    require(abs(primary['mae_pp']-1.802498670919723)<1e-10,'Complete-response reference arithmetic differs')
    ng=read('analysis/runtime_io_nginx_prediction/generation-01/campaign/comparison.json')
    result=dict(date='2026-10-10',role='reviewer_style_internal_audit_not_external_peer_review',
        verdict='revise_before_submission_contribution_needs_narrowing',
        source_manuscript_sha256=inputs['paper/deadline_resolution_extension.tex'],
        scientific_results_refuted=False,scientific_thresholds_changed=False,
        empirical_novelty_established=False,new_algorithm_established=False,
        new_performance_collection=False,prospective_control=False,
        comparator_check_role='Post-hoc saved-data diagnostic; method chosen after outcomes, calibration values only; no new confirmatory gate.',
        calibration_cohorts=cohorts,complete_response_reference_samples=len(full),
        queue_wait_mean_ns=st.mean(queues),queue_wait_maximum_ns=max(queues),
        all_client_records_also_meet_existing_queue_selection=True,
        algebraic_identity='worker + (e2e - queue - worker) = e2e - queue',
        whole_response_cdf_primary=primary,frozen_queue_subtracted_cdf_mae_pp=frozen_mae,
        descriptive_error_difference_pp=frozen_mae-primary['mae_pp'],
        tiny_difference_superiority_established=False,whole_response_cdf_grid=grid,primary_trial_errors=rows,
        client_observer_removal_qualified=False,client_only_deployment_prospectively_validated=False,
        nginx_block_errors_pp=ng['block_mae_pp'],
        nginx_largest_block_share_of_total_absolute_error=max(ng['block_mae_pp'])/sum(ng['block_mae_pp']),
        calibration_distribution_shared_across_applications=False,
        endpoint_clarification='Both primary validation targets are all-offer scheduled-to-client-completion misses; exact completion/body checks, forecast calibration inputs and observed domains differ.',
        limits='One host; four timing calibration cohorts and six validation blocks; block t intervals are conditional. The new comparator is retrospective and uses records collected with the existing apparatus.',
        recommended_next_step='Revise the existing empirical extension: add the ordinary complete-response diagnostic, distinguish target outcome from queue-adjusted calibration inputs, and improve self-contained methods. No new collection is required for those revisions.')
    OUT.mkdir(parents=True)
    (OUT/'report.json').write_text(json.dumps(result,indent=2)+'\n')
    (OUT/'inputs_sha256.json').write_text(json.dumps(inputs,indent=2)+'\n')
    (OUT/'review_deadline_extension.py').write_bytes(Path(__file__).read_bytes())
    note=ROOT/'docs/runtime_io_deadline_extension_reviewer_assessment_20261010.md'
    require(note.exists(),'Write the accompanying reviewer assessment before building its sealed package')
    (OUT/'report.md').write_bytes(note.read_bytes())
    outputs={str(p.relative_to(ROOT)):sha(p) for p in sorted(OUT.iterdir()) if p.is_file()}
    outputs[str(note.relative_to(ROOT))]=sha(note)
    outputs[str(Path(__file__).relative_to(ROOT))]=sha(Path(__file__))
    (OUT/'evidence-seal.json').write_text(json.dumps(dict(files_sha256=outputs),indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['verdict','scientific_results_refuted',
        'whole_response_cdf_primary','frozen_queue_subtracted_cdf_mae_pp','descriptive_error_difference_pp']},indent=2))


if __name__=='__main__':main()
