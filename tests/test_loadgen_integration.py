"""Real HTTP checks. Run explicitly with host socket access; excluded from unit discovery."""
import json
from pathlib import Path
import subprocess
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = Path(__file__).resolve().parents[1]


class Handler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Length', '2')
        self.end_headers()
        self.wfile.flush()
        time.sleep(.08)
        self.wfile.write(b'OK')
    def log_message(self, *args):
        pass


class LoadgenIntegration(unittest.TestCase):
    def test_body_timing_and_drain(self):
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory(prefix='quota-loadgen-test-') as tmp:
                out = Path(tmp) / 'report.json'
                subprocess.run([str(ROOT / 'tools/loadgen/bin/loadgen'), '-url',
                    f'http://127.0.0.1:{server.server_port}', '-duration', '1s', '-rate', '20',
                    '-output', str(out)], check=True, stdout=subprocess.DEVNULL)
                d = json.loads(out.read_text())
                self.assertEqual(d['total_scheduled'], 20)
                self.assertEqual(d['total_success'], 20)
                self.assertGreaterEqual(d['service_latency_summary']['p50_ms'], 75)
                self.assertGreater(d['elapsed_including_drain_sec'], 1)
                self.assertLess(d['successful_throughput_rps'], 20)
                self.assertEqual(len(d['requests']), 20)
                self.assertEqual(d['requests'][0]['ScheduledOffsetNs'], 0)
        finally:
            server.shutdown()
            server.server_close()


if __name__ == '__main__':
    unittest.main()
