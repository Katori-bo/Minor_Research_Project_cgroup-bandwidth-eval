#!/usr/bin/env python3
"""Offline review of the completed generation-02 pilot; no collection or rerun."""
import collections
import json
from pathlib import Path
import statistics as st
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'diagnostic'))
import period_cost as pc


def read(path):
    return json.loads(path.read_text())


def host_summary(paths):
    # Includes all saved monitoring samples: warmup and arrivals. Do not call
    # snapshot clock values execution-weighted worker frequency measurements.
    samples = [s for path in paths for s in read(path / 'monitor.json')]
    duration = sum(s['process_interval_sec'] for s in samples)
    desktop = collections.defaultdict(float)
    for s in samples:
        for p in s['process_cpu_deltas']:
            if p['comm'] in ('plasmashell', 'kwin_wayland', 'baloo_file'):
                desktop[p['comm']] += p.get('cpu_delta_sec', 0)
    temperatures = [s['temps_c']['k10temp:temp1_input'] for s in samples]
    return dict(samples=len(samples), scope='all 80 saved warmup/arrival samples per trial',
        temperature_mean_c=st.mean(temperatures), temperature_min_c=min(temperatures),
        temperature_max_c=max(temperatures),
        desktop_pct_one_core={k:100*v/duration for k,v in desktop.items()},
        chatgpt_present=any(s['chatgpt_present'] for s in samples),
        cpu_util_pct={k:st.mean(s['cpu_util_pct'][k] for s in samples)
                      for k in ('cpu', 'cpu2', 'cpu3', 'cpu4', 'cpu5')})


def fixed_busy_rate(path):
    client, server, config = (read(path / name) for name in
                            ('loadgen.json', 'server_metrics.json', 'config.json'))
    _, mapping, _ = pc.legacy_analysis.join(client, server, config)
    origin = mapping['client_test_start_ns'] + (
        mapping['server_minus_client_lower_ns'] + mapping['server_minus_client_upper_ns']) / 2
    times = [(j['completion_ns'] - origin)/1e9 for j in server['events']]
    return sum(0 <= t < 60 and 6.5 <= t % 10 < 9.5 for t in times) / 18


def main():
    session = ROOT / 'analysis/runtime_io_period_cost_pilot/generation-02'
    report_path = session / 'analysis/1791227322172383591'
    manifest = pc.verify_preparation(session, current=False)
    assert all(pc.old.digest(ROOT/name) == sha for name,sha in manifest['sources'].items())
    pc.old.verify_seal(session / 'counter_fixtures')
    fixtures = pc.validate_fixtures(session / 'counter_fixtures')
    assert fixtures == read(session / 'counter_fixtures/result.json')
    pc.old.verify_seal(report_path)
    original = read(report_path / 'report.json')
    assert pc.old.digest(session / 'preparation/seal.json') == original['preparation_seal']
    assert pc.old.digest(session / 'counter_fixtures/seal.json') == original['fixture_seal']
    rows, paths = [], []
    for spec in pc.matrix():
        path = session / 'trials' / spec['trial']
        result = pc.replay_trial(path)
        assert result == read(path / 'derived.json')
        assert read(path / 'complete.json')['valid'] is True
        assert pc.old.digest(path / 'seal.json') == original['trial_seals'][spec['trial']]
        rows.append(result['summary']); paths.append(path)
    recomputed = pc.compare(rows)
    assert all(original[k] == v for k,v in recomputed.items())
    cells = {}
    for period in (100,20):
        for counters in (False,True):
            group = [r for r in rows if r['period_ms'] == period and r['counters'] == counters]
            cells[f'{period}_{"on" if counters else "off"}'] = {
                k:st.mean(r[k] for r in group) for k in
                ('cpu_usec_per_completed_work', 'busy_capacity', 'busy_cpu_cores',
                 'timely_500_fraction', 'timely_1000_fraction', 'failure_fraction', 'p99_e2e_ms')}
    previous = pc.BASE
    old_paths = sorted(p.parent for p in (previous / 'trials').glob('*/attempt-*/derived.json'))
    assert len(old_paths) == 16
    for path in old_paths: pc.old.verify_seal(path)
    previous_manifest = read(previous / 'preparation/manifest.json')
    same = {k:manifest[k] == previous_manifest[k] for k in
            ('baseline','image','server_sha256','loadgen_sha256','gate_sha256')}
    same['arrivals'] = read(session / 'preparation/arrivals.json') == read(previous / 'preparation/arrivals.json')
    same['power_settings'] = read(session / 'environment.json')['power_settings'] == read(previous / 'environment.json')['power_settings']
    rates = {}
    for label, candidates in [('pilot',paths),('V20',old_paths)]:
        periods = collections.defaultdict(list)
        for path in candidates:
            summary = read(path / 'derived.json')['summary']
            if (label == 'pilot' and summary['counters']) or (label == 'V20' and summary['arm'] not in ('A','C')):
                continue
            periods[summary['period_us']//1000].append(fixed_busy_rate(path))
        rates[label] = {str(k):dict(values=v, mean=st.mean(v)) for k,v in periods.items()}
    result = dict(review='2026-10-06', decision_recomputed=recomputed['decision'],
        pilot_raw_replays_verified=16, prior_trial_seals_verified=16,
        offers=sum(r['offered'] for r in rows), completed=sum(r['completed_computations'] for r in rows),
        fixtures_passed=fixtures['passed'], cells=cells, contrasts=recomputed,
        matched_contract=same, matched_fixed_busy_window_rps=rates,
        host=dict(pilot=host_summary(paths), V20=host_summary(old_paths)),
        idle_baseline_c=dict(pilot=read(session / 'environment.json')['baseline_c'],
                             V20=read(previous / 'environment.json')['baseline_c']),
        causal_explanation_established=False,
        limits=['Host comparisons are descriptive, across sessions, not randomized interventions.',
                'Host monitor summaries include warmup and arrivals; snapshot frequencies are not worker clocks.',
                'Original V20 yielding arms are not repeated by this cost pilot.',
                'The frozen decision and original evidence are unchanged.'],
        source_seals={str(path.relative_to(ROOT) / 'seal.json'):pc.old.digest(path / 'seal.json')
                      for path in paths + old_paths + [report_path, session / 'counter_fixtures', session / 'preparation']})
    out = ROOT / 'analysis/runtime_io_period_cost_pilot_review/20261006'
    out.mkdir(parents=True, exist_ok=True)
    pc.old.save(out / 'report.json', result)
    print(json.dumps({k:result[k] for k in ('decision_recomputed','pilot_raw_replays_verified',
        'prior_trial_seals_verified','offers','completed','fixtures_passed','matched_contract','host')}, indent=2))
    print('Review: ' + str(out / 'report.json'))


if __name__ == '__main__':
    main()
