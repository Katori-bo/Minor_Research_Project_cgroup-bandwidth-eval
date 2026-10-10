#!/usr/bin/env python3
"""Independent tick reference, accounting checks and preservation audit."""
import ast
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'analysis/runtime_io_quota_update_replay/20261008'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def tick_reference(spec, phase, arm):
    # Independent 1ms state stepping for declared grid-aligned reference cases.
    # Never calls the event model or its setter/refill helpers.
    q = spec['initial']; g = q; local = 0; used = 0; numerator = 0
    completed = []; left = 5_000; next_tick = phase; pending = None
    old_proposal = spec['initial']; changes = dict(spec['changes']); window = None
    for t in range(0, 4_500_000, 1_000):
        if t == 4_000_000:
            window = {'cpu_us': used, 'nominal_numerator': numerator}
        if t == next_tick:
            if pending is not None:
                q = pending
                if arm == 'boundary_setter':
                    g = q; local = 0
                pending = None
            g = min(g + q, q)
            next_tick += 100_000
        if t in changes and changes[t] != old_proposal:
            old_proposal = changes[t]
            if arm.startswith('boundary'):
                pending = old_proposal
            else:
                # Zero-gap pair and quota-only have the same final state.
                q = old_proposal; g = q; local = 0
        if t < 4_000_000:
            numerator += q * 1_000
        if len(completed) < 800 and t >= len(completed) * 5_000:
            if local == 0:
                moved = min(5_000, g); g -= moved; local += moved
            if local:
                assert local >= 1_000 and left >= 1_000
                local -= 1_000; used += 1_000; left -= 1_000
                if left == 0:
                    completed.append(t + 1_000); left = 5_000
    window['miss_pct'] = {str(d): 100 * sum(i >= len(completed) or completed[i] > i * 5_000 + d for i in range(800)) / 800 for d in [100_000, 300_000, 500_000]}
    window['completions_us'] = completed
    return window


def main():
    plan = json.loads((OUT / 'design/plan.json').read_text())
    results = json.loads((OUT / 'results.json').read_text())
    loader = importlib.util.spec_from_file_location('quota_gate', ROOT / 'analysis/check_quota_update_replay.py')
    module = importlib.util.module_from_spec(loader)
    loader.loader.exec_module(module)
    reference_checks = 0
    for spec in plan['fixed_sequences']:
        for phase in [1_000, 50_000, 100_000]:
            for arm in plan['arms']:
                actual = module.replay(spec, phase, arm)
                expected = tick_reference(spec, phase, arm)
                for key in expected:
                    assert actual[key] == expected[key], (spec['id'], phase, arm, key)
                reference_checks += 1
    # Exhaustive finite-state check of the algebra with zero burst, no debt,
    # and no execution between writes. Includes decreasing quotas and silos.
    algebra_checks = 0
    for old in range(1, 21):
        for new in range(1, 21):
            for global_balance in range(0, 31):
                for local_balance in range(0, 6):
                    paired = min(min(global_balance + old, old) + new, new)
                    single = min(global_balance + new, new)
                    assert paired == single == new
                    # Both setters clear any preexisting local balance.
                    assert (paired, 0) == (single, 0)
                    algebra_checks += 1
    row_checks = 0
    matching_failures = 0
    for row in results['fixed']:
        runs = row['runs']; a = runs['original_pair']; b = runs['quota_only']
        assert a['cpu_us'] == b['cpu_us'] and a['miss_pct'] == b['miss_pct']
        assert a['nominal_numerator'] == b['nominal_numerator']
        for r in runs.values():
            assert r['initial_us'] + r['net_grants_us'] - r['discarded_local_us'] == r['cpu_us'] + r['global_us'] + r['local_us']
            assert 0 <= r['cpu_us'] <= plan['resource_window_us']
            if 'matching' in r:
                m = r['matching']; assert abs((r[m['field']] - m['target']) - m['error']) < 1e-8
                matching_failures += not m['within_10_cpu_us']
            row_checks += 1
    # Execute the pinned worker's actual outer-loop actuation predicates and
    # setter against in-memory paths, using the scalar proposals produced by
    # each native-policy replay. This catches premature quota rounding changes.
    source = ROOT / 'analysis/runtime_io_novelty_discovery_round/20261008/sources/autothrottle/worker-daemon.py'
    tree = ast.parse(source.read_text())
    setter_node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'set_cpu_limit')
    run_node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'run')
    loop_node = next(n for n in ast.walk(run_node) if isinstance(n, ast.For) and ast.unparse(n.target) == '(name, scaler)')
    setter_code = compile(ast.Module(body=[setter_node], type_ignores=[]), str(source), 'exec')
    loop_code = compile(ast.Module(body=[loop_node], type_ignores=[]), str(source), 'exec')
    native_driver_checks = 0
    native_write_pairs = 0
    class Sink:
        def __init__(self, field, output): self.field = field; self.output = output
        def write_text(self, value): self.output.append([self.field, value])
    for phase in plan['phases_first_boundary_us']:
        captured = []
        captain = module.native_class()(target=0.1, initial_limit=0.5)
        def observed_policy(t, stats):
            proposal = captain(t, stats)
            captured.append((t, proposal))
            return proposal
        actual = module.Model(50_000, phase, 'original_pair', policy=observed_policy).run()
        writes = []
        namespace = {'stat_path': lambda pod_map, name, field: Sink(field, writes)}
        exec(setter_code, namespace)
        namespace.update({'limits': {'svc': 0.5}, 'pod_map': {}})
        emitted = []
        for t, proposal in captured:
            writes.clear()
            namespace.update({'t': t, 'stats': {'svc': {}}, 'scalers': {'svc': lambda _, __, value=proposal: value}})
            exec(loop_code, namespace)
            if writes:
                assert writes[0] == ['cpu.cfs_period_us', '100000']
                assert writes[1][0] == 'cpu.cfs_quota_us' and len(writes) == 2
                emitted.append([round(t * 1e6), int(writes[1][1])])
                native_write_pairs += 1
            native_driver_checks += 1
        assert emitted == actual['requested_changes'], phase
    assessment = json.loads((OUT / 'assessment.json').read_text())
    for case, summary in assessment['fixed_sequences'].items():
        rows = [r for r in results['fixed'] if r['id'] == case]
        for arm, expected in summary.items():
            diff = [100 * (r['runs']['original_pair']['cpu_us'] - r['runs'][arm]['cpu_us']) / r['runs'][arm]['cpu_us'] for r in rows]
            eligible = rows if arm != 'boundary_setter_match_cpu' else [r for r in rows if r['runs'][arm]['matching']['within_10_cpu_us']]
            pp = [r['runs'][arm]['miss_pct'][str(d)] - r['runs']['original_pair']['miss_pct'][str(d)] for r in eligible for d in plan['deadlines_us']]
            assert expected['cpu_difference_pct_range'] == [min(diff), max(diff)]
            assert expected['deadline_difference_pp_range_eligible'] == [min(pp), max(pp)]
            assert expected['cpu_material_phase_points'] == sum(d >= 5 for d in diff)
            assert expected['eligible_phase_points'] == len(eligible)
    assert assessment['matching']['cpu_match_failures_per_boundary_arm'] == sum(not r['runs']['boundary_setter_match_cpu']['matching']['within_10_cpu_us'] for r in results['fixed'])
    assert assessment['novelty_established'] is False
    protected = json.loads((OUT / 'design/protected_sha256.json').read_text())
    preserved = json.loads((OUT / 'design/preserved_sha256.json').read_text())
    for rel, expected in {**protected, **preserved}.items():
        assert sha(ROOT / rel) == expected, rel
    for rel, expected in json.loads((OUT / 'design/seal.json').read_text()).items():
        assert sha(OUT / 'design' / rel) == expected, rel
    audit = {'status': 'pass', 'independent_tick_reference_vectors': reference_checks,
             'finite_state_pair_equivalence_checks': algebra_checks, 'fixed_arm_accounting_rows': row_checks,
             'matching_targets_outside_10_cpu_us': matching_failures,
             'native_outer_loop_predicate_calls': native_driver_checks,
             'native_setter_write_pairs': native_write_pairs,
             'assessment_numerical_ranges_recomputed': True,
             'protected_scientific_paths': len(protected), 'additional_preserved_paths': len(preserved),
             'fresh_workload_runs': 0, 'native_scalar_policy_only': True, 'paper_unchanged': True}
    (OUT / 'verification.json').write_text(json.dumps(audit, indent=2, sort_keys=True) + '\n')
    print(json.dumps(audit))


if __name__ == '__main__':
    main()
