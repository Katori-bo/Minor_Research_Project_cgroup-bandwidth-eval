#!/usr/bin/env python3
"""Build native collector; check110 seconds on a regular file, no Docker/workload."""
import os
from pathlib import Path
import subprocess
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'diagnostic'))
import v24r3_common as c
import v24r3_counter as counter
import v24r3_software as software

def main():
    c.BUILD.mkdir(parents=True,exist_ok=False)
    argv=['/usr/bin/gcc','-std=c11','-O2','-Wall','-Wextra','-Werror',
          str(c.ROOT/'diagnostic/v24r3_counter.c'),'-o',str(c.BUILD/'counter')]
    result=subprocess.run(argv,capture_output=True,text=True,timeout=60)
    (c.BUILD/'stdout').write_text(result.stdout);(c.BUILD/'stderr').write_text(result.stderr)
    if result.returncode:raise ValueError('native compilation failed')
    compiler=subprocess.run(['/usr/bin/gcc','--version'],capture_output=True,text=True,check=True).stdout
    c.save(c.BUILD/'manifest.json',dict(compile_passed=True,argv=argv,compiler=compiler,
        source_sha256=c.digest(c.ROOT/'diagnostic/v24r3_counter.c'),binary_sha256=c.digest(c.BUILD/'counter')))
    c.seal(c.BUILD);software.verify_build(c)
    c.REPAIR.mkdir(parents=True,exist_ok=False)
    fixture=c.REPAIR/'synthetic.cpu.stat'
    fixture.write_text('usage_usec 100000\nuser_usec 90000\nsystem_usec 10000\n'
        'nice_usec 0\ncore_sched.force_idle_usec 0\nnr_periods 100\nnr_throttled 50\n'
        'throttled_usec 50000\nnr_bursts 0\nburst_usec 0\n')
    argv=[str(c.BUILD/'counter'),'--path',str(fixture),'--output',str(c.REPAIR/'counter.raw.json')]
    c.save(c.REPAIR/'argv.json',argv)
    print('Native110-second synthetic-file software check started; no service.',flush=True)
    with (c.REPAIR/'stdout').open('x') as out,(c.REPAIR/'stderr').open('x') as err:
        result=subprocess.run(argv,stdout=out,stderr=err,timeout=125,
            preexec_fn=lambda:os.sched_setaffinity(0,{0,1}))
    if result.returncode:raise ValueError('native software collection failed')
    probe=counter.decode(c.read(c.REPAIR/'counter.raw.json'));c.save(c.REPAIR/'counter.json',probe)
    summary=software.summarize(probe,str(fixture))
    c.save(c.REPAIR/'report.json',dict(decision='native_synthetic_sampler_pass',performance_run=False,
        runtime_qualified=False,binary_sha256=c.digest(c.BUILD/'counter'),
        source_hashes={n:c.digest(c.ROOT/n) for n in software.SOURCES},summary=summary))
    c.seal(c.REPAIR);software.verify_receipt(c.REPAIR,c);print(summary,flush=True)

if __name__=='__main__':main()
