#!/usr/bin/env python3
"""Verify real HTTP fixtures under both runtimes without quota performance work."""
import argparse
import os
from pathlib import Path
import shutil
import tempfile

import build_fairness as build
import fairness_analysis
import run
import trace_analysis


def verify(directory):
    manifest=build.verify_manifest()
    if directory.exists():raise RuntimeError('Use a fresh functional fixture directory')
    directory.mkdir(parents=True)
    summary=dict(performance_run=False,eligible_for_full=False,images=manifest['images'],modes=[])
    with tempfile.TemporaryDirectory(prefix='fairness-functional-') as tmp:
        root=Path(tmp)
        build.prepare.prepare(build.SOURCE,root/'runtime')
        for variant in ('stock','patched'):
            output=directory/variant;output.mkdir()
            trace_file=root/(variant+'.trace');trace_file.touch()
            command=['docker','run','--rm','--network','none','--read-only','--cap-drop','ALL',
                     '--security-opt','no-new-privileges','--user',f'{os.getuid()}:{os.getgid()}',
                     '--tmpfs','/tmp:rw,exec,nosuid,size=1g','-e','GOCACHE=/tmp/go-cache',
                     '-e','GOTOOLCHAIN=local','-e','GOENV=off','-e','TRACE_TEST_OUTPUT=/out',
                     '-v',f'{run.HERE/"service"}:/src:ro','-v',f'{output}:/out',
                     '-v',f'{trace_file}:/runtime.trace','-w','/src']
            if variant=='patched':
                for name in build.prepare.EXPECTED:
                    command+=['-v',f'{root/"runtime"/name}:/usr/local/go/src/runtime/{name}:ro']
            command+=[build.prepare.IMAGE,'go','test','-v','-count=1','./...']
            print('FUNCTIONAL FIXTURES:',variant,flush=True)
            with (directory/(variant+'_go_tests.log')).open('w') as log:
                run.sp.run(command,stdout=log,stderr=run.sp.STDOUT,check=True)
            parsed=root/(variant+'-analysis');shutil.copytree(output,parsed)
            combined=trace_analysis.analyze(parsed,build.DECODER,manifest['decoder_sha256'])
            config=dict(runtime_trace=True,custom_recording=True,trace_storage='memory',worker_yield=False)
            run.validate_trace_storage(run.read(parsed/'trace_status.json'),config)
            custom=parsed/'custom';config=dict(config,runtime_trace=False)
            run.validate_reduced_trace(custom,config,run.read(custom/'loadgen.json'),
                                       run.read(custom/'server_metrics.json'))
            dump=root/(variant+'-parsed.txt')
            with dump.open('w') as stream:
                run.sp.run([str(build.DECODER),'-d=parsed',str(parsed/'runtime.trace')],stdout=stream,check=True)
            waits=fairness_analysis.network_waits(dump,combined)
            assert combined['outcome_counts']['success']>0 and combined['outcome_counts']['rejected']>0
            assert combined['outcome_counts']['timeout']>0
            summary['modes'].append(dict(variant=variant,outcomes=combined['outcome_counts'],
                                         reduced_custom_valid=True,network_ready=waits,
                                         go_tests_passed=sum(line.startswith('--- PASS:')
                                                             for line in (directory/(variant+'_go_tests.log')).read_text().splitlines())))
    summary['fixture_sha256']={str(p.relative_to(directory)):run.sha(p) for p in directory.rglob('*') if p.is_file()}
    run.put(directory/'verification.json',summary)
    print('FUNCTIONAL VERIFICATION COMPLETE:',directory/'verification.json',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory',type=Path,required=True)
    verify(parser.parse_args().directory.resolve())
