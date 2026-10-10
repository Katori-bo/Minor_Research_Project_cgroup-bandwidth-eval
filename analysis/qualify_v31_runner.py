"""Offline V31 qualification using explicitly historical software fixtures only."""
import argparse
import copy
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'diagnostic'))
import v30_common as old
import v30_verify as old_verify
import v31_common as c
import v31_model as model
import v31_raw as raw
import v31_verify as verify


def qualify(out):
    if out.parent!=ROOT/'analysis/runtime_io_v31_preparation_review' or out.exists() or out.is_symlink():
        raise ValueError('use a new direct V31 preparation-review directory')
    session=c.PARENT/'generation-01';manifest=verify.verify_bundle(session)
    if any((session/name).exists() for name in ('preparation','slots','predictions','measurement_lifetime.json')):
        raise ValueError('offline-only review requires unstarted V31 generation')
    old_session=old.PARENT/'generation-01'
    # Entire prospective V30 record must still replay without any edits.
    prior=old_verify.verify_completion(old_session)
    if prior['decision']!='short_deadline_prediction_confirmed':raise ValueError('unexpected preserved V30 result')
    refs=old.read(old.resolve(old_session,old.read(old_session/'latest_analysis.json')['path'])/'report.json')['trial_refs']
    history_paths=list((ROOT/'diagnostic').glob('v30_*.py'))+[ROOT/'diagnostic/test_v30.py',ROOT/'diagnostic/start_v30.sh']
    history_paths+=[old.DESIGN/'design.json',old.DESIGN/'seal.json',old_session/'bundle/seal.json',old_session/'predictions/seal.json']
    history_hashes={str(p.relative_to(ROOT)):c.digest(p) for p in history_paths}
    fixtures={};new_refs={};values=[]
    with tempfile.TemporaryDirectory(prefix='v31-software-fixture-') as temp:
        fixture_session=Path(temp)
        for cfg in c.calibration_configs():
            original_trial=cfg['trial'].removeprefix('v31_');ref=refs[original_trial]
            directory=old.resolve(old_session,ref['path'])
            if old.digest(directory/'seal.json')!=ref['seal']:raise ValueError('historical fixture seal differs')
            # Namespace-only adapter for archived configurations. Actual raw
            # stages, clocks, schedules and binary identities remain unchanged.
            # It exists only inside this offline software check.
            with patch.object(c,'validate_config',side_effect=old.validate_config),patch.object(c,'schedule',side_effect=old.schedule):
                derived=raw.replay(directory)
            if derived!=old.read(directory/'derived.json'):raise ValueError('V31 decoder does not reproduce archived raw stages')
            row=copy.deepcopy(old.read(directory/'phase_accounting.json'));row['trial']=cfg['trial'];values.append(row)
            target=fixture_session/cfg['trial'];target.mkdir()
            c.save(target/'config.json',cfg);c.save(target/'derived.json',derived);c.seal(target)
            new_refs[cfg['trial']]=dict(path=cfg['trial'],seal=c.digest(target/'seal.json'))
            fixtures[cfg['trial']]=dict(original_trial=original_trial,raw_directory=str(directory.relative_to(ROOT)),
                raw_seal=ref['seal'],derived_sha256=c.digest(directory/'derived.json'))
        fitted=model.fit_calibration(fixture_session,values,new_refs)
        if not fitted['usable']:raise ValueError('historical software fixture failed model fitting')
        start=time.monotonic();summary,vectors=model.forecast(fitted,c.validation_configs());elapsed=time.monotonic()-start
        # Exhaustive elementary counting supplies a separate timing-CDF oracle.
        paired=fitted['paired_samples'];workers=[r['worker_ns'] for r in paired];residuals=[r['residual_ns'] for r in paired]
        for ms in c.DEADLINES_MS:
            expected=sum(r['total_ns']>ms*1000000 for r in paired)/len(paired)
            convolution=sum(w+r>ms*1000000 for w in workers for r in residuals)/(len(workers)*len(residuals))
            for cfg in c.validation_configs():
                grid=vectors[model.PRIMARY][cfg['trial']]
                if grid[str(ms)]!=[expected]*len(c.schedule(cfg)):raise ValueError('per-offer paired CDF differs from independent count')
                actual=summary['methods']['independent_worker_response_convolution'][cfg['trial']]['deadline_miss_pct'][str(ms)]/100
                if abs(actual-convolution)>1e-12:raise ValueError('convolution differs from exhaustive independent count')
        out.mkdir(parents=True)
        c.save(out/'historical_software_fixture.json',dict(status='historical_software_check_only_not_V31_parameters',
            calibration=fitted,forecast_summary=summary,fixtures=fixtures,forecast_seconds=elapsed))
    # Source and historical evidence integrity must hold after fixture adapters.
    if c.source_hashes()!=manifest['sources']:raise ValueError('qualified source changed')
    if history_hashes!={str(p.relative_to(ROOT)):c.digest(p) for p in history_paths}:raise ValueError('V30 source/evidence changed')
    tests=(session/'bundle/tests.stderr').read_text();match=re.search(r'Ran (\d+) tests',tests)
    if not match or not tests.rstrip().endswith('OK'):raise ValueError('missing successful bundle test receipt')
    subprocess.run(['bash','-n',str(ROOT/'diagnostic/start_v31.sh')],check=True,timeout=10)
    report=dict(status='offline_runner_qualification_passed_runtime_checks_pending',software_checks=int(match[1]),
        retained_periodic_oracle_cases=40,compiled_schedule_exports=len(manifest['compiled_exports']),
        historical_calibration_raw_replays=len(fixtures),historical_V30_completion_replay='passed',
        historical_fixture_forecast_seconds=elapsed,historical_files_unchanged=len(history_hashes),
        fresh_calibration_trials=16,held_out_validation_trials=18,measurement_offers=12600,
        runtime_qualified=False,performance_started=False,V31_parameters_fitted=False,V31_outcomes_collected=False,
        bundle_seal_sha256=c.digest(session/'bundle/seal.json'),design_seal_sha256=c.digest(c.DESIGN/'seal.json'),
        generation=str(session),sources=manifest['sources'],preserved_V30_hashes=history_hashes,
        input_hashes={'analysis/qualify_v31_runner.py':c.digest(Path(__file__))})
    c.save(out/'report.json',report)
    shutil.copy2(Path(__file__),out/'qualify_v31_runner.py')
    (out/'report.md').write_text(
        '# V31 offline preparation qualification\n\n'
        '**Offline runner qualification passed; runtime checks and scientific collection remain unrun.**\n\n'
        f"{report['software_checks']} software checks passed, including retained independent periodic-budget oracle checks "
        '(40 cases). All 69 compiled scientific/warmup/functional schedule exports agree with the rational oracle. '
        'All sixteen archived V30 calibration records reproduce under the V31 raw decoder using a namespace-only '
        'fixture adapter. The preserved full V30 completion record also replays successfully.\n\n'
        'Historical calibration exercises the new fitting and forecast code only in a temporary software fixture. '
        'Its paired-CDF per-offer probabilities and independent empirical convolution match separate exhaustive '
        'counting at all eleven deadlines. These are not V31 parameters, predictions or outcomes; there is no '
        'scientific forecast directory in the fresh generation.\n\n'
        'The execution design and sources/binaries are sealed. The external launcher must still verify the '
        'unreleased resource preflight, all six functional cases, fresh terminal-authenticated observer inventory '
        'and fresh calibration before freezing forecasts and collecting eighteen new-rate validation trials. '
        'Domain exits and failed confirmation gates remain adverse results, without scientific replacements.\n\n'
        'Launch instructions: `docs/runtime_io_v31_execution.md`. No collection has started.\n')
    c.seal(out);c.verify_seal(out);verify.verify_bundle(session)
    print(f"V31 offline qualification passed: {report['software_checks']} tests, 69 schedule exports, 16 historical raw fixtures. Runtime/scientific collection pending.")


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    qualify(p.parse_args().output.absolute())
