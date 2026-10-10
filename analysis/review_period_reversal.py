#!/usr/bin/env python3
"""Audit existing V20/pilot records and collection differences, without collecting."""
import collections
import json
from pathlib import Path
import statistics as st
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'diagnostic'))
import period_cost as pc
from verify_execution_delay import verify_completion


def average(rows):
    return {k:st.mean(r[k] for r in rows) for k in rows[0]}


def normalized_client_command(argv):
    out = list(argv)
    out[0] = '<same-hash-loadgen>'
    out[out.index('-url')+1] = '<loopback-dynamic-port>/work?iterations=44000'
    out[out.index('-output')+1] = '<trial-output>'
    return out


def main():
    old, pilot = pc.BASE, pc.DEFAULT
    pm = pc.verify_preparation(pilot, current=False)
    om = pc.old.read(old / 'preparation/manifest.json')
    shared = sorted(set(pm['sources']) & set(om['sources']))
    assert len(shared) == 115
    for name in shared:
        assert pm['sources'][name] == om['sources'][name] == pc.old.digest(ROOT / name)
    original_completion = verify_completion(old)
    report_path = pilot / 'analysis/1791227322172383591'
    pc.old.verify_seal(report_path)
    report = pc.old.read(report_path / 'report.json')
    rows = []
    groups = {}
    sources = {}
    all_commands, all_limits = {}, {}
    for label, paths in [('V20', sorted((old / 'trials').glob('*/attempt-*'))),
                         ('pilot', sorted((pilot / 'trials').glob('*')))]:
        assert len(paths) == 16
        grouped = collections.defaultdict(list)
        for path in paths:
            pc.old.verify_seal(path)
            sources[str(path.relative_to(ROOT) / 'seal.json')] = pc.old.digest(path / 'seal.json')
            result = pc.old.read(path / 'derived.json')
            if label == 'pilot':
                assert pc.replay_trial(path) == result
                rows.append(result['summary'])
            summary = result['summary']
            client, server, config, obs, warm, wm, initial = (
                pc.old.read(path / name) for name in ('loadgen.json', 'server_metrics.json',
                'config.json', 'observations.json', 'warmup.json', 'warmup_server_metrics.json', 'initial.json'))
            # Independent calculations do not use the report's CPU or outcome functions.
            start, stop = (obs[k]['cpu_stat'] for k in ('measurement_start', 'measurement_stop'))
            cpu = stop['usage_usec'] - start['usage_usec']
            computed_cost = cpu / server['completed']
            expected_cost = summary['legacy_cpu_usec_per_completed_work'] if label == 'pilot' else summary['cpu_usec_per_completed_work']
            assert computed_cost == expected_cost
            timely = sum(not r['Error'] and r['StatusCode'] == 200 and r['EndToEndLatencyNs'] <= 500_000_000
                         for r in client['requests']) / client['total_scheduled']
            assert timely == summary['timely_500_fraction']
            pc.old.validate_client(client, config)
            pc.old.validate_client(warm, dict(config, duration_sec=20))
            assert pc.old.read(path / 'reset.json')['health']['completed'] == 0
            assert not server['active_handlers'] and not server['queue_len']
            assert server['completed'] == server['admitted']
            assert initial['uncapped_ancestors'] == [{'path':'/sys/fs/cgroup/system.slice','cpu_max':'max 100000'}]
            arm = summary['arm']
            commands = {name:normalized_client_command(pc.old.read(path / (name+'_argv.json')))
                        for name in ('warmup','loadgen')}
            key = (label, arm)
            all_commands.setdefault(key, commands)
            assert all_commands[key] == commands
            all_limits.setdefault(key, initial['initial_limits'])
            assert all_limits[key] == initial['initial_limits']
            # Bridge process-relative client/server clocks to host monotonic; never
            # subtract raw client_test_start_ns directly from host timestamps.
            _, mapping, _ = pc.legacy_analysis.join(client, server, config)
            host_mapping = pc.kernel_bridge_analysis.clock_join(pc.old.read(path / 'host_server_anchors.json'),
                                                                mapping, server['clock_generation'])
            client_host_start = client['client_test_start_ns'] + (
                mapping['server_minus_client_lower_ns'] + mapping['server_minus_client_upper_ns'] +
                host_mapping['kernel_minus_server_lower_ns'] + host_mapping['kernel_minus_server_upper_ns']) / 2
            warmup_cost = (start['usage_usec']-obs['startup']['cpu_stat']['usage_usec'])/wm['completed']
            group = arm if label == 'V20' else f"{summary['period_ms']}_{'on' if summary['counters'] else 'off'}"
            grouped[group].append(dict(cpu_usec_per_completed_work=computed_cost,
                user_usec_per_completed_work=(stop['user_usec']-start['user_usec'])/server['completed'],
                timely_500_fraction=timely, warmup_completed=wm['completed'],
                warmup_failures=warm['total_503']+warm['total_errors'],
                startup_to_measurement_cpu_per_warmup_computation_usec=warmup_cost,
                reset_to_client_start_ms=(client_host_start-pc.old.read(path/'reset.json')['monotonic_ns'])/1e6,
                dispatch_mean_ms=client['dispatch_lag_summary']['mean_ms'], client_missed=client['missed_arrivals'],
                nr_periods=stop['nr_periods']-start['nr_periods'], nr_throttled=stop['nr_throttled']-start['nr_throttled']))
        groups[label] = {k:dict(trial_values=v, means=average(v)) for k,v in grouped.items()}
    for arm in ('A','C'):
        assert all_commands[('V20',arm)] == all_commands[('pilot',arm)]
        assert all_limits[('V20',arm)] == all_limits[('pilot',arm)]
    assert all(report[k] == v for k,v in pc.compare(rows).items())
    script_text = (ROOT/'diagnostic/period_cost.py').read_text()
    assert script_text.index("load(20,'warmup')") < script_text.index("helper.request('attach')")
    result = dict(review='2026-10-06', shared_sources_verified=115,
        prior_completion_verified=original_completion['decision'], pilot_raw_replays_verified=16,
        independent_cpu_and_deadline_checks=32, workload_commands_and_resource_limits_match=True,
        grouped_records=groups, frozen_pilot_decision=report['decision'],
        known_collection_differences=[
            'Pilot starts a persistent root helper and four counter fixtures before initial idle; V20 does not.',
            'Counter-off still launches perf stat -n and a blocked cat process; V20 has neither.',
            'Pilot counter-control IPC extends the idle interval between reset and client start.',
            'V20 has four full-duration rehearsals and yield-on trial cells; pilot uses counter-on cells instead.',
            'V20 emits progress and reads temperature roughly every 10 seconds during load; pilot does not.',
            'Both call the same Service.observe approximately once per second; pilot also retains returned resource samples.',
            'The user supplied launch block sets Balanced explicitly and kills additional exact process names.'
        ],
        causal_explanation_established=False,
        conclusions=[
            'No frozen-source, executable, resource, arrival, raw CPU-denominator or deadline-calculation mismatch explains the reversal.',
            'The 20 ms warmup rejection/cost difference is already present before per-trial collector attachment.',
            'This limits measurement-window and attachment-only explanations, not whole-pilot-context explanations.',
            'Recorded host activity and temperatures differ, but the records cannot attribute causation.',
            'A faithful original-runner repeat is the next bounded diagnostic; do not repeat the cost pilot until it passes.'
        ], source_seals=sources,
        reviewer_sha256=pc.old.digest(Path(__file__)))
    output=ROOT/'analysis/runtime_io_period_reversal_review/20261006'
    output.mkdir(parents=True, exist_ok=True)
    pc.old.save(output/'report.json', result)
    print(json.dumps({k:result[k] for k in ('shared_sources_verified','prior_completion_verified',
        'pilot_raw_replays_verified','independent_cpu_and_deadline_checks',
        'workload_commands_and_resource_limits_match','frozen_pilot_decision')},indent=2))
    print('Audit: '+str(output/'report.json'))


if __name__ == '__main__':
    main()
