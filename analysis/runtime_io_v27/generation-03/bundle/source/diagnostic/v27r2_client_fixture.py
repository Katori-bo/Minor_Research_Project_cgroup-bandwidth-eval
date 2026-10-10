"""Compiled-client report replay against a local HTTP software stub, without quotas."""
import copy
import json
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
import v27r2_common as c
import v27r2_raw as raw
import parallelism_analysis


def run_fixture(binary, output, pattern='bursty'):
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    origin=time.monotonic_ns();lock=threading.Lock();jobs=[];entries=[];handlers=[]
    cfg=dict(c.functional_configs()[0],duration_sec=.3,traffic_pattern=pattern,
             burst_period_sec=.15,burst_low_duration_sec=.1,burst_low=30,burst_high=60,
             rate=(.1*30+(.15-.1)*60)/.15 if pattern=='bursty' else 30,timeout_sec=5)
    class Handler(BaseHTTPRequestHandler):
        protocol_version='HTTP/1.1'
        def log_message(self,*args):pass
        def do_GET(self):
            parsed=urlparse(self.path)
            if parsed.path=='/clock':
                body=json.dumps(dict(server_ns=time.monotonic_ns()-origin,generation=1)).encode()
                self.send_response(200);self.send_header('Content-Type','application/json')
                self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body);return
            if parsed.path!='/work':self.send_error(404);return
            rid=int(parse_qs(parsed.query)['id'][0]);entry=time.monotonic_ns()-origin
            # Serialize synthetic worker timestamps to satisfy the retained
            # one-worker stage accounting. This is not a SHA workload.
            with lock:
                admit=time.monotonic_ns()-origin;worker=time.monotonic_ns()-origin
                completion=time.monotonic_ns()-origin;resume=time.monotonic_ns()-origin
                jobs.append(dict(id=rid,admission_ns=admit,worker_start_ns=worker,completion_ns=completion,
                                 queue_wait_ns=worker-admit,processing_ns=completion-worker))
            self.send_response(200);self.send_header('Content-Length','2')
            self.send_header('X-Queue-Wait-Ns',str(worker-admit));self.send_header('X-Processing-Ns',str(max(1,completion-worker)))
            self.send_header('X-Queue-Depth','0');self.send_header('X-Pre-Admission-Ns',str(admit-entry))
            self.send_header('X-Post-Work-Wait-Ns',str(resume-completion));self.end_headers()
            write_start=time.monotonic_ns()-origin;self.wfile.write(b'ok');self.wfile.flush();write_end=time.monotonic_ns()-origin
            exit_ns=time.monotonic_ns()-origin;handler_exit=time.monotonic_ns()-origin
            with lock:
                entries.append(dict(id=rid,entry_ns=entry,exit_ns=exit_ns,admitted=True))
                handlers.append(dict(id=rid,entry_ns=entry,admission_ns=admit,resume_ns=resume,
                    write_start_ns=write_start,write_end_ns=write_end,handler_exit_ns=handler_exit,
                    post_work_wait_ns=resume-completion,pre_admission_ns=admit-entry))
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler);server.daemon_threads=True
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    target=f'http://127.0.0.1:{server.server_port}/work?iterations=44000'
    argv=[str(binary),'-url',target,'-duration','0.3s','-pattern',pattern,'-rate',str(cfg['rate']),
          '-burst-low','30','-burst-high','60','-burst-period','0.15s','-burst-low-duration','0.1s',
          '-concurrency','2','-timeout','5s','-trace-client=true','-output',str(output/'loadgen.json')]
    try:
        result=subprocess.run(argv,capture_output=True,text=True,timeout=10)
    finally:
        server.shutdown();server.server_close();thread.join(timeout=2)
    (output/'client.stdout').write_text(result.stdout);(output/'client.stderr').write_text(result.stderr)
    c.save(output/'argv.json',argv)
    if result.returncode:raise ValueError('compiled client software fixture failed: '+result.stderr)
    client=c.read(output/'loadgen.json')
    n=len(jobs)
    metrics=dict(runtime_variant='stock',runtime_capture=False,custom_recording=False,
        worker_yield=False,entry_protocol='all-outcomes-v1',workers=1,gomaxprocs=1,queue_cap=128,
        go_version='go1.26.1',instrument=True,active_handlers=0,queue_len=0,
        completed=n,admitted=n,rejected=0,events=jobs,handler_events=handlers,entry_events=entries,clock_generation=1)
    c.save(output/'server_metrics.json',metrics);c.save(output/'config.json',cfg)
    # The JSON below is emitted by the real compiled client; no clock or request
    # fields are injected. This would reject the failed revision-01 binary.
    mapping=parallelism_analysis.clock_mapping(client,metrics)
    rows,joined,logical=raw.join(client,metrics,cfg)
    if joined!=mapping or len(rows)!=len(c.schedule(cfg)) or client['total_success']!=len(rows):
        raise ValueError('compiled report stage replay or all-offer conservation failed')
    receipt=dict(compiled_client_report_replay_passed=True,pattern=pattern,requests=len(rows),
        actual_json_fields=sorted(client),clock_anchors=len(client['clock_anchors']),
        clock_uncertainty_ns=mapping['uncertainty_ns'],clock_fields_injected=False,
        stage_accounting_replay_passed=True,quota_or_scientific_service_used=False,binary_sha256=c.digest(binary))
    c.save(output/'report.json',receipt);c.seal(output)
    return receipt
