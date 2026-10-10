"""Retrospective deadline sensitivity of V28's unchanged capacity estimates.

No refitting, new service execution, quota-phase inference or prospective claim.
Writes only a new extension directory; refuses to replace an existing report.
"""
import argparse
from collections import deque
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'diagnostic'))
import v28_common as c

DEADLINES_MS = (25, 50, 100, 200, 500, 1000)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def forecast_latencies(offsets, capacity):
    """Original finite FIFO contract; None represents a rejected offer."""
    pending = deque()
    end = 0.0
    result = []
    for stamp in offsets:
        arrival = stamp / 1e9
        while pending and pending[0] <= arrival:
            pending.popleft()
        if len(pending) >= 129:
            result.append(None)
            continue
        end = max(arrival, end) + 1 / capacity
        pending.append(end)
        result.append((end - arrival) * 1e9)
    return result


def miss_pct(latencies, deadline_ns):
    return 100 * sum(x is None or x > deadline_ns for x in latencies) / len(latencies)


def close(actual, expected):
    if not math.isclose(actual, expected, abs_tol=1e-8, rel_tol=1e-10):
        raise ValueError(f'Original 500 ms result differs: {actual} vs {expected}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    extension_root = (ROOT / 'analysis' / 'runtime_io_v2_extension').resolve()
    if extension_root not in output.parents or output.exists():
        raise ValueError('Use a new directory below analysis/runtime_io_v2_extension')

    session = c.PARENT / 'generation-01'
    latest = c.read(session / 'latest_analysis.json')
    original = c.resolve(session, latest['path'])
    c.verify_seal(original)
    if c.digest(original / 'seal.json') != latest['seal']:
        raise ValueError('Original analysis seal differs')
    report = c.read(original / 'report.json')
    design = c.design()
    protected = {}

    def remember(path):
        protected[str(path.relative_to(ROOT))] = digest(path)

    # Verify all declared input files, then check preservation again after reading.
    for directory in (original, c.DESIGN, ROOT / 'paper'):
        for path in directory.rglob('*'):
            if path.is_file():
                remember(path)
    rows = []
    for cfg in c.validation_configs():
        reference = report['trial_refs'][cfg['trial']]
        trial = c.resolve(session, reference['path'])
        c.verify_seal(trial)
        if c.digest(trial / 'seal.json') != reference['seal']:
            raise ValueError('Validation trial seal differs')
        for path in trial.rglob('*'):
            if path.is_file():
                remember(path)
        client = c.read(trial / 'loadgen.json')
        offsets = c.validate_client(client, cfg)
        actual = [None] * len(offsets)
        for request in client['requests']:
            if not request['Error'] and request['StatusCode'] == 200:
                actual[request['ID']] = request['EndToEndLatencyNs']
        predictions = {
            name: forecast_latencies(offsets, method['capacity_rps'])
            for name, method in report['calibration']['methods'].items()
            if method['status'] == 'available'
        }
        for deadline in DEADLINES_MS:
            observed = miss_pct(actual, deadline * 1_000_000)
            for name, predicted_latencies in predictions.items():
                predicted = miss_pct(predicted_latencies, deadline * 1_000_000)
                row = dict(trial=cfg['trial'], block=cfg['block'],
                           burst_cycle_sec=cfg['burst_period_sec'], low_rate=cfg['low_rate'],
                           offers=len(offsets), deadline_ms=deadline, method=name,
                           observed_miss_pct=observed, predicted_miss_pct=predicted,
                           signed_error_pp=predicted-observed,
                           absolute_error_pp=abs(predicted-observed))
                if deadline == 500:
                    saved = next(x for x in report['result']['methods'][name]['errors']
                                 if x['trial'] == cfg['trial'])
                    close(observed, saved['observed_miss_pct'])
                    close(predicted, saved['predicted_miss_pct'])
                    close(row['absolute_error_pp'], saved['deadline_error_pp'])
                rows.append(row)
    summary = []
    for deadline in DEADLINES_MS:
        for name in predictions:
            selected = [r for r in rows if r['deadline_ms'] == deadline and r['method'] == name]
            summary.append(dict(deadline_ms=deadline, method=name,
                                trial_count=len(selected),
                                observed_mean_miss_pct=statistics.mean(r['observed_miss_pct'] for r in selected),
                                deadline_mae_pp=statistics.mean(r['absolute_error_pp'] for r in selected),
                                maximum_error_pp=max(r['absolute_error_pp'] for r in selected),
                                mean_signed_error_pp=statistics.mean(r['signed_error_pp'] for r in selected)))
    if any(digest(ROOT / name) != expected for name, expected in protected.items()):
        raise ValueError('A protected input changed during this audit')
    output.mkdir(parents=True)
    result = dict(status='retrospective_discovery_only',
                  original_report=str(original / 'report.json'),
                  original_analysis_seal_sha256=latest['seal'],
                  deadlines_ms=list(DEADLINES_MS), calibration_refitted=False,
                  fresh_trials=0, original_500ms_results_reproduced=True,
                  input_seals_checked=True, protected_inputs_unchanged=True,
                  capacities_rps={name: value['capacity_rps'] for name, value in report['calibration']['methods'].items()
                                  if value['status'] == 'available'},
                  summary=summary, per_trial=rows,
                  limitations=[
                      'Deadline grid selected after V28 outcomes were known; no new prospective evidence.',
                      'No quota phase or per-request CPU attribution is inferred from these observations.',
                      'Errors can reflect queue timing, runtime/HTTP delay, capacity drift or quota supply timing.',
                      'Six alternative endpoints are exploratory; original 3 pp screen is not a new acceptance rule.',
                      'No confidence intervals or practical decision threshold are selected by this audit.',
                      'One application, host and quota; four historical validation blocks.'])
    (output / 'report.json').write_text(json.dumps(result, indent=2) + '\n')
    (output / 'input_hashes.json').write_text(json.dumps(protected, indent=2) + '\n')
    lines = ['# Retrospective deadline-resolution audit', '',
             'Unchanged V28 calibrations; 16 retained validation trials. No new collection or fitting.',
             'Alternate deadlines were selected after the original results; these are discovery diagnostics.', '',
             '| Deadline ms | Whole MAE pp | Busy MAE pp | Quadratic MAE pp | Busy maximum error pp |',
             '|---:|---:|---:|---:|---:|']
    for deadline in DEADLINES_MS:
        by_name = {r['method']: r for r in summary if r['deadline_ms'] == deadline}
        lines.append(f"| {deadline} | {by_name['whole']['deadline_mae_pp']:.3f} | "
                     f"{by_name['busy']['deadline_mae_pp']:.3f} | {by_name['quadratic']['deadline_mae_pp']:.3f} | "
                     f"{by_name['busy']['maximum_error_pp']:.3f} |")
    lines += ['', 'All original 500 ms forecasts/outcomes reproduce. Consumed trial seals and design hashes pass.',
              'The manuscript and consumed historical inputs retain their hashes.', '',
              'This audit does not identify an error mechanism, establish novelty, or validate a new forecast.',
              'See report.json for all five methods, per-trial errors and limitations.']
    (output / 'report.md').write_text('\n'.join(lines) + '\n')
    manifest = {p.name: digest(p) for p in output.iterdir() if p.is_file()}
    manifest['analysis_script'] = digest(Path(__file__))
    (output / 'output_hashes.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
