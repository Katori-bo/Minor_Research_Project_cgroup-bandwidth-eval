#!/usr/bin/env python3
"""Real HTTP identity/capture fixtures; no quota performance measurement."""
import hashlib
import http.client
import json
from pathlib import Path
import subprocess
import time

import build_decision_probe as build
import decision_analysis
import decision_probe as probe
import run


def verify():
    manifest=probe.verify_build(require_fixtures=False);records=[]
    fixture_root=build.DEFAULT/'functional_fixtures'/str(time.time_ns())
    for mode,image in manifest['images'].items():
        container=run.capture(['docker','run','-d','--read-only','--network','bridge',
            '--cap-drop','ALL','--security-opt','no-new-privileges','-e','WORKERS=4',
            '-e','QUEUE_SIZE=128','-e','GOMAXPROCS=2','-e','INSTRUMENT=1','-e','WORKER_YIELD=0',
            '-e','TRACE_DIAGNOSTIC=1','-e','TRACE_RUNTIME=0','-e','TRACE_CUSTOM=1',
            '-e','TRACE_STORAGE=memory','-p','127.0.0.1::8080',image])
        client=None
        try:
            port=int(run.capture(['docker','port',container,'8080/tcp']).split(':')[-1])
            def request(method,path):
                client.request(method,path)
                response=client.getresponse();body=response.read()
                return response.status,body
            for _ in range(50):
                client=http.client.HTTPConnection('127.0.0.1',port,timeout=10)
                try:
                    code,body=request('GET','/health')
                    if code!=200: raise ValueError('health failed')
                    health=json.loads(body);break
                except OSError:
                    client.close();time.sleep(.1)
            else: raise RuntimeError('fixture health timeout')
            if (health['workers'],health['gomaxprocs'],health['queue_cap'],health['worker_yield'],health['runtime_capture'])!=(4,2,128,False,False):
                raise ValueError('fixture workload/runtime settings differ')
            for path in ('/reset','/trace/start'):
                if request('POST',path)[0]!=204: raise ValueError('fixture start failed')
            digest=bytes(range(32))
            for _ in range(44000):digest=hashlib.sha256(digest).digest()
            expected=f'OK: iter=44000 digest={digest[:8].hex()}\n'.encode()
            requests=[]
            for rid in (0,1,2):
                # Persistent connection, followed by another independent socket,
                # exercises reuse and distinct HTTP G identities.
                if rid==2:
                    client.close();client=http.client.HTTPConnection('127.0.0.1',port,timeout=10)
                code,body=request('GET',f'/work?iterations=44000&id={rid}')
                if code!=200 or body!=expected: raise ValueError('original SHA work/response changed')
                requests.append(dict(ID=rid,StatusCode=code,Error='',TimedOut=False))
            for _ in range(100):
                _,body=request('GET','/health');h=json.loads(body)
                if h['admitted']==h['completed'] and h['active_handlers']==0 and h['trace_pending_responses']==0:break
                time.sleep(.01)
            else: raise ValueError('functional fixture did not drain')
            if request('POST','/trace/stop')[0]!=204: raise ValueError('fixture stop failed')
            _,body=request('GET','/trace/status');status=json.loads(body)
            _,body=request('GET','/metrics');server=json.loads(body)
            result=decision_analysis.analyze_capture(server,status,dict(requests=requests),mode=='observed')
            capture=server['scheduler_capture']
            _,body=request('GET','/metrics')
            if json.loads(body)['scheduler_capture']!=capture:raise ValueError('stopped capture changed')
            target=fixture_root/mode;target.mkdir(parents=True,exist_ok=False)
            for name,value in [('server_metrics.json',server),('trace_status.json',status),
                ('loadgen.json',dict(requests=requests)),('scheduler_attribution.json',result)]:
                run.put(target/name,value)
            if mode=='observed' and (not any(e['kind']==4 and e['request']==0 for e in capture['events'])
                                    or result['matched_prehandler_network_waits']<1):
                raise ValueError('real HTTP wake/dispatch/request-zero join missing')
            records.append(dict(mode=mode,image=image,events=capture['reserved'],
                fixture_directory=str(target.relative_to(build.DEFAULT)),
                matched_prehandler_network_waits=result.get('matched_prehandler_network_waits'),
                original_sha_response_passed=True,stopped_capture_immutable=True,
                fixture_files_sha256={p.name:run.sha(p) for p in target.iterdir()}))
        finally:
            if client is not None:client.close()
            subprocess.run(['docker','rm','-f',container],stdout=subprocess.DEVNULL,check=True)
    run.put(build.DEFAULT/'functional_verification.json',dict(passed=True,performance_run=False,
        eligible_for_full=False,records=records,verifier_sha256=run.sha(Path(__file__)),
        analyzer_sha256=run.sha(Path(decision_analysis.__file__))))
    print('BOTH DECISION IMAGE APIS AND HTTP JOINS VERIFIED; no quota measurement run.')


if __name__=='__main__':verify()
