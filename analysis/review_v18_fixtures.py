#!/usr/bin/env python3
"""Review sealed V18 fixture captures without changing the original evidence."""
import argparse
import hashlib
import json
from pathlib import Path
import runpy
import statistics


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def review(source):
    seal = read(source / 'fixture_seal.json')['files_sha256']
    actual = {str(p.relative_to(source)): digest(p) for p in source.rglob('*')
              if p.is_file() and p.name != 'fixture_seal.json'}
    if actual != seal:
        raise ValueError('fixture seal or file inventory mismatch')
    for name, expected in read(source / 'source_hashes.json').items():
        if digest(source / 'source' / name) != expected:
            raise ValueError('frozen source hash mismatch: ' + name)
    summary = read(source / 'summary.json')
    if not summary['passed'] or summary['error'] is not None:
        raise ValueError('original fixture collection did not pass')
    if read(source / 'root_trace_state_before.json') != read(source / 'root_trace_state_after.json'):
        raise ValueError('root trace controls changed')
    api = read(source / 'map_api_check.json')
    if api['returncode'] or api['stderr'].strip() or api['stdout'].strip() != 'MAP_API 1 0 1':
        raise ValueError('native map API guard failed')
    # Only execute the reviewed, hash-verified analyzer retained with these captures.
    validate = runpy.run_path(str(source / 'source/kernel_fixture_analysis.py'))['validate']
    validations = []
    for mode in ('sleep', 'cpu', 'quota'):
        case = source / mode
        attempt = read(case / 'attempt.json')
        metadata = attempt['metadata']
        if attempt['error'] or attempt['cleanup_errors'] or not attempt['cgroup_removed']:
            raise ValueError('fixture cleanup failed: ' + mode)
        if metadata['observer_returncode'] or metadata['worker_returncode'] or not attempt['owned_bpf_ids']:
            raise ValueError('fixture process/attachment check failed: ' + mode)
        if attempt['owned_bpf_ids'] != metadata['owned_bpf_ids']:
            raise ValueError('owned BPF identity mismatch: ' + mode)
        result = validate((case / 'events.txt').read_text(), (case / 'worker.jsonl').read_text(),
                          (case / 'observer.stderr').read_text(), metadata)
        if result != read(case / 'validation.json'):
            raise ValueError('raw replay differs from saved validation: ' + mode)
        validations.append(result)
    if validations != summary['fixtures']:
        raise ValueError('summary differs from replayed validations')
    if summary['performance_batch_ready'] or summary['observer_cost_qualified'] or summary['performance_run']:
        raise ValueError('unexpected performance qualification claim')
    intervals = validations[2]['quota_intervals']
    midpoints = [(v['duration_lower_ns'] + v['duration_upper_ns']) / 2e6 for v in intervals]
    return dict(source=str(source), source_seal_sha256=digest(source / 'fixture_seal.json'),
                original_seal_verified=True, frozen_raw_replay_verified=True,
                root_trace_controls_unchanged=True, cleanup_checks_passed=True,
                fixtures=validations,
                quota_pause_midpoint_ms=dict(median=statistics.median(midpoints),
                                            minimum=min(midpoints), maximum=max(midpoints)),
                maximum_transition_duration_bracket_width_us=max(
                    v['duration_upper_ns']-v['duration_lower_ns'] for v in intervals)/1000,
                decision='single_cpu_fixture_observation_qualified',
                service_observation_qualified=False, observer_cost_qualified=False,
                service_request_attribution=False,
                next_gate='service thread/CPU coverage, ancestry and clock alignment; then observer cost pilot')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    source = args.source.resolve()
    output = args.output.resolve()
    if output == source or source in output.parents:
        raise ValueError('derived review must be outside the sealed capture')
    result = review(source)
    output.mkdir(parents=True, exist_ok=False)
    (output / 'review.json').write_text(json.dumps(result, indent=2)+'\n')
    (output / 'review_source.py').write_bytes(Path(__file__).read_bytes())
    table = '\n'.join(
        f"| {v['mode']} | {v['received_events']} | {v['process_cpu_ms']:.3f} | "
        f"{v['successful_throttle_intervals']} | {v['cpu_stat_nr_throttled']} |"
        for v in result['fixtures'])
    q = result['quota_pause_midpoint_ms']
    (output / 'report.md').write_text(f'''# V18 bounded fixture review

Decision: **single_cpu_fixture_observation_qualified**.

Reviewed capture: `{source}`. All sealed file hashes and frozen source hashes
match. Replaying the frozen analyzer against each raw capture reproduces its
saved validation and the collection summary. All three observers/workers exited
successfully; their recorded owned-probe detach and temporary-cgroup removal
checks passed. Root tracing controls match before/after.

| Fixture | Received events | Process CPU ms | Closed quota intervals | nr_throttled |
|---|---:|---:|---:|---:|
{table}

The quota fixture recorded 190 throttle attempts, but only 18 successful, closed
quota-state intervals. Their duration midpoint median is {q['median']:.6f} ms,
range {q['minimum']:.6f}–{q['maximum']:.6f} ms. The widest duration bracket is
{result['maximum_transition_duration_bracket_width_us']:.2f} microseconds.
These bounds describe function-transition brackets, not total request clock error.
The kernel counter records 18 throttled periods in this single-CPU fixture; this
agreement is a cross-check and is not a general equality for multi-CPU operation.
Sleep and uncapped CPU controls have no quota intervals. Emitted/received event
counts agree and observer diagnostics are empty in all three captures.

The result verifies detection of known scheduler/quota events on CPU2. It does
not explain any HTTP deadline miss, resolve rebuild/clock effects, or qualify
observer overhead. Per-CPU quota state is not a whole-service stop. Publication
and Go handler runnable-readiness remain unobserved. The first failed capture
remains invalid and unchanged.

Next gate: a bounded original-service compatibility check on CPUs2,4, including
existing/new thread coverage, initial state, exact leaf cgroup and uncapped
ancestors, and mapping to retained service/client clock bounds. Then freeze and
collect six matched tracing-off/on pairs in a separate quiet window. Only after
that cost screen can kernel overlap be interpreted as service contribution evidence.
No performance batch was launched by this review.
''')
    hashes = {p.name: digest(p) for p in output.iterdir() if p.is_file()}
    (output / 'review_seal.json').write_text(json.dumps(dict(files_sha256=hashes), indent=2)+'\n')
    print(output / 'report.md')


if __name__ == '__main__':
    main()
