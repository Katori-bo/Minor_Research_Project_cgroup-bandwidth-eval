"""Offline consistency/preservation audit of the completed empirical extension.

Uses only saved results and the standard library; no collector or model fitter.
"""
import hashlib
import json
import math
from pathlib import Path
import re
import statistics as st

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'analysis/runtime_io_deadline_extension_finalization/20261010'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(rel):
    return json.loads((ROOT / rel).read_text())


def require(ok, message):
    if not ok: raise ValueError(message)


def close(actual, expected):
    require(math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-10),
            f'Numerical mismatch: {actual} != {expected}')


def verify_seal(path):
    verified = {}
    for name, expected in json.loads(path.read_text())['files_sha256'].items():
        local = path.parent / name
        file = local if local.exists() else ROOT / name
        require(file.is_file(), 'Missing sealed file: ' + str(file))
        require(sha(file) == expected, 'Existing seal mismatch: ' + str(file))
        verified[str(file.relative_to(ROOT))] = expected
    verified[str(path.relative_to(ROOT))] = sha(path)
    return verified


def preserved_inventory():
    """Protect extension campaign sources, forecasts/raw records and review seals."""
    roots = [
        'analysis/runtime_io_v30/generation-01',
        'analysis/runtime_io_v31/generation-01',
        'analysis/runtime_io_nginx_prediction/generation-01',
        'analysis/runtime_io_v29_result_review/20261009-complete-matrix',
        'analysis/runtime_io_v30_result_review/20261009-generation01',
        'analysis/runtime_io_v31_result_review/20261009-generation01',
        'analysis/runtime_io_v2_extension/20261009-v30-timing-boundary',
        'analysis/runtime_io_nginx_prediction_result_review/20261009-generation01',
        'analysis/runtime_io_nginx_prediction_diagnosis/20261010-generation01',
        'analysis/runtime_io_deadline_boundary_prior_work_review/20261010',
        'analysis/runtime_io_imgproxy_feasibility_review/20261009-generation01',
        'analysis/runtime_io_imgproxy_one_cpu_abort_review/20261009-generation01',
        'analysis/runtime_io_imgproxy_one_cpu_failure_review/20261009-generation02',
        'analysis/runtime_io_gzip_failure_review/20261009-generation01',
        'analysis/runtime_io_nginx_qualification_review/20261009-generation02',
    ]
    inventory = {}; seals = []
    for rel in roots:
        for path in sorted((ROOT / rel).rglob('*seal.json')):
            require(not path.is_symlink(), 'Unexpected seal symlink')
            mapping = json.loads(path.read_text())
            if 'files_sha256' not in mapping: continue
            inventory.update(verify_seal(path)); seals.append(str(path.relative_to(ROOT)))
    for rel in ['paper/capacity_calibration_empirical.md', 'paper/capacity_calibration_empirical.tex',
                'docs/runtime_io_v31_candidate_protocol_20261009.md',
                'docs/runtime_io_nginx_prediction_protocol_20261009.md']:
        inventory[rel] = sha(ROOT / rel)
    return inventory, seals


def tables(text):
    groups = []; rows = []
    for line in text.splitlines() + ['']:
        if line.startswith('|'):
            row = [x.strip() for x in line.strip('|').split('|')]
            if not all(re.fullmatch(r'[-:]+',x) for x in row): rows.append(row)
        elif rows:
            groups.append(rows); rows=[]
    return groups


def audit():
    v29 = read('analysis/runtime_io_v29_result_review/20261009-complete-matrix/report.json')
    v30 = read('analysis/runtime_io_v30_result_review/20261009-generation01/report.json')
    v31 = read('analysis/runtime_io_v31_result_review/20261009-generation01/report.json')
    nginx = read('analysis/runtime_io_nginx_prediction_result_review/20261009-generation01/report.json')
    comparison = read('analysis/runtime_io_nginx_prediction/generation-01/campaign/comparison.json')
    manuscript = ROOT / 'paper/deadline_resolution_extension.md'; text = manuscript.read_text()
    require(all(v30['primary_gates'].values()) and all(v31['gates'].values()), 'Prospective positive gates changed')
    require(nginx['status']=='verified_complete_accuracy_not_supported', 'Adverse transfer status changed')
    groups = tables(text); require(len(groups)==7, 'Expected seven scientific tables')
    expected=[[[p, traffic, str(v30['profiles'][p]['offers']//v30['profiles'][p]['trials'])]
               for p,traffic in [('A','Steady 4 requests/s'),('B','Steady 18 requests/s'),
                                 ('C','Repeated 1 s at 4 requests/s, then 1 s at 42 requests/s')]]]
    expected.append([[quota+', '+work, f"{v29['contexts'][key]['methods']['busy']['capacity_rps']:.3f}",
                      f"{v29['contexts'][key]['methods']['busy']['mae_pp']:.3f}"]
                     for key,quota,work in [('q050_small','50% CPU','44000 iterations'),
                                           ('q025_small','25% CPU','44000 iterations'),
                                           ('q050_large','50% CPU','88000 iterations'),
                                           ('q025_large','25% CPU','88000 iterations')]])
    expected.append([[traffic, f"{v30['profiles'][p]['observed_mean_miss_pct']:.3f}%",
                      f"{v30['profiles'][p]['predicted_miss_pct']:.3f}%", f"{v30['profiles'][p]['mae_pp']:.3f}"]
                     for p,traffic in [('A','Steady 4 requests/s'),('B','Steady 18 requests/s'),('C','Bursty profile C')]])
    expected.append([[d+' (primary)' if d=='25' else d,
                      f"{v30['secondary_deadline_mae_pp'][d]['fluid_busy']:.3f}",
                      f"{v30['secondary_deadline_mae_pp'][d]['periodic_uniform_phase_calibrated_delay']:.3f}"]
                     for d in ['10','20','25','35','50','75','100','150','500']])
    cdf=v31['deadline_grid']['joint_calibration_cdf']['10']
    expected.append([[p,str(rate),f"{cdf['per_profile'][p]['mean_observed_miss_pct']:.3f}",
                      f"{cdf['per_profile'][p]['mean_predicted_miss_pct']:.3f}",f"{cdf['per_profile'][p]['mae_pp']:.3f}"]
                     for p,rate in [('A',5),('B',11),('C',19)]])
    expected.append([[d+' (primary)' if d=='10' else d]+[f"{v31['deadline_grid'][method][d]['mae_pp']:.3f}"
                     for method in ['joint_calibration_cdf','independent_worker_response_convolution',
                                    'periodic_uniform_phase_calibrated_delay']]
                     for d in ['9','9.5','10','10.5','11','12']])
    expected.append([[rate,f"{r['observed_mean_miss_pct']:.3f}",f"{r['forecast_miss_pct']:.3f}",f"{r['mae_pp']:.3f}"]
                     for r,rate in zip(nginx['profiles'],['4','approximately 6','8'])])
    for actual,wanted in zip(groups,expected):
        require(actual[1:]==wanted, 'Manuscript table mismatch: '+str(actual[0]))
    intervals=[]
    for values,stored in [([b['improvement_pp'] for b in v30['blocks']],v30['paired_block_improvement']),
                          ([b['improvement_pp'] for b in v31['independent_blocks']],v31['paired_improvement'])]:
        mean=st.mean(values); radius=2.571*st.stdev(values)/math.sqrt(6)
        close(mean,stored['mean_pp'])
        interval=stored.get('interval_95',stored.get('model_based_95_interval'))
        for actual,wanted in zip([mean-radius,mean+radius],interval): close(actual,wanted)
        intervals.append([mean-radius,mean+radius])
    blocks=[]
    for b in range(1,7):
        errors=[e['absolute_error_pp'] for e in comparison['errors'] if e['block']==b]
        require(len(errors)==3,'Missing NGINX profile in a block'); blocks.append(st.mean(errors))
    mean=st.mean(blocks); radius=2.571*st.stdev(blocks)/math.sqrt(6)
    close(mean,nginx['mean_block_mae_pp'])
    for actual,wanted in zip([mean-radius,mean+radius],nginx['conditional_model_based_95_interval_pp']): close(actual,wanted)
    require(mean+radius>5 and comparison['status']=='full_response_prediction_accuracy_not_supported',
            'NGINX criterion/result altered')
    intervals.append([mean-radius,mean+radius])
    for block in v31['independent_blocks']:
        for method,key in [('joint_calibration_cdf','cdf_mae_pp'),('periodic_uniform_phase_calibrated_delay','periodic_mae_pp')]:
            errors=[e['absolute_error_pp'] for e in v31['deadline_grid'][method]['10']['errors'] if e['block']==block['block']]
            close(st.mean(errors),block[key])
        close(block['periodic_mae_pp']-block['cdf_mae_pp'],block['improvement_pp'])
    for stage in v31['stage_totals'].values():
        require(stage['misses']==sum(stage[k] for k in ['unsuccessful','computation_certainly_after',
                'computation_certainly_within_but_client_missed','computation_boundary_ambiguous']), 'Stage counts do not conserve misses')
    from finalize_deadline_extension import figure_data, latex
    data=figure_data(); require(data==json.loads((OUT/'figure_data.json').read_text()),'Figure values changed')
    require(latex(text,data)==(ROOT/'paper/deadline_resolution_extension.tex').read_text(), 'LaTeX differs from manuscript derivation')
    phrases=['79.203 pp burst error','independent convolution is better at',
             'does not propagate calibration uncertainty','scientific novelty remains a candidate',
             'not an identified processing stage','All trials, the original primary deadline and the original gate',
             'No universal deadline/period boundary','Maximum individual CDF trial error is 5.055 pp']
    flat=re.sub(r'\s+',' ',text)
    for phrase in phrases: require(phrase in flat,'Missing scope/adverse-result statement: '+phrase)
    links=0
    for rel in ['paper/deadline_resolution_extension.md','paper/deadline_resolution_supporting_material.md',
                'paper/deadline_resolution_reproducibility.md']:
        doc=ROOT/rel
        for target in re.findall(r'\]\(([^)]+)\)',doc.read_text()):
            if target.startswith(('https://','http://','#')): continue
            file=(doc.parent/target.split('#')[0]).resolve()
            if file==OUT/'report.json' and not file.exists(): continue
            require(file.exists(),'Broken local link: '+str(file)); links+=1
    return dict(status='saved_evidence_and_documents_verified',scientific_table_rows=sum(map(len,expected)),
                primary_intervals_recomputed=intervals,v31_blocks_recomputed=6,
                stage_conservation_checked=True,figure_values_reconciled=True,latex_derivation_checked=True,
                scope_statements_checked=len(phrases),local_links_checked=links,
                fresh_raw_campaign_replay_performed=False,new_collection=False,new_model_fit=False,
                novelty_established=False,independent_hardware_replication=False)


def main():
    require((OUT/'evidence-seal.json').exists(),'Finalization package not yet sealed')
    verify_seal(OUT/'evidence-seal.json')
    for name,expected in json.loads((OUT/'protected_evidence_sha256.json').read_text()).items():
        require(sha(ROOT/name)==expected,'Protected input changed: '+name)
    result=audit(); print(json.dumps(result,indent=2))


if __name__=='__main__': main()
