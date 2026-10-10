#!/usr/bin/env python3
"""Read-only audit of sealed V16 data; derived evidence lives outside the session."""
import collections
import csv
import json
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'diagnostic'))
import repeatability_study as study
import run

RESULTS = ROOT / 'results/diagnostic/runtime-io-v16-repeatability-1'
OUT = ROOT / 'analysis/runtime_io_v16_repeatability_review'


def canonical_command(command):
    command = command.copy()
    command[command.index('--name') + 1] = '<trial-container-name>'
    command[-1] = '<declared-image>'
    return command


def main():
    study.verify_completion(RESULTS)
    if OUT.exists():
        raise ValueError('preserve existing derived review')
    session = RESULTS / 'session'
    plan = run.read(session / 'matrix.json')
    environment = run.read(session / 'environment.json')
    with (session / 'analysis/trials.csv').open() as stream:
        trial_rows = {r['run_id']: r for r in csv.DictReader(stream)}
    detail = []
    commands, powers, runtime_states, resource_settings, schedules = [], [], [], [], []
    for config in plan:
        seal = run.read(RESULTS / 'completion.json')['attempts'][config['run_id']]
        path = session / 'attempts' / config['run_id'] / seal['attempt']
        result, monitor, container = (run.read(path / name) for name in ('result.json', 'monitor.json', 'container.json'))
        client, server = run.read(path / 'loadgen.json'), run.read(path / 'server_metrics.json')
        commands.append(canonical_command(container['command']))
        powers.extend([result['power_before'], result['power_after']])
        keys = ('go_version', 'runtime_variant', 'gomaxprocs', 'gomaxprocs_env', 'godebug',
                'num_cpu', 'workers', 'queue_cap', 'instrument', 'entry_protocol',
                'runtime_capture', 'custom_recording', 'worker_yield')
        runtime_states.append({k: result['runtime'][k] for k in keys})
        resource_settings.append(result['limits'][result['cgroup_path']])
        schedule = [(q['ID'], q['ScheduledOffsetNs']) for q in sorted(client['requests'], key=lambda q: q['ID'])]
        schedules.append(schedule)
        cpus, other = collections.Counter(), collections.Counter()
        for sample in monitor:
            for process in sample['process_cpu_deltas']:
                if process['comm'] == 'server':
                    cpus[process['last_cpu']] += process['cpu_delta_sec']
                elif process['comm'] not in ('loadgen', 'python3'):
                    other[process['comm']] += process['cpu_delta_sec']
        delta = result['cgroup_delta']
        row = trial_rows[config['run_id']]
        thermal = run.read(path / 'settling.json')
        final = thermal['samples'][-1]['elapsed_sec']
        window = [s for s in thermal['samples'] if s['elapsed_sec'] >= final - run.POLICY['window_sec']]
        detail.append(dict(run_id=config['run_id'], block=config['rep'], arm=config['recorder_arm'],
            image_id=container['image_id'], idle_mean_c=statistics.mean(s['temperatures']['k10temp:Tctl'] for s in window),
            sampled_load_mean_c=statistics.mean(s['temps_c']['k10temp:temp1_input'] for s in monitor),
            sampled_freq_mean_mhz={f'cpu{k}': statistics.mean(s['freqs_mhz'][f'cpu{k}'] for s in monitor) for k in (2, 4)},
            user_cpu_usec_per_job=delta['user_usec'] / server['completed'],
            system_cpu_usec_per_job=delta['system_usec'] / server['completed'],
            cpu_usec_per_job=float(row['cpu_usec_per_completed_work']),
            queue_p99_ms=float(row['p99_queue_ms']), post_work_p99_ms=float(row['p99_post_work_ms']),
            sampled_process_seconds_by_last_cpu=dict(cpus),
            background_process_sample_seconds=dict(other.most_common(10)), quality_flags=result['quality_flags']))
    def identical(values):
        return all(v == values[0] for v in values)
    checks = dict(launch_arguments_equal_except_name_and_declared_image=identical(commands),
        runtime_configuration_equal=identical(runtime_states), actual_own_cgroup_settings_equal=identical(resource_settings),
        power_settings_equal_to_baseline=all(p == environment['power_settings'] for p in powers),
        all_offered_schedules_identical=identical(schedules), no_quality_flags=all(not d['quality_flags'] for d in detail))
    if not all(checks.values()):
        raise ValueError('unexpected launch/resource/workload difference: ' + str(checks))
    classes = {arm: collections.Counter() for arm in study.analysis.ARMS}
    with (session / 'analysis/requests.csv').open() as stream:
        for row in csv.DictReader(stream):
            if row['deadline_ms'] == '500':
                classes[row['recorder_arm']][row['deadline_crossing']] += 1
    audit_dir = session / 'repeatability_build/binary_audit'
    image_a, image_z = (run.read(audit_dir / (name + '.image.json')) for name in ('legacy', 'exact_rebuild'))
    image_differences = sorted(k for k in set(image_a) | set(image_z) if image_a.get(k) != image_z.get(k))
    summary = {}
    for arm in study.analysis.ARMS:
        values = [d for d in detail if d['arm'] == arm]
        summary[arm] = {key: dict(median=statistics.median(d[key] for d in values),
            minimum=min(d[key] for d in values), maximum=max(d[key] for d in values)) for key in
            ('idle_mean_c', 'sampled_load_mean_c', 'cpu_usec_per_job', 'user_cpu_usec_per_job',
             'system_cpu_usec_per_job', 'queue_p99_ms', 'post_work_p99_ms')}
    evidence = dict(at=run.now(), completed_evidence_verified=True, performance_collection_started=False,
        checks=checks, arm_summary=summary, trials=detail,
        deadline_500_classes={a: dict(c) for a, c in classes.items()}, image_inspect_differing_keys=image_differences,
        image_config_identical=image_a['Config'] == image_z['Config'],
        limitation='Sampled frequency, temperature and process last_cpu do not establish instantaneous execution '
        'frequency, exclusive CPU occupancy or request-level throttling. Four blocks cannot establish equivalence. '
        'No causal container, thermal, scheduler or filesystem mechanism is identified.',
        input_sha256={str(p.relative_to(ROOT)): run.sha(p) for p in
            (RESULTS / 'completion.json', session / 'metadata.json', session / 'analysis/trials.csv',
             session / 'analysis/requests.csv', session / 'analysis/repeatability_screen.json', Path(__file__))})
    OUT.mkdir(parents=True)
    run.put(OUT / 'review.json', evidence)
    report = '''# V16 repeatability review and offline execution audit — 2026-10-04

All 12 accepted trials and the frozen source/build/environment/raw/analysis seals verified.
The original-image A/A comparison is within the declared discovery margins in every block.
The exact-source rebuild is outside the timely-success margin in both comparisons in every block,
in the direction of improvement: +1.53–3.92 percentage points at 500 ms. This is a failed neutrality
screen, not a technically invalid collection. Four blocks do not establish statistical equivalence.

## What the offline audit establishes

Actual launch arguments match except for declared image ID and trial container name. Actual own
cgroup settings, runtime configuration, power settings and every offered ID/scheduled-offset
vector match. All inherited acceptance checks passed. Executable bytes, Go build IDs and image
runtime configuration match. Image identity/rootfs layer, creation/history/reference metadata differ;
the recorded image size differs by one byte. These differences do not establish a runtime cause.

The sampled mean temperatures under load range from 59.98–60.85°C across trials. This does not
support a large arm-specific temperature separation in these samples, but does not prove thermal
equivalence. Sampled frequencies and process CPU-placement snapshots vary and do not identify
actual frequency during each computation or exclusive occupancy. No clear causal host or
configuration mismatch was identified in the retained records.

The rebuilt-image runs use approximately 0.27–0.51% less aggregate CPU per completed job than
original label A and 0.38–0.46% less than B. Most of the difference is in user CPU accounting;
system CPU is not consistently lower. Queue p99 is 468–480 ms in rebuilt runs versus 496–508 ms
in original runs. Post-work p99 remains approximately 160–162 ms in all arms. This accompanies
the timely-success improvement, but neither marginal percentiles nor small CPU changes establish
the mechanism.

## The original research problem remains

Each arm offers 27,172 requests across four blocks. Original label A retains 2,344 successful late
responses whose computation certainly finishes before 500 ms; B retains 2,311 and the rebuild
2,381. Requests with computation certainly finishing after 500 ms number 4,935, 5,084 and 4,182,
respectively. These are descriptive request counts, not independent replications. Overall improvement
coexists with persistent post-computation misses; it is not a handoff remedy. No publication or
runnable-readiness boundary has been added.

## Decision and bounded next task

Stay in Step 1. Exact build reproducibility is established for bytes; original-image repeatability
passes the discovery screen. Behavioral neutrality across separately built image layers is still
unresolved. Do not return to another clock-count sweep or claim a scheduler cause.

If further collection is justified, prepare one narrow container-execution comparison that deliberately
equalizes the backing executable file and keeps image choice/order explicit. Declare which image/layer
or launch-state ambiguity it tests, its contrasts and interpretation before collection. A common-file
loading control is a proposed treatment, not an established solution; record identity/mount settings
without new per-request markers. If the effect persists or the control itself changes timing, report
that uncertainty and reconsider the precision/scope rather than layering instrumentation onto it.
Persistent publication recording and worker/parallelism interventions remain unqualified. No new
performance batch was prepared or launched by this offline review.

[Sealed result report](../../results/diagnostic/runtime-io-v16-repeatability-1/session/analysis/report.md)
[Detailed audit](review.json)
'''
    (OUT / 'report.md').write_text(report)
    run.put(OUT / 'review_seal.json', dict(files_sha256={name: run.sha(OUT / name) for name in ('review.json', 'report.md')}))
    print('Offline V16 review complete:', OUT / 'report.md')
    print('Recorded comparisons:', checks)


if __name__ == '__main__':
    main()
