import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
spec = importlib.util.spec_from_file_location('analysis_v2', ROOT / 'analysis/analyze_v2.py')
analysis = importlib.util.module_from_spec(spec)
spec.loader.exec_module(analysis)
spec2 = importlib.util.spec_from_file_location('experiment', ROOT / 'scripts/experiment.py')
exp = importlib.util.module_from_spec(spec2)
spec2.loader.exec_module(exp)


class AnalysisTests(unittest.TestCase):
    def test_complete_design_and_exclusion_of_pilot(self):
        with tempfile.TemporaryDirectory(prefix='quota-analysis-test-') as tmp:
            session = Path(tmp)
            rows = exp.matrix({'iterations': 40000, 'moderate_rps': 50, 'high_rps': 85})
            exp.write_json(session / 'matrix.json', rows)
            # Data here are artificial fixtures, not experimental measurements.
            for index, cfg in enumerate(rows):
                d = {'config': cfg, 'quality_flags': [],
                     'loadgen_metrics': {'end_to_end_latency_summary': {'p99_ms': 6 + index / 100,
                          'p50_ms': 4, 'p95_ms': 5}, 'successful_throughput_rps': cfg['rate'], 'total_errors': 0, 'total_503': 0},
                     'cgroup_metrics': {'cpu_usage_cores': .4, 'throttling_fraction': .1}}
                exp.write_json(session / 'raw' / cfg['run_id'] / 'result.json', d)
            exp.write_json(session / 'pilot' / 'do_not_include' / 'result.json', {'invalid': True})
            analysis.main(session)
            self.assertEqual(len((session / 'processed/summary.csv').read_text().splitlines()), 301)
            self.assertTrue((session / 'processed/regression.txt').is_file())
            self.assertTrue((session / 'processed/latency_high.png').is_file())
