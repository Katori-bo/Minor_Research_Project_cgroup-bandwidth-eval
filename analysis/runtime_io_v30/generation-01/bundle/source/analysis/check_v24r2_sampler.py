#!/usr/bin/env python3
"""110-second software recording on a synthetic file, with no service or Docker."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'diagnostic'))
import v24r2_common as c
import v24r2_software as software


def main():
    directory = c.REPAIR
    directory.mkdir(parents=True,exist_ok=False)
    fixture = directory/'synthetic.cpu.stat'
    fixture.write_text('usage_usec 100000\nuser_usec 90000\nsystem_usec 10000\n'
        'nice_usec 0\ncore_sched.force_idle_usec 0\nnr_periods 100\n'
        'nr_throttled 50\nthrottled_usec 50000\nnr_bursts 0\nburst_usec 0\n')
    argv = [sys.executable,str(c.ROOT/'diagnostic/v24r2_counter.py'),
            '--path',str(fixture),'--output',str(directory/'counter.json')]
    c.save(directory/'argv.json',argv)
    print('Starting110-second synthetic-file sampler software check; no workload.',flush=True)
    process = None
    try:
        with (directory/'sampler.stdout').open('x') as stdout, (directory/'sampler.stderr').open('x') as stderr:
            process = subprocess.Popen(argv,stdout=stdout,stderr=stderr,
                preexec_fn=lambda:os.sched_setaffinity(0,{0,1}))
            if process.wait(timeout=125):
                raise ValueError('synthetic sampler process failed')
        probe = c.read(directory/'counter.json')
        summary = software.summarize(probe,str(fixture))
        report = dict(schema=1,decision='synthetic_sampler_check_pass',
            fixture_kind='regular_file_with_synthetic_cpu_stat',
            python_version=sys.version,python_executable=sys.executable,
            source_hashes={name:c.digest(c.ROOT/name) for name in software.SOURCES},
            runtime_qualified=False,performance_run=False,created=time.time(),summary=summary,
            limits='Regular-file software check on the active desktop; real cgroup reads and observer comparability must pass at the external launch.')
        c.save(directory/'report.json',report);c.seal(directory)
        software.verify_receipt(directory,c)
        print(json.dumps(summary,indent=2),flush=True)
    except BaseException as exc:
        if process is not None and process.poll() is None:
            process.kill();process.wait(timeout=5)
        c.save(directory/'failure.json',dict(error=str(exc),time=time.time()))
        c.seal(directory)
        raise


if __name__=='__main__':main()
