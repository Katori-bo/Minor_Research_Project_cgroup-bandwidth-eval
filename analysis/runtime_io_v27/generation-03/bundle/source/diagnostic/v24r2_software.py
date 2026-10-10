"""Replay the full-duration synthetic sampler check; never launches a workload."""
import math
import sys

import v24r2_model as model

SOURCES = ('diagnostic/v24r2_counter.py', 'diagnostic/v24r2_model.py',
           'diagnostic/v24r2_software.py', 'analysis/check_v24r2_sampler.py')


def summarize(probe, path):
    samples = model.validate_samples(probe, path)
    duration = (probe['finished_ns']-probe['started_ns'])/1e9
    widths = [r['after_ns']-r['before_ns'] for r in samples]
    gaps = [b['before_ns']-a['after_ns'] for a,b in zip(samples,samples[1:])]
    if not 110 <= duration <= 110.1 or not 5000 <= len(samples) <= 6000:
        raise ValueError('synthetic recording lacks full110-second coverage')
    if max(gaps) > 50_000_000:
        raise ValueError('synthetic sampler gap exceeds50ms')
    if (samples[0]['before_ns']-probe['started_ns'] > 50_000_000
            or probe['finished_ns']-samples[-1]['after_ns'] > 50_000_000):
        raise ValueError('synthetic lifetime endpoints lack coverage')
    ordered = sorted(widths)
    return dict(samples=len(samples), duration_sec=duration,
        max_read_width_ms=max(widths)/1e6,
        p99_read_width_ms=ordered[math.ceil(.99*len(ordered))-1]/1e6,
        max_adjacent_gap_ms=max(gaps)/1e6,
        own_cpu_ms=probe['own_cpu_ns']/1e6,
        gc_collections_during_capture=[b-a for a,b in zip(
            probe['gc_collections_before'],probe['gc_collections_after'])])


def verify_receipt(directory, c):
    c.verify_seal(directory)
    report = c.read(directory/'report.json')
    if (report.get('schema') != 1 or report.get('decision') != 'synthetic_sampler_check_pass'
            or report.get('fixture_kind') != 'regular_file_with_synthetic_cpu_stat'
            or report.get('runtime_qualified') is not False
            or report.get('performance_run') is not False
            or report.get('python_version') != sys.version
            or report.get('python_executable') != sys.executable):
        raise ValueError('synthetic sampler receipt identity/contract failed')
    expected = {name:c.digest(c.ROOT/name) for name in SOURCES}
    if report['source_hashes'] != expected:
        raise ValueError('synthetic sampler check sources changed')
    path = str(directory/'synthetic.cpu.stat')
    probe = c.read(directory/'counter.json')
    if summarize(probe,path) != report['summary']:
        raise ValueError('synthetic sampler summary differs from raw recording')
    if c.read(directory/'counter.ready.json') != probe['samples'][0]:
        raise ValueError('synthetic sampler readiness differs')
    argv = [sys.executable,str(c.ROOT/'diagnostic/v24r2_counter.py'),
            '--path',path,'--output',str(directory/'counter.json')]
    if c.read(directory/'argv.json') != argv:
        raise ValueError('synthetic sampler command differs')
    return report
