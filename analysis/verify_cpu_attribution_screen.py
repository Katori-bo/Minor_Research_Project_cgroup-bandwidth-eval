"""Independent arithmetic/report/hash checks; never execute the workload."""
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'analysis/runtime_io_cpu_attribution_novelty_screen/20261008'


def read(p):
    return json.loads(p.read_text())


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def equal(a, b):
    assert math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-12), (a, b)


def main():
    design = OUT / 'design'
    expected = read(design / 'seal.json')
    assert expected == {p.name: sha(p) for p in design.iterdir() if p.name != 'seal.json'}
    protected = read(ROOT / 'analysis/runtime_io_paper_consolidation_review/20261008/protected_evidence_sha256.json')
    other = read(design / 'preserved_sha256.json')
    for rel, digest in {**protected, **other}.items():
        assert sha(ROOT / rel) == digest, rel
    plan = read(design / 'plan.json')
    audit = read(OUT / 'evidence_audit.json')
    data = {k: read(ROOT / rel) for k, rel in plan['inputs'].items()}
    for name in ['v25', 'v27']:
        rows = [r for r in data[name]['trial_accounting'] if r['counter_probe']]
        assert len(rows) == audit[name]['sampler_on_trials'] == 8
        assert all(r['phases']['busy']['state_eligible'] for r in rows)
        for index, fn in [(0, min), (1, max)]:
            equal(audit[name]['busy_consumed_cpu_fraction_envelope'][index],
                  fn(r['phases']['busy']['cpu_delta_bounds']['usage_usec'][index] /
                     (r['phases']['busy']['duration_sec'] * 1_000_000) for r in rows))
    for size in ['small', 'large']:
        rows = [r for r in data['leads']['trials'] if r['size'] == size]
        summary = audit['v25']['conditional_accounting'][size]
        assert summary['qualified_low_states'] == sum(r['low_state_eligible'] for r in rows) == 0
        equal(summary['system_difference_share_max_upper'], max(
            r['low_minus_busy_system_cost_usec_bounds'][1] / r['low_minus_busy_total_cost_usec_bounds'][0] for r in rows))
        equal(summary['edge_cpu_share_max_upper'], max(
            (r['before_first_offer_cpu_usec_bounds'][1] + r['after_arrivals_through_measurement_stop_cpu_usec_bounds'][1]) /
            r['excess_over_all_jobs_at_busy_aggregate_cost_usec_bounds'][0] for r in rows))
        assert summary['all_edge_cpu_insufficient_for_reference_excess']
    assert audit['v27']['original_decision'] == data['v27']['result']['decision'] == 'composition_inconclusive'
    for level, summary in audit['v27']['sampler_contrasts'].items():
        for metric, item in summary.items():
            original = data['v27']['result']['by_sampler'][level][metric]
            assert item == {k: original[k] for k in item}
    equal(audit['v28']['idle_consumed_cpu_fraction'], data['v28']['calibration']['idle_cpu_rate'])
    for method, row in audit['v28']['methods'].items():
        errors = data['v28']['result']['methods'][method]['errors']
        equal(row['deadline_mae_pp'], sum(abs(e['deadline_error_pp']) for e in errors) / len(errors))
        equal(row['capacity_rps'], data['v28']['calibration']['methods'][method]['capacity_rps'])
    checks = read(OUT / 'offline_checks.json')
    for row in checks['closed_cohort_aggregate_allocations']:
        equal(row['request_user'] + row['request_system'] + row['shared_user'], row['cgroup_cpu_sec'])
        equal((row['request_user'] + row['request_system']) / row['completed'], row['request_cpu_sec_per_job'])
        equal(row['request_user'] + row['shared_user'], 3.8)
        equal(row['request_system'], .2)
    assert {r['request_cpu_sec_per_job'] for r in checks['closed_cohort_aggregate_allocations']} == {.003, .004}
    fit = checks['ordinary_additive_fit']
    equal(fit['fitted_request_cpu_sec'], .003)
    equal(fit['fitted_constant_background_cpu_fraction'], .1)
    for n, u in zip(fit['counts'], fit['cpu_sec']):
        equal(fit['fitted_request_cpu_sec']*n + fit['fitted_constant_background_cpu_fraction']*fit['wall_sec'], u)
    for row in checks['load_proportional_background_confounding_even_with_idle']:
        n, t = row['completed'], row['wall_sec']
        equal(.003*n + .01*t + .001*n, row['both_cpu_sec'])
        equal(.004*n + .01*t, row['both_cpu_sec'])
    for row in checks['throughput_alone_confounds_cost_and_consumption']:
        equal(row['consumed_cpu_fraction'], row['throughput_rps']*row['request_cpu_sec'])
    assert {r['consumed_cpu_fraction'] for r in checks['throughput_alone_confounds_cost_and_consumption']} == {.4, .5}
    for row in checks['equal_elapsed_different_cpu']:
        assert row['on_cpu_ms'] + row['off_cpu_ms'] == row['elapsed_ms'] == 10
    assert {r['on_cpu_ms'] for r in checks['equal_elapsed_different_cpu']} == {4, 10}
    assessment = read(OUT / 'assessment.json')
    assert assessment['decision'] == checks['decision'] == 'stop_custom_method_and_collection_at_this_gate'
    assert not assessment['novelty_established'] and not assessment['fresh_collection'] and not assessment['paper_modified']
    assert assessment['protected_scientific_files'] == len(protected) == 1911
    assert assessment['additional_preserved_files'] == len(other) == 233
    receipt = {'status': 'pass', 'screen': 4, 'arithmetic_check_families': 5,
               'v25_sampler_on_trials_audited': 8, 'v27_sampler_on_trials_audited': 8,
               'v28_method_maes_recomputed': 5, 'protected_scientific_files': len(protected),
               'additional_preserved_files': len(other), 'design_seal_verified': True,
               'published_algorithms_executed': False, 'new_collection': False,
               'verifier_sha256': sha(Path(__file__))}
    (OUT / 'verification.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
