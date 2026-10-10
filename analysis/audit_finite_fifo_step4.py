"""Audit frozen Step 4 input selection, both result batches and old evidence."""
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import sys

import z3
from compare_finite_fifo_step4 import CONFIGS, FAMILIES, generate, write_new
from finite_fifo_deadline_reference import Problem, replay, solve
from finite_fifo_deadline_shortcut import solve_shortcut
from finite_fifo_deadline_admission import solve_admission

REPO = Path(__file__).resolve().parent.parent
ROOT = REPO/'analysis/runtime_io_fifo_hardcases_step4'
ORIGINAL = ROOT/'20261008-01'
CONFIRM = ROOT/'20261008-02-confirmation'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    design = json.loads((ORIGINAL/'design.json').read_text())
    selection = json.loads((ORIGINAL/'selection.json').read_text())
    for name in ('protocol.json', 'selection.json', 'design.json'):
        assert (ORIGINAL/name).read_bytes() == (CONFIRM/name).read_bytes()
    assert digest(ORIGINAL/'protocol.json') == design['protocol_sha256']
    assert digest(ORIGINAL/'selection.json') == design['selection_sha256']
    for name, expected in design['source_sha256'].items():
        assert digest(REPO/'analysis'/name) == expected
    groups = defaultdict(list)
    for row in selection['pool']:
        groups[row['stratum']].append(row)
        p = Problem.from_json(row['problem'])
        family = next(f for f in FAMILIES if row['stratum'].startswith(f+'_'))
        config = next(c for c in CONFIGS if row['stratum'].endswith('_'+c))
        ci = list(CONFIGS).index(config)
        regenerated = Problem(generate(family, len(p.arrivals), ci, row['trial']), **CONFIGS[config])
        assert regenerated.to_json() == row['problem']
        sc = solve_shortcut(p)
        for key in ('proved_lower_count', 'proved_upper_count', 'sampled_minimum_count', 'sampled_maximum_count'):
            assert sc[key] == row[key]
        assert sc['status'] == row['shortcut_status']
        rejections = [replay(p, s)['rejected'] for s in row['probe_service_times']]
        assert rejections == row['probe_rejected_counts']
        assert row['eligible'] == (sc['status']=='undetermined' and max(rejections)>0)
    assert len(groups) == 24 and len(selection['pool']) == 1200
    for rows in groups.values():
        assert [r['trial'] for r in rows] == list(range(50))
        expected = next(r['trial'] for r in rows if r['eligible'])
        assert [r['trial'] for r in rows if r['selected']] == [expected]
    assert {c['id'] for c in design['cases']} == set(groups)
    batches = []
    baseline_counts = None
    for root in (ORIGINAL, CONFIRM):
        rows = [json.loads(line) for line in (root/'runs.jsonl').read_text().splitlines()]
        assert len(rows)==216
        assert [(r['case'],r['method'],r['repeat']) for r in rows] == [tuple(j) for j in design['order']]
        assert len({(r['case'],r['method'],r['repeat']) for r in rows})==216
        counts={}
        for case in design['cases']:
            assert json.loads((root/'inputs'/(case['id']+'.json')).read_text())==case['problem']
            vals={(r['minimum_failures'],r['maximum_failures']) for r in rows
                  if r['case']==case['id'] and r['status']=='exact'}
            assert len(vals)==1
            counts[case['id']]=next(iter(vals))
        if baseline_counts is None: baseline_counts=counts
        assert counts==baseline_counts
        assert all(r['witnesses_verified'] for r in rows if r['status']=='exact')
        summary=json.loads((root/'comparison.json').read_text())
        assert summary['design_sha256']==digest(root/'design.json')
        batches.append(dict(package=root.name,runs=len(rows),completions=summary['completions'],
            incomplete_runs=summary['incomplete_runs'],candidate_faster_cases=summary['candidate_faster_cases'],
            candidate_at_least_2x_cases=summary['candidate_at_least_2x_cases'],
            practical_gate_passed=summary['practical_gate_passed']))
    examples = ORIGINAL/'examples'
    examples.mkdir()
    for case_id,label in [('mixed_gaps_16_small_buffer','missed_maximum'),
                          ('clustered_16_larger_buffer','missed_minimum')]:
        case=next(c for c in design['cases'] if c['id']==case_id)
        p=Problem.from_json(case['problem'])
        candidate=solve_admission(p)
        reference=solve(p)
        assert tuple(candidate[k]['failures'] for k in ('minimum','maximum'))==baseline_counts[case_id]
        assert tuple(reference[k]['failures'] for k in ('minimum','maximum'))==baseline_counts[case_id]
        write_new(examples/(label+'_input.json'),p.to_json())
        write_new(examples/(label+'_candidate.json'),candidate)
        write_new(examples/(label+'_reference.json'),reference)
        write_new(examples/(label+'_shortcut.json'),solve_shortcut(p))
    protected=json.loads((REPO/'analysis/runtime_io_paper_consolidation_review/20261008/protected_evidence_sha256.json').read_text())
    failures=[name for name,expected in protected.items() if digest(REPO/name)!=expected]
    assert not failures
    old_seals=[]
    for path in ['runtime_io_deadline_guard_exploration/20261008-review',
                 'runtime_io_originality_review/20261008-01',
                 'runtime_io_fifo_reference/20261008-01',
                 'runtime_io_fifo_smt_baseline/20261008-01',
                 'runtime_io_fifo_admission_step3/20261008-01']:
        root=REPO/'analysis'/path
        seal=json.loads((root/'seal.json').read_text())
        for name,expected in seal['files_sha256'].items():
            assert digest(root/name)==expected, (path,name)
        old_seals.append(dict(package=path,sealed_files_verified=len(seal['files_sha256']),
                              seal_sha256=digest(root/'seal.json')))
    prior=json.loads((REPO/'analysis/runtime_io_fifo_admission_step3/20261008-01/review_report.json').read_text())
    for name,expected in prior['source_files_sha256'].items():
        assert digest(REPO/name)==expected
    historical={
        'docs/runtime_io_short_working_draft_v4.md':'d5418476bbf8bee996c1da0372f1ac9ba096c0569c288c6f051e406a8884058c',
        'docs/runtime_io_load_dependent_baseline_assessment_20261008.md':'defd85ea1cefd04bda9b45d7fde9693e49e2bce6eeaabd9bc3f8be14c6092df5'}
    for name,expected in historical.items(): assert digest(REPO/name)==expected
    tests=[]
    for kind in ('admission','shortcut'):
        raw=Path('/tmp/fifo-step4-'+kind+'-tests.log').read_text()
        assert raw.rstrip().endswith('OK')
        with (ORIGINAL/(kind+'_verification.log')).open('x') as out: out.write(raw)
        tests.append(dict(command=f'/tmp/fifo-step2-venv/bin/python3 -m unittest discover -s analysis -p test_finite_fifo_deadline_{kind}.py -v',
            exit_code=0,log=kind+'_verification.log'))
    for kind,src in [('original','/tmp/fifo-step4-progress.log'),
                     ('confirmation','/tmp/fifo-step4-confirmation-progress.log')]:
        with (ORIGINAL/(kind+'_progress.log')).open('x') as out:
            out.write(Path(src).read_text())
    write_new(ORIGINAL/'audit.json',dict(schema=1,created_utc=datetime.now(timezone.utc).isoformat(),
        pool_candidates_regenerated=1200,shortcut_and_rejection_selection_verified=True,
        first_eligible_selection_verified=True,frozen_source_hashes_verified=True,
        identical_frozen_design_in_both_batches=True,all_completed_extrema_agree_between_batches=True,
        batches=batches,total_timed_runs=432,extra_reference_examples=2,
        protected_files_verified=len(protected),protected_mismatches=[],old_seals=old_seals,
        step3_source_files_verified=len(prior['source_files_sha256']),historical_sha256=historical,
        tests=tests,environment=dict(python=sys.version,z3=z3.get_version_string(),
                                    executable=sys.executable,platform=platform.platform()),
        scientific_collection_launched=False,novelty_established=False))
    print(json.dumps(dict(batches=batches,protected_files_verified=len(protected),old_seals=old_seals)))


if __name__=='__main__': main()
