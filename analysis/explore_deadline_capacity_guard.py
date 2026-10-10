"""Read sealed V28 records and write a NEW, explicitly retrospective analysis.

No original results, source seals, prediction files or paper are modified.
This program contains no collector, service launcher, subprocess, or network.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'diagnostic'))
import v28_common as historical
from deadline_capacity_guard import diagnose, fifo, fit_reference


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def confusion(rows, field):
    admitted = [x for x in rows if x[field] == 'accept_conditional']
    flagged = [x for x in rows if x[field] == 'flag_for_recalibration']
    return dict(accepted=len(admitted), flagged=len(flagged),
                abstained=len(rows)-len(admitted)-len(flagged),
                inaccurate_accepted=sum(x['observed_error_pp'] > 3 for x in admitted),
                inaccurate_flagged=sum(x['observed_error_pp'] > 3 for x in flagged),
                accurate_flagged=sum(x['observed_error_pp'] <= 3 for x in flagged),
                accurate_accepted=sum(x['observed_error_pp'] <= 3 for x in admitted))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.absolute()
    allowed = ROOT/'analysis/runtime_io_deadline_guard_exploration'
    if output.parent != allowed or output.is_symlink() or output.exists():
        raise ValueError('use a fresh direct child of analysis/runtime_io_deadline_guard_exploration')
    session = historical.PARENT/'generation-01'
    latest = read(session/'latest_analysis.json')
    original = historical.resolve(session, latest['path'])
    historical.verify_seal(original)
    historical.verify_seal(session/'predictions')
    # The original design's source and schedule checks remain authoritative.
    historical.design()
    report = read(original/'report.json')
    rows = report['trial_accounting']
    anchors = [r for r in rows if r['role']=='mixed' and r['block']==1]
    discrepancy = [r for r in rows if r['role']=='mixed' and r['block']==2]
    schedules = {cfg['trial']: historical.schedule(cfg) for cfg in historical.calibration_configs()}
    reference = fit_reference(anchors, discrepancy, schedules)
    estimates = report['calibration']['methods']
    # Commit all diagnostic decisions before reading validation outcomes into
    # evaluation. This structural separation is NOT a historical preregistration.
    decisions = []
    for cfg in historical.validation_configs():
        schedule = historical.schedule(cfg)
        for method, estimate in estimates.items():
            if estimate['status'] != 'available':
                raise ValueError('preserve unavailable method rather than silently dropping it')
            guard = diagnose(schedule, estimate['capacity_rps'], reference['reference_capacity_rps'], reference['margin_pp'])
            lo, hi = reference['reference_capacity_rps']
            gap = max(abs(estimate['capacity_rps']/x-1)*100 for x in (lo, hi))
            point = guard['point_forecast']['miss_pct']
            cal_errors = [abs(fifo(schedules[r['trial']], estimate['capacity_rps'])['miss_pct']-r['miss_pct']) for r in discrepancy]
            decisions.append(dict(trial=cfg['trial'], block=cfg['block'], method=method,
                                  period_sec=cfg['burst_period_sec'], low_rate=cfg['low_rate'], guard=guard,
                                  decision=guard['decision'],
                                  fixed_5pct_capacity_gap=('accept_conditional' if gap<=5 else 'flag_for_recalibration'),
                                  unpadded_forecast_gap=('accept_conditional' if guard.get('forecast_disagreement_pp', float('inf'))<=3 else 'flag_for_recalibration'),
                                  calibration_error_only=('accept_conditional' if max(cal_errors)<=3 else 'flag_for_recalibration')))
    predictions = read(session/'predictions/summary.json')
    observed = {r['trial']:r for r in rows if r['role']=='validation'}
    for d in decisions:
        saved = predictions[d['method']][d['trial']]['miss_pct']
        point = d['guard']['point_forecast']['miss_pct']
        if abs(point-saved)>1e-9:
            raise ValueError('rational FIFO differs from historical floating-point forecast; retain and investigate')
        row = observed[d['trial']]
        d['observed_miss_pct'] = row['miss_pct']
        d['observed_error_pp'] = abs(point-row['miss_pct'])
        lo, hi = reference['reference_capacity_rps']
        a, b = row['busy_capacity_bounds_rps']
        d['validation_busy_bounds_inside_reference_range'] = lo<=a<=b<=hi
    summary = {}
    for method in estimates:
        selected = [d for d in decisions if d['method']==method]
        summary[method] = {field:confusion(selected, field) for field in
                           ('decision','fixed_5pct_capacity_gap','unpadded_forecast_gap','calibration_error_only')}
    inputs = {str(p.relative_to(ROOT)):sha(p) for p in
              (original/'report.json', original/'seal.json', session/'predictions/seal.json',
               session/'predictions/summary.json', session/'latest_analysis.json')}
    sources = {str(p.relative_to(ROOT)):sha(p) for p in
               (Path(__file__), ROOT/'analysis/deadline_capacity_guard.py', ROOT/'analysis/test_deadline_capacity_guard.py')}
    result = dict(study='deadline guard retrospective development on V28',
                  created_utc=datetime.now(timezone.utc).isoformat(), prospective_validation=False,
                  novelty_established=False, scientific_collection_started=False,
                  rule_developed_after_V28_outcomes_known=True, reference=reference,
                  summaries=summary, decisions=decisions,
                  distinct_validation_schedules=4, validation_blocks=4,
                  reference_coverage_trials=sum(d['validation_busy_bounds_inside_reference_range'] for d in decisions if d['method']=='busy'),
                  input_sha256=inputs, source_sha256=sources,
                  limitations=['Empirical reference range and residual maximum have no statistical future coverage.',
                               'All V28 outcomes were previously known; calibration separation does not undo that.',
                               'Requires backlogged reference probes; measurement savings have not been demonstrated.',
                               'Five estimators on sixteen shared trials are not eighty independent samples.',
                               'Published load-dependent and adaptive-selection algorithms have not been reproduced.',
                               'Quota stalls, request-entry effects and varying effective capacity are omitted.'])
    output.mkdir(parents=True, exist_ok=False)
    (output/'report.json').write_text(json.dumps(result, indent=2)+'\n')
    (output/'decisions_before_outcome_evaluation.json').write_text(json.dumps(
        [dict(trial=d['trial'], method=d['method'], guard=d['guard']) for d in decisions], indent=2)+'\n')
    if any(sha(ROOT/name)!=digest for name,digest in inputs.items()):
        raise ValueError('historical input changed during exploration')
    files = {p.name:sha(p) for p in output.iterdir() if p.is_file()}
    (output/'seal.json').write_text(json.dumps(dict(files_sha256=files), indent=2)+'\n')
    print(json.dumps(dict(output=str(output), reference=reference, summaries=summary,
                         reference_coverage_trials=result['reference_coverage_trials']), indent=2))


if __name__ == '__main__':
    main()
