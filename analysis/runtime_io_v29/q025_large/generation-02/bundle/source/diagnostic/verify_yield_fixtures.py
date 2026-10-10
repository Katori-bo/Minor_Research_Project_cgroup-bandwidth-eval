#!/usr/bin/env python3
"""Export and validate real HTTP yield fixtures; no quota performance run."""
import argparse
import os
from pathlib import Path
import tempfile
import run
import trace_analysis
import verify_component_fixtures


def verify(directory, output):
    if directory.exists():
        raise ValueError('use a fresh fixture directory; existing evidence is not overwritten')
    directory.mkdir(parents=True)
    with tempfile.TemporaryDirectory() as tmp:
        trace_file = Path(tmp)/'runtime.trace'
        trace_file.touch()
        run.sp.run(['docker', 'run', '--rm', '--user', f'{os.getuid()}:{os.getgid()}',
                    '-e', 'GOCACHE=/tmp/go-cache', '-e', 'TRACE_TEST_OUTPUT=/out',
                    '-v', f'{run.HERE / "service"}:/src:ro', '-v', f'{directory}:/out',
                    '-v', f'{trace_file}:/runtime.trace', '-w', '/src',
                    'golang:1.26.1-alpine', 'go', 'test', '-count=1', './...'], check=True)
    verify_component_fixtures.verify(directory, output)
    result = run.read(output)
    result['yield_modes'] = []
    # Parse on a copy, retaining the exported fixture directory as raw evidence.
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)/'yield'
        run.shutil.copytree(directory/'yield', root)
        combined = trace_analysis.analyze(root)
        for mode, source, runtime in [('combined', root, True), ('custom', root/'custom', False)]:
            config = dict(runtime_trace=runtime, custom_recording=True,
                          trace_storage='memory', worker_yield=True)
            status, server, lg = [run.read(source/n) for n in
                                  ('trace_status.json', 'server_metrics.json', 'loadgen.json')]
            run.validate_trace_storage(status, config)
            run.validate_worker_yield(server, config)
            if not runtime:
                run.validate_reduced_trace(source, config, lg, server)
            for bad in (dict(status, worker_yield=False),
                        {k: v for k, v in status.items() if k != 'worker_yield'}):
                try:
                    run.validate_trace_storage(bad, config)
                except ValueError:
                    pass
                else:
                    raise AssertionError('incorrect or missing yield evidence accepted')
            result['yield_modes'].append(dict(mode=mode, worker_yield=True,
                                              outcome_counts=combined['outcome_counts'] if runtime else None,
                                              corruption_rejected=True))
    result['source_hashes'] = {str(p.relative_to(directory)): run.sha(p)
                             for p in directory.rglob('*') if p.is_file()}
    run.put(output, result)
    print('YIELD FIXTURES VERIFIED:', output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    verify(args.directory.resolve(), args.output.resolve())
