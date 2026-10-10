#!/usr/bin/env python3
"""Parse real Go functional fixtures and challenge reduced-mode validation."""
import argparse
import copy
from pathlib import Path
import shutil
import tempfile
import run
import trace_analysis


def verify(source, output):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)/'fixtures'
        shutil.copytree(source, root)
        combined = trace_analysis.analyze(root)
        checked = {'combined_outcomes': combined['outcome_counts'], 'reduced_modes': []}
        for mode, runtime, custom in [('runtime', True, False), ('custom', False, True)]:
            directory = root / mode
            config = dict(runtime_trace=runtime, custom_recording=custom)
            lg, srv = [run.read(directory/n) for n in ('loadgen.json','server_metrics.json')]
            if runtime:
                run.put(directory/'trace_scheduler.json', trace_analysis.parse_trace(directory/'runtime.trace'))
            run.validate_reduced_trace(directory, config, lg, srv)
            status = run.read(directory/'trace_status.json')
            corrupt = copy.deepcopy(status)
            if custom:
                corrupt['io_events'] = [e for e in corrupt['io_events'] if e['kind'] != 'rejected']
            else:
                corrupt['clock_anchors'][0]['after_ns'] = -1
            run.put(directory/'trace_status.json', corrupt)
            try:
                run.validate_reduced_trace(directory, config, lg, srv)
            except ValueError:
                pass
            else:
                raise AssertionError(f'{mode}: corrupted evidence accepted')
            checked['reduced_modes'].append(dict(mode=mode,valid_fixture=True,corruption_rejected=True))
        output.parent.mkdir(parents=True, exist_ok=True)
        checked['source_hashes'] = {str(p.relative_to(source)):run.sha(p) for p in source.rglob('*') if p.is_file()}
        run.put(output, checked)
        print(output)


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    verify(args.source.resolve(),args.output.resolve())
