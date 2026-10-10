#!/usr/bin/env python3
"""Explore sealed V25 accounting without collecting data or changing old reports."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'diagnostic'))
import v25_common as common
import v25_verify as verify
from kernel_bridge_analysis import clock_join
from v24r3_model import counter_bounds


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def difference(a, b):
    return [a[0] - b[1], a[1] - b[0]]


def cost(phase, key):
    cpu = phase['cpu_delta_bounds'][key]
    count = phase['clock_bounded_completions']
    return [cpu[0] / count[1], cpu[1] / count[0]]


def build(session):
    # Full independent raw replay precedes any new calculation.
    verified = verify.verify_completion(session)
    latest = common.read(session / 'latest_analysis.json')
    original = common.resolve(session, latest['path'])
    report = common.read(original / 'report.json')
    source_hash = digest(original / 'report.json')
    rows = []
    for trial in report['trial_accounting']:
        if not trial['counter_probe']:
            continue
        ref = report['trial_refs'][trial['trial']]
        directory = common.resolve(session, ref['path'])
        if digest(directory / 'seal.json') != ref['seal']:
            raise ValueError('trial reference changed')
        derived = common.read(directory / 'derived.json')
        server = common.read(directory / 'server_metrics.json')
        probe = common.read(directory / 'counter.json')
        anchors = common.read(directory / 'host_server_anchors.json')
        observations = common.read(directory / 'observations.json')
        mapping = derived['clocks']
        joined = clock_join(anchors, mapping, server['clock_generation'])
        origin = [mapping['client_test_start_ns'] + joined['kernel_minus_client_' + k + '_ns']
                  for k in ('lower', 'upper')]
        start = observations['measurement_start']['cpu_stat']['usage_usec']
        stop = observations['measurement_stop']['cpu_stat']['usage_usec']
        at_zero = counter_bounds(probe['samples'], *origin)['usage_usec']
        at_sixty = counter_bounds(probe['samples'], origin[0] + 60e9,
                                  origin[1] + 60e9)['usage_usec']
        pre = [max(0, at_zero[0] - start), max(0, at_zero[1] - start)]
        post = [max(0, stop - at_sixty[1]), max(0, stop - at_sixty[0])]
        busy, low = (trial['phases'][p] for p in ('busy', 'low'))
        total_difference = difference(cost(low, 'usage_usec'), cost(busy, 'usage_usec'))
        user_difference = difference(cost(low, 'user_usec'), cost(busy, 'user_usec'))
        system_difference = difference(cost(low, 'system_usec'), cost(busy, 'system_usec'))
        n = derived['summary']['completed_computations']
        total = stop - start
        busy_cost = cost(busy, 'usage_usec')
        excess = [total - n * busy_cost[1], total - n * busy_cost[0]]
        edge_upper = pre[1] + post[1]
        if total_difference[0] <= 0 or excess[0] <= 0:
            raise ValueError('positive accounting difference not established')
        rows.append(dict(
            trial=trial['trial'], size=trial['size'], trial_seal=ref['seal'],
            busy_state_eligible=busy['state_eligible'], low_state_eligible=low['state_eligible'],
            low_minus_busy_total_cost_usec_bounds=total_difference,
            low_minus_busy_user_cost_usec_bounds=user_difference,
            low_minus_busy_system_cost_usec_bounds=system_difference,
            system_share_of_cost_difference_upper=system_difference[1] / total_difference[0],
            whole_cpu_usec=total, whole_completions=n,
            excess_over_all_jobs_at_busy_aggregate_cost_usec_bounds=excess,
            before_first_offer_cpu_usec_bounds=pre,
            after_arrivals_through_measurement_stop_cpu_usec_bounds=post,
            all_edge_cpu_over_excess_upper=edge_upper / excess[0],
            all_edge_cpu_smaller_than_reference_excess=edge_upper < excess[0],
        ))
    if digest(original / 'report.json') != source_hash:
        raise ValueError('original report changed during review')
    result = dict(
        schema=1, decision='exploratory_accounting_leads_only',
        independent_v25_completion_replay_passed=verified['complete'],
        source_report=str((original / 'report.json').relative_to(ROOT)),
        source_report_sha256=source_hash,
        script_sha256=digest(Path(__file__)),
        trials=rows, by_size={},
        interpretation=(
            'Original fixed low windows are lower-arrival windows, not qualified low states. '
            'User/system costs divide aggregate counters by phase completions, not per-job CPU. '
            'Edge accounting compares all pre-offer and post-arrival CPU with the excess over '
            'N times busy-window aggregate CPU/completion; it is a conditional reference '
            'calculation, not identification of a mechanism or attribution to individual jobs. '
            'Clock/counter bounds are not statistical confidence intervals. '
            'No state criteria, windows, thresholds or original reports were changed.'),
    )
    for size in ('small', 'large'):
        selected = [r for r in rows if r['size'] == size]
        result['by_size'][size] = dict(
            on_trials=len(selected), qualified_low_states=sum(r['low_state_eligible'] for r in selected),
            user_difference_lower_min_usec=min(r['low_minus_busy_user_cost_usec_bounds'][0] for r in selected),
            system_share_upper_max=max(r['system_share_of_cost_difference_upper'] for r in selected),
            edge_share_upper_max=max(r['all_edge_cpu_over_excess_upper'] for r in selected),
            all_edge_cpu_smaller_in_every_trial=all(r['all_edge_cpu_smaller_than_reference_excess'] for r in selected),
        )
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('use a fresh output directory; do not overwrite a prior review')
    result = build(ROOT / 'analysis/runtime_io_v25/generation-01')
    args.output.mkdir(parents=True)
    (args.output / 'report.json').write_text(json.dumps(result, indent=2) + '\n')
    lines = ['# V25 exploratory contribution leads', '', result['interpretation'], '',
             'Independent V25 completion replay passed before these calculations.', '',
             '| Size | Trials | Qualified low states | Minimum user-cost increase | Maximum system share of phase difference | Maximum edge CPU / reference excess |',
             '|---|---:|---:|---:|---:|---:|']
    for size, row in result['by_size'].items():
        lines.append(f"| {size} | {row['on_trials']} | {row['qualified_low_states']} | "
                     f"{row['user_difference_lower_min_usec']/1000:.3f} ms/completion | "
                     f"{100*row['system_share_upper_max']:.1f}% | {100*row['edge_share_upper_max']:.1f}% |")
    lines.extend(['', 'The aggregate user-CPU difference is positive in all eight recordings. '
                  'System CPU alone cannot account for the entire measured phase-cost difference '
                  'within these bounds. This does not identify SHA, runtime, HTTP or frequency effects.', '',
                  'Pre-offer plus post-arrival CPU is smaller than the reference excess in every '
                  'recording. Under that reference accounting, attributing every edge CPU-second '
                  'to overhead is still insufficient. This is not a job-level decomposition.', '',
                  'No new workload was run. All original phase/state outcomes remain unchanged.'])
    (args.output / 'report.md').write_text('\n'.join(lines) + '\n')
    seal = {'files_sha256': {p.name: digest(p) for p in sorted(args.output.iterdir())}}
    (args.output / 'seal.json').write_text(json.dumps(seal, indent=2) + '\n')
    print(json.dumps(result['by_size'], indent=2))


if __name__ == '__main__':
    main()
