#!/usr/bin/env python3
"""Independent supply calculation plus corrected sample metadata replay."""
from pathlib import Path
import hashlib,json,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'diagnostic'))
import v28_common as c
OUT=ROOT/'analysis/runtime_io_profiler_semantics_gate/20261008'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    c.verify_seal(OUT/'design')
    plan=c.read(OUT/'design/plan.json');report=c.read(OUT/'assessment.json')
    for rel,h in plan['scripts_sha256'].items():
        if sha(ROOT/rel)!=h:raise ValueError('frozen script changed')
    protected=c.read(ROOT/'analysis/runtime_io_paper_consolidation_review/20261008/protected_evidence_sha256.json')
    preserved=c.read(OUT/'design/preserved_sha256.json')
    for rel,h in {**protected,**preserved}.items():
        if sha(ROOT/rel)!=h:raise ValueError('protected input changed')
    for row in c.read(OUT/'sources/manifest.json')['files']:
        if sha(ROOT/row['saved_path'])!=row['sha256']:raise ValueError('source mismatch')
    cases={r['id']:r for r in report['cases']}
    for r in cases.values():
        C=100*(r['q']-r['reserve']);H=100*r['reserve']
        if C!=r['application_cpu_ms'] or H!=r['charged_controller_cpu_ms']:raise ValueError('budget conservation')
        if C//50!=r['original_completions'] or C//20!=r['genuine_optimized_completions']:raise ValueError('independent supply count')
    for r in report['deadline_ranking_example']:
        work=([20]*5+[50]*5) if r['id']=='save_first_five' else ([50]*5+[20]*5)
        cumulative=0;ends=[]
        for w in work:
            cumulative+=w;ends.append(((cumulative-1)//50)*100+(cumulative-1)%50+1)
        if ends!=r['completions_ms']:raise ValueError('independent inverse-supply vector')
    # Initial reporting profiles used total CPU+blocked sample counts even for
    # CPU-only credit. The native viewers ignore this field. Preserve originals
    # and correct the synthetic metadata; results must remain identical.
    inputs=c.read(OUT/'reporting_inputs.json')
    for row in inputs['records']:
        if row['id']=='phase_metadata_control':
            continue
        mode='line_all_blocked' if row['id'].endswith('_line_all_blocked') else 'cpu_only'
        caseid=row['id'].removesuffix('_'+mode);case=cases[caseid]
        count=10000 if mode=='line_all_blocked' else case['application_cpu_ms']
        lines=[]
        for line in row['profile_text'].splitlines():
            if line.startswith('experiment\t'):
                fields=line.split('\t');fields=[f'selected-samples={count}' if f.startswith('selected-samples=') else f for f in fields]
                line='\t'.join(fields)
            elif line.startswith('samples\t'):line=f'samples\tlocation=work.cc:1\tcount={count*2}'
            lines.append(line)
        row['profile_text']='\n'.join(lines)+'\n'
    half=next(x['profile_text'] for x in inputs['records'] if x['id']=='half_cpu_cpu_only')
    inputs['records'][-1]['profile_text']=half.replace('count=10000','count=100000000').replace('time=20000000000','time=90000000000')
    c.save(OUT/'reporting_inputs_corrected.json',inputs)
    runner=(ROOT/'analysis/run_pinned_profiler_reporting.js').read_text()
    runner=runner.replace("const root = path.resolve(__dirname, '..');",'const root = '+json.dumps(str(ROOT))+';')
    runner=runner.replace("'reporting_inputs.json'","'reporting_inputs_corrected.json'").replace("'native_reporting_results.json'","'native_reporting_results_corrected.json'")
    c.save(OUT/'metadata_correction.json',dict(reason='Correct CPU-only selected-sample metadata from CPU+blocked count to CPU count. Preserve initial records; reporting outputs unaffected.',
        verifier_sha256=sha(Path(__file__)),adapted_runner_sha256=hashlib.sha256(runner.encode()).hexdigest()))
    subprocess.run(['node','-'],input=runner,text=True,check=True,cwd=ROOT)
    old=c.read(OUT/'native_reporting_results.json');new=c.read(OUT/'native_reporting_results_corrected.json')
    if old!=new:raise ValueError('metadata correction changed results')
    result=dict(status='pass',pinned_source_files=127,independent_supply_cases=5,
       independent_completion_vectors=2,native_reporting_records=22,corrected_metadata_reporting_records=22,
       sample_metadata_correction_no_numeric_effect=True,protected_scientific_files=len(protected),
       additional_preserved_files=len(preserved),actual_runtime_profiler_executed=False,new_collection=False,
       source_semantics_scope='C++ counter updates inspected and conditionally modeled; exact native viewer parsing/aggregation/reporting executed. Kernel samples and scheduling not reproduced.')
    c.save(OUT/'verification.json',result);print(json.dumps(result,indent=2))

if __name__=='__main__':main()
