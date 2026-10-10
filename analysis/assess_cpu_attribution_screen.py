"""Fourth bounded screen: saved-accounting audit and declared algebraic witnesses.

No service execution, instrumentation, Linux simulation, or published estimator
implementation. Run with python3 -B to avoid caches in preserved directories.
"""
import hashlib
import json
from fractions import Fraction as F
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'analysis/runtime_io_cpu_attribution_novelty_screen/20261008'
INPUTS = {
    'v25': 'analysis/runtime_io_v25/generation-01/analysis/1791389865386770727/report.json',
    'leads': 'analysis/runtime_io_v25_contribution_leads/20261007/report.json',
    'v27': 'analysis/runtime_io_v27/generation-03/analysis/1791429220799564493/report.json',
    'v28': 'analysis/runtime_io_v28/generation-01/analysis/1791438579821212637/report.json',
    'details': 'analysis/runtime_io_capacity_state_details/20261007/report.json',
}


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def read(p):
    return json.loads(p.read_text())


def save(p, value):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def check_preserved():
    protected = read(ROOT / 'analysis/runtime_io_paper_consolidation_review/20261008/protected_evidence_sha256.json')
    other = read(OUT / 'design/preserved_sha256.json')
    for rel, expected in {**protected, **other}.items():
        if sha(ROOT / rel) != expected:
            raise ValueError('Preserved input changed: ' + rel)
    return len(protected), len(other)


def prepare():
    if (OUT / 'design').exists():
        raise ValueError('Do not overwrite an existing screen design')
    previous = ROOT / 'analysis/runtime_io_profiler_semantics_gate/20261008'
    preserved = read(previous / 'design/preserved_sha256.json')
    for p in previous.rglob('*'):
        if p.is_file():
            preserved[str(p.relative_to(ROOT))] = sha(p)
    more = list(INPUTS.values()) + [
        'docs/runtime_io_profiler_semantics_gate_20261008.md',
        'docs/runtime_io_short_working_draft_v5.md',
        'docs/runtime_io_paper_supporting_material_20261008.md',
        'diagnostic/completion_service.go',
        'analysis/runtime_io_paper_consolidation_review/20261008/protected_evidence_sha256.json',
        str(Path(__file__).relative_to(ROOT)),
    ]
    for rel in more:
        preserved[rel] = sha(ROOT / rel)
    for rel in ['README.md', 'docs/current_research_plan.md', 'docs/runtime_io_research_status_20261008.md']:
        p = OUT / 'provenance/status_before' / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes((ROOT / rel).read_bytes())
    save(OUT / 'design/preserved_sha256.json', preserved)
    save(OUT / 'design/plan.json', {
        'date': '2026-10-08', 'screen_number': 4,
        'question': 'Distinguish increased request CPU, additional runtime/background CPU, and reduced CPU delivery sufficiently to choose a remedy.',
        'inputs': INPUTS,
        'scope': 'Retrospective offline accounting and conditional algebra; no fresh performance data or estimator benchmark.',
        'checks': ['Separate consumption from supplied opportunity', 'Aggregate request/background ambiguity',
                   'Ordinary additive identification and its load-dependent confounding', 'Timing is not CPU attribution'],
        'proceed_gate': 'Concrete additional identification or remedy-ranking mechanism, with a measurable advantage over adequate ordinary attribution at matched accuracy/cost.',
        'stop_gate': 'Only missing labels, ordinary regression/profiling, or an assumption-boundary illustration emerges.',
        'collection': 'stopped', 'quota_period_selection': 'on_hold', 'fifo_theorem': 'closed',
        'prior_inventory_caveat': 'Previously recorded unsealed calibration-cost __pycache__ remains untouched; this screen preserves hashes and does not repair/reseal old roots.',
    })
    save(OUT / 'design/seal.json', {p.name: sha(p) for p in (OUT / 'design').iterdir() if p.name != 'seal.json'})
    check_preserved()


def assess():
    protected_count, other_count = check_preserved()
    data = {k: read(ROOT / rel) for k, rel in INPUTS.items()}
    evidence = {}
    for k in ['v25', 'v27']:
        rows = [r for r in data[k]['trial_accounting'] if r['counter_probe']]
        bounds = [r['phases']['busy']['delivered_cpu_fraction_bounds'] for r in rows]
        evidence[k] = {'sampler_on_trials': len(rows),
                       'all_busy_states_eligible': all(r['phases']['busy']['state_eligible'] for r in rows),
                       'busy_consumed_cpu_fraction_envelope': [min(b[0] for b in bounds), max(b[1] for b in bounds)]}
    evidence['v25']['conditional_accounting'] = {}
    for size in ['small', 'large']:
        rows = [r for r in data['leads']['trials'] if r['size'] == size]
        summary = {
            'trials': len(rows), 'qualified_low_states': sum(r['low_state_eligible'] for r in rows),
            'user_cost_difference_min_lower_usec': min(r['low_minus_busy_user_cost_usec_bounds'][0] for r in rows),
            'system_difference_share_max_upper': max(r['system_share_of_cost_difference_upper'] for r in rows),
            'edge_cpu_share_max_upper': max(r['all_edge_cpu_over_excess_upper'] for r in rows),
            'all_edge_cpu_insufficient_for_reference_excess': all(r['all_edge_cpu_smaller_than_reference_excess'] for r in rows),
        }
        evidence['v25']['conditional_accounting'][size] = summary
    evidence['v27']['original_decision'] = data['v27']['result']['decision']
    evidence['v27']['sampler_contrasts'] = {}
    for level, row in data['v27']['result']['by_sampler'].items():
        evidence['v27']['sampler_contrasts'][level] = {
            k: {a: row[k][a] for a in ['midpoint_mean', 'model_based_95_interval', 'screen_pass']}
            for k in ['whole_cpu_usec_per_job', 'busy_capacity_rps']}
    cal = data['v28']['calibration']
    evidence['v28'] = {
        'original_decision': data['v28']['result']['decision'],
        'idle_consumed_cpu_fraction': cal['idle_cpu_rate'],
        'methods': {k: {'capacity_rps': cal['methods'][k]['capacity_rps'],
                        'deadline_mae_pp': v['deadline_mae_pp'], 'original_accuracy_pass': v['accuracy_pass']}
                    for k, v in data['v28']['result']['methods'].items()},
    }
    evidence['limits'] = data['details']['limitations']
    save(OUT / 'evidence_audit.json', evidence)

    # CPU seconds, ten wall seconds, 1000 completed requests; closed cohort,
    # no carry-in/out. These are illustrative allocations, not measured worlds.
    worlds = [dict(name='request_cost', request_user=F(38, 10), request_system=F(2, 10), shared_user=F(0)),
              dict(name='shared_cost', request_user=F(28, 10), request_system=F(2, 10), shared_user=F(1))]
    aggregates = [(w['request_user'] + w['shared_user'], w['request_system']) for w in worlds]
    assert aggregates[0] == aggregates[1] == (F(38, 10), F(2, 10))
    allocation_rows = [{**{k: float(v) if isinstance(v, F) else v for k, v in w.items()},
                        'wall_sec': 10, 'completed': 1000,
                        'request_cpu_sec_per_job': float((w['request_user'] + w['request_system']) / 1000),
                        'cgroup_cpu_sec': float(sum(aggregates[i]))} for i, w in enumerate(worlds)]
    # Distinct observed N/T identifies c,h only under U = c*N + h*T.
    n1, n2, t = F(100), F(1000), F(10)
    c, h = F(3, 1000), F(1, 10)
    u1, u2 = c*n1+h*t, c*n2+h*t
    fitted_c = (u2-u1)/(n2-n1)
    fitted_h = (u1-fitted_c*n1)/t
    assert fitted_c == c and fitted_h == h
    proportional = []
    for n in [0, 100, 500, 1000]:
        ua = F(3, 1000)*n + F(1, 100) * t + F(1, 1000)*n
        ub = F(4, 1000)*n + F(1, 100) * t
        assert ua == ub
        proportional.append({'completed': n, 'wall_sec': 10, 'both_cpu_sec': float(ua)})
    delivery = [{'consumed_cpu_fraction': .5, 'request_cpu_sec': .005, 'throughput_rps': 100},
                {'consumed_cpu_fraction': .4, 'request_cpu_sec': .004, 'throughput_rps': 100}]
    assert all(F(str(r['consumed_cpu_fraction'])) / F(str(r['request_cpu_sec'])) == 100 for r in delivery)
    timing = [{'on_cpu_ms': 4, 'off_cpu_ms': 6, 'elapsed_ms': 10},
              {'on_cpu_ms': 10, 'off_cpu_ms': 0, 'elapsed_ms': 10}]
    assert all(r['on_cpu_ms'] + r['off_cpu_ms'] == r['elapsed_ms'] for r in timing)
    save(OUT / 'offline_checks.json', {
        'scope': 'Exact declared arithmetic; no identical Linux-trace claim and no reproduced profiler/estimator.',
        'closed_cohort_aggregate_allocations': allocation_rows,
        'ordinary_attribution_reference': 'Correct labeled/request CPU totals distinguish 4 ms/job from 3 ms/job and reveal 1 CPU second shared work; label accuracy and coverage are assumptions.',
        'ordinary_additive_fit': {'counts': [100, 1000], 'wall_sec': 10,
                                  'cpu_sec': [float(u1), float(u2)], 'fitted_request_cpu_sec': float(fitted_c),
                                  'fitted_constant_background_cpu_fraction': float(fitted_h)},
        'load_proportional_background_confounding_even_with_idle': proportional,
        'throughput_alone_confounds_cost_and_consumption': delivery,
        'consumption_limitation': 'U/T is used CPU, not unavailable runnable opportunity; low utilization alone cannot identify supply loss.',
        'equal_elapsed_different_cpu': timing,
        'novelty_established': False, 'new_collection': False,
        'decision': 'stop_custom_method_and_collection_at_this_gate',
    })
    p, q = check_preserved()
    save(OUT / 'assessment.json', {'screen': 4, 'decision': 'stop_custom_method_and_collection_at_this_gate',
          'novelty_established': False, 'additional_capability_demonstrated': False,
          'reason': 'The sparse evidence does not identify components; richer ordinary attribution is an adequate reference under declared assumptions. No nonroutine mechanism for less-information remedy selection emerged.',
          'protected_scientific_files': p, 'additional_preserved_files': q,
          'fresh_collection': False, 'published_algorithms_reproduced': False,
          'paper_modified': False, 'script_sha256': sha(Path(__file__))})
    print(json.dumps({'decision': 'stop', 'protected_scientific_files': p, 'additional_preserved_files': q,
                      'v25_busy_consumption': evidence['v25']['busy_consumed_cpu_fraction_envelope'],
                      'v27_busy_consumption': evidence['v27']['busy_consumed_cpu_fraction_envelope']}))


if __name__ == '__main__':
    import sys
    if len(sys.argv) == 2 and sys.argv[1] == 'prepare':
        prepare()
    elif len(sys.argv) == 2 and sys.argv[1] == 'assess':
        assess()
    else:
        raise SystemExit('Usage: python3 -B analysis/assess_cpu_attribution_screen.py prepare|assess')
