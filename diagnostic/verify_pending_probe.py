#!/usr/bin/env python3
"""Check both probe image APIs with tiny functional requests, not measurements."""
import json
from pathlib import Path
import subprocess
import time
import urllib.request

import build_pending_probe as build
import pending_probe as probe
import run


def verify():
    manifest=probe.verify_build();records=[]
    for mode,image in manifest['images'].items():
        container=run.capture(['docker','run','-d','--read-only','--cap-drop','ALL',
            '--security-opt','no-new-privileges','-e','WORKERS=4','-e','QUEUE_SIZE=128',
            '-e','GOMAXPROCS=2','-e','INSTRUMENT=1','-e','WORKER_YIELD=0',
            '-e','TRACE_DIAGNOSTIC=1','-e','TRACE_RUNTIME=0','-e','TRACE_CUSTOM=1',
            '-e','TRACE_STORAGE=memory','-p','127.0.0.1::8080',image])
        try:
            port=run.capture(['docker','port',container,'8080/tcp']).split(':')[-1]
            url='http://127.0.0.1:'+port
            for _ in range(50):
                try:
                    with urllib.request.urlopen(url+'/health',timeout=1) as response:health=json.load(response)
                    break
                except OSError:time.sleep(.1)
            else:raise RuntimeError('fixture server health timeout')
            with urllib.request.urlopen(url+'/work?iterations=44000&id=0',timeout=5) as response:
                if response.status!=200 or not response.read().startswith(b'OK: iter=44000 digest='):
                    raise ValueError('original work response changed')
            with urllib.request.urlopen(url+'/metrics',timeout=5) as response:metrics=json.load(response)
            tmp=build.DEFAULT/('functional_'+mode);tmp.mkdir(exist_ok=False)
            run.put(tmp/'server_metrics.json',metrics)
            probe.validate_counters(tmp,dict(probe_mode=mode))
            if (metrics['workers'],metrics['gomaxprocs'],metrics['queue_cap'],metrics['worker_yield'])!=(4,2,128,False):
                raise ValueError('probe fixture settings differ')
            records.append(dict(mode=mode,image=image,health=health,
                                counters=metrics['scheduler_counters'],functional_response_passed=True))
        finally:
            subprocess.run(['docker','rm','-f',container],stdout=subprocess.DEVNULL,check=True)
    run.put(build.DEFAULT/'functional_verification.json',dict(passed=True,performance_run=False,
        eligible_for_full=False,records=records,verifier_sha256=run.sha(Path(__file__))))
    print('BOTH PROBE IMAGE APIS VERIFIED; no quota performance measurement run.')


if __name__=='__main__':verify()
