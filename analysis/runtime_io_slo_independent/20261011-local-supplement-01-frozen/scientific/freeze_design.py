#!/usr/bin/env python3
"""Freeze offline design/evaluator/schedules only; never collect or launch a service."""
import argparse
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path(__file__).resolve().parent
PROTOCOL = ROOT / 'docs/runtime_io_slo_independent_protocol_20261011.md'
GO_BASE = ROOT / 'handoff/v31-host02-intel-20261011'
NGINX_BASE = ROOT / 'analysis/runtime_io_nginx_feasibility/generation-02'
ORDERS = ['ABC', 'BCA', 'CAB', 'ACB', 'CBA', 'BAC']


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as handle:
        json.dump(value, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write('\n')


def go_vector(cfg):
    if cfg['traffic_pattern'] == 'idle':
        return []
    duration = Fraction(str(cfg['duration_sec']))
    i, out = 0, []
    while True:
        if cfg['traffic_pattern'] == 'steady':
            seconds = Fraction(i) / Fraction(str(cfg['rate']))
        else:
            low, high = Fraction(str(cfg['burst_low'])), Fraction(str(cfg['burst_high']))
            period, low_duration = Fraction(str(cfg['burst_period_sec'])), Fraction(str(cfg['burst_low_duration_sec']))
            count = low * low_duration + high * (period - low_duration)
            cycle = Fraction(i) // count
            within = Fraction(i) - cycle * count
            seconds = cycle * period + (within / low if within < low * low_duration else
                       low_duration + (within - low * low_duration) / high)
        exact = seconds * 10**9
        rounded = (2 * exact.numerator + exact.denominator) // (2 * exact.denominator)
        if rounded >= duration * 10**9:
            return out
        out.append(rounded)
        i += 1


def warmup_config(cfg):
    low = cfg['low_rate']
    return dict(cfg, duration_sec=20,
                traffic_pattern='idle' if cfg['traffic_pattern']=='idle' else 'steady',
                rate=low, burst_low=low, burst_high=low)


def go_schedules(output, design):
    binary = GO_BASE / 'assets/binaries/loadgen'
    require(sha(binary) == design['loadgen_sha256'], 'retained Go client changed')
    counts, checks = {}, []
    for cfg in design['calibration_configs'] + design['validation_configs']:
        for phase in ('warmup', 'measurement'):
            selected = warmup_config(cfg) if phase=='warmup' else cfg
            name = cfg['trial'] + '_' + phase
            path = output / 'schedules/go' / (name + '.json')
            vector = go_vector(selected)
            path.parent.mkdir(parents=True, exist_ok=True)
            if selected['traffic_pattern'] == 'idle':
                write(path, vector)
            else:
                argv = [str(binary), '-duration', str(selected['duration_sec']) + 's',
                    '-rate', str(selected['rate']), '-pattern', selected['traffic_pattern'],
                    '-burst-low', str(selected['burst_low']), '-burst-high', str(selected['burst_high']),
                    '-burst-period', str(selected['burst_period_sec']) + 's',
                    '-burst-low-duration', str(selected['burst_low_duration_sec']) + 's',
                    '-schedule-output', str(path)]
                result = subprocess.run(argv, capture_output=True, text=True, timeout=10)
                require(result.returncode == 0, 'offline Go schedule export failed: ' + result.stderr)
                require(json.loads(path.read_text()) == vector, 'compiled and rational schedule mismatch')
                checks.append(name)
            # A separate exported historical vector validates the regenerated
            # oracle without reading a single historical response outcome.
            retained = GO_BASE / 'assets/scientific_design/schedules' / (name + '.json')
            if retained.exists():
                require(json.loads(retained.read_text()) == vector, 'retained offered offsets differ')
            counts[name] = len(vector)
    return counts, checks


def nginx_schedules(output):
    intervals = dict(A=250000000, B=166666667, C=125000000)
    rows = []
    for i, profile in enumerate('ABC', 1):
        rows.append(dict(id='qualification_' + profile, role='qualification', profile=profile,
                         interval_ns=intervals[profile], count=100, warmup_count=25))
    for i in range(1, 5):
        rows.append(dict(id='calibration_' + str(i), role='calibration', profile=None,
                         interval_ns=200000000, count=400, warmup_count=25))
    for block, order in enumerate(ORDERS, 1):
        for profile in order:
            rows.append(dict(id=f'b{block}_{profile}', role='validation', block=block,
                             profile=profile, interval_ns=intervals[profile], count=300, warmup_count=25))
    for cfg in rows:
        for phase, count in [('warmup', 25), ('measurement', cfg['count'])]:
            write(output / 'schedules/nginx' / (cfg['id'] + '_' + phase + '.json'),
                  [i * cfg['interval_ns'] for i in range(count)])
    # The retained native client lacks a no-network export mode. Inspect its
    # unchanged source for the actual integer formula rather than executing it.
    source = ROOT / 'diagnostic/nginx_client/main.go'
    require('scheduled := int64(i) * *interval' in source.read_text(), 'NGINX offset primitive changed')
    return rows


def verify_runtime_inputs():
    paths = []
    manifest_path = NGINX_BASE / 'software/manifest.json'
    manifest = json.loads(manifest_path.read_text())
    for name, expected in manifest['runtime_files_sha256'].items():
        path = NGINX_BASE / 'software/runtime' / name
        require(path.is_file() and sha(path) == expected, 'NGINX runtime dependency differs: ' + name)
        paths.append(path)
    for name, key in [('nginx', 'nginx_sha256'), ('client', 'client_sha256'),
                      ('gate', 'gate_sha256'), ('runtime.tar', 'runtime_tar_sha256')]:
        path = NGINX_BASE / 'software' / name
        require(sha(path) == manifest[key], 'NGINX retained executable/archive changed')
        paths.append(path)
    identity_path = GO_BASE / 'assets/retained_identity.json'
    identity = json.loads(identity_path.read_text())
    image_tar = GO_BASE / 'assets/service-image.tar'
    require(sha(image_tar) == identity['image_archive_sha256'], 'Go service image archive changed')
    for name, key in [('gate', 'gate_sha256'), ('loadgen', 'loadgen_sha256'),
                      ('image.server', 'server_sha256')]:
        path = GO_BASE / 'assets/binaries' / name
        require(sha(path) == identity[key], 'Go retained executable changed')
        paths.append(path)
    paths += [manifest_path, identity_path, image_tar,
              ROOT / 'diagnostic/nginx_prediction_study.py', ROOT / 'diagnostic/v31_study.py',
              ROOT / 'diagnostic/nginx_client/main.go']
    return paths, manifest, identity


def prepare(output, registered_utc):
    require(not output.exists(), 'preserve an existing freeze; use another generation')
    output.mkdir(parents=True)
    design_path = GO_BASE / 'assets/scientific_design/design.json'
    design = json.loads(design_path.read_text())
    require(design['block_orders'] == ORDERS, 'Go orders differ')
    require(len(design['calibration_configs']) == 16 and len(design['validation_configs']) == 18,
            'Go scope differs')
    counts, compiled_checks = go_schedules(output, design)
    nginx_configs = nginx_schedules(output)
    paths, nginx_manifest, go_identity = verify_runtime_inputs()
    go_cal_offers = sum(counts[x['trial'] + '_measurement'] for x in design['calibration_configs'])
    go_warmups = sum(counts[x['trial'] + '_warmup'] for x in design['calibration_configs'])
    timing = [x for x in design['calibration_configs'] if x['role'] == 'steady' and
              x['reference_low_rate'] in (15, 30)]
    go_reference = sum(counts[x['trial'] + '_measurement'] for x in timing)
    go_target = sum(counts[x['trial'] + '_measurement'] for x in design['validation_configs'])
    go_target_warmup = sum(counts[x['trial'] + '_warmup'] for x in design['validation_configs'])
    require((go_reference, go_target) == (676, 12600), 'Go acquired/reference counts differ')
    nginx_acquisition_ns = sum((x['count'] + 25) * x['interval_ns'] for x in nginx_configs)
    nginx_scheduled_sec = nginx_acquisition_ns / 1e9
    go_nominal_sec = 600 + 34 * 60 + 34 * 20 + sum(x['duration_sec'] for x in
                                                               design['calibration_configs'] + design['validation_configs'])
    go_floor = go_nominal_sec + 600 + 300 + 900 + 120 + 18
    nginx_floor = nginx_scheduled_sec + 25 * 10 + 120 + 18
    budget = dict(go=dict(cap_sec=12600, initial_idle_settling_and_scheduled_sec=go_nominal_sec,
        plus_preparation_observer_analysis_cleanup_barrier_sec=1938,
        planning_floor_sec=go_floor, nominal_headroom_sec=12600-go_floor,
        service_watchdog_sec=360, full_completion_under_maximum_waits_guaranteed=False),
        nginx=dict(cap_sec=2700, conservative_scheduled_acquisition_sec=nginx_scheduled_sec,
        settling_sec=250, cleanup_reserve_sec=120, added_barrier_allowance_sec=18,
        planning_floor_sec=nginx_floor, nominal_headroom_sec=2700-nginx_floor,
        service_watchdog_sec=120, full_completion_under_maximum_waits_guaranteed=False),
        total_cap_sec=30600, setup_engineering_included=False, planning_only=True)
    require(go_floor < 12600 and nginx_floor < 2700, 'nominal timing does not fit')
    require(go_nominal_sec == 5000, 'Go duration geometry differs')
    require(sum(x['count'] for x in nginx_configs if x['role']=='validation') == 5400,
            'NGINX target denominator differs')
    # Snapshot the original complete Go plan for fields not abbreviated below.
    shutil.copy2(design_path, output / 'retained_go_design.json')
    for name in ('evaluation.py', 'test_evaluation.py', 'freeze_design.py'):
        shutil.copy2(SOURCE / name, output / name)
    shutil.copy2(PROTOCOL, output / 'protocol.md')
    plan = dict(id='independent-slo-decision-v1', registered_utc=registered_utc,
        registration='local pre-outcome sealed specification; no third-party timestamp',
        role='future finite-window stress evaluation; no outcomes acquired by preparation',
        host_preference='pending; fixed known-host planning allocation; v2 required for change',
        hosts=[dict(id='host01', cpu='AMD Ryzen 5 5600H', go_service_cpus=[2,4],
                    nginx_service_cpus=[2], control_cpus=[0,1], order=['Go','NGINX']),
               dict(id='host02', cpu='Intel Core i5-10300H', go_service_cpus=[2,3],
                    nginx_service_cpus=[2], control_cpus=[0,1], order=['NGINX','Go'])],
        campaigns=[dict(id=f'slo_v1_{h}_{a}', host=h, application=a, planned_windows=18,
                        scientific_attempt_limit=1, previous_v31_return_used=False)
                   for h in ('host01','host02') for a in ('Go','NGINX')],
        planned_target_windows=72, independent_hardware_hosts=2, independent_iid_histories_established=False,
        primary=dict(quantile='39/40', method='reference', budget='1/20',
            event='false assurance AND forecast slack >0 AND absolute error <=1/20',
            finite_window_hardware_recurrence='at least one valid host02 primary event',
            population_risk_certification=False),
        quantiles=['9/10','19/20','39/40','99/100','199/200'],
        fixed_deadlines_ns=dict(Go=[10000000,11000000,12000000],NGINX=[20565395]),
        methods=['reference','recent25','weighted_update'],
        uncertainty='two-sided 95% IID DKW sampling illustration; no transfer guarantee',
        exact_miss_rule='failed/missing completion OR complete response ns > deadline; equality timely',
        warmup_selected_offers=25, acquired_cost_full=True,
        barrier=dict(max_availability_to_child_creation_ns=1000000000,
            anchor='validated warmup readback and drain; not final HTTP completion',
            durable_receipt_before_target_process=True, boot_identity_required=True,
            current_collectors_integrated=False),
        Go=dict(reference_offers_expected_if_qualified=go_reference,
            acquired_calibration_offers=go_cal_offers, calibration_warmup_offers=go_warmups,
            target_offers=go_target, target_warmup_offers=go_target_warmup,
            complete_reference_trials=[x['trial'] for x in timing],
            sampler_off=True, historical_outcomes_used=False,
            full_configuration='retained_go_design.json'),
        NGINX=dict(configs=nginx_configs, reference_offers=1600, calibration_warmup_offers=100,
            qualification_offers=300, qualification_warmup_offers=75, target_offers=5400,
            target_warmup_offers=450, runtime_manifest_sha256=sha(NGINX_BASE/'software/manifest.json'),
            immutable_original_image=json.loads((NGINX_BASE/'software/image.json').read_text())['id'],
            source_archive_sha256=nginx_manifest['source_archive_sha256'],
            input_sha256=nginx_manifest['runtime_files_sha256']['input/corpus.ndjson']),
        budget=budget, eligibility='protocol.md; retain partial, technical and domain-exit records',
        no_auto_retry=True, no_new_predictor=True, no_new_observer=True,
        scientific_design_frozen=True, launch_ready=False, collection_authorized=False)
    write(output / 'plan.json', plan)
    input_hashes = {str(p.relative_to(ROOT)):sha(p) for p in paths + [design_path,PROTOCOL,
        ROOT/'docs/runtime_io_slo_independent_evaluation_draft_20261011.md',
        ROOT/'docs/runtime_io_slo_contribution_review_20261011.md',
        ROOT/'docs/runtime_io_nginx_prediction_protocol_20261009.md']}
    write(output / 'input_sha256.json', input_hashes)
    write(output / 'feasibility.json', dict(scientific_design='GO within finite descriptive scope',
        collection='NO_GO until integrated isolated collector and host qualification',
        reasons=['Forecast hook absent from both current collectors',
                 'NGINX historical runner imports host01 generation/boot and resource seals',
                 'Fresh hardware availability and runtime eligibility unverified',
                 'New barrier behavioral neutrality not established or assumed'],
        static_runtime_dependency_integrity='passed', schedule_export_checks=len(compiled_checks),
        go_schedule_files=len(counts), nginx_schedule_files=50,
        schedule_export_no_network=True, timing_budget=budget,
        possible_claim='finite-window recurrence and tradeoffs; not a certified safety rate',
        prior_v31_package_changed=False, hardware_collection_started=False))
    tests = subprocess.run([sys.executable,'-B','-m','unittest','discover','-s',str(output),
                            '-p','test_evaluation.py','-v'], capture_output=True,text=True,timeout=60)
    (output/'tests.stdout').write_text(tests.stdout)
    (output/'tests.stderr').write_text(tests.stderr)
    require(tests.returncode == 0, 'frozen evaluator tests failed')
    hashes = {str(p.relative_to(output)):sha(p) for p in sorted(output.rglob('*')) if p.is_file()}
    write(output/'seal.json',dict(registered_utc=registered_utc, files_sha256=hashes,
        no_performance_collection=True, no_new_outcomes=True, launch_ready=False,
        third_party_registration=False))
    verify(output)
    print(json.dumps(dict(status='scientific_design_frozen_collection_no_go',output=str(output),
        compiled_schedule_checks=len(compiled_checks), evaluator_tests=19,
        plan_sha256=sha(output/'plan.json'), seal_sha256=sha(output/'seal.json')),indent=2))


def verify(output):
    seal = json.loads((output/'seal.json').read_text())
    actual = {str(p.relative_to(output)) for p in output.rglob('*') if p.is_file() and
              p != output/'seal.json'}
    require(actual == set(seal['files_sha256']), 'frozen file set differs')
    for name, expected in seal['files_sha256'].items():
        require(sha(output/name) == expected, 'frozen artifact differs: '+name)
    inputs = json.loads((output/'input_sha256.json').read_text())
    for name, expected in inputs.items():
        require(sha(ROOT/name)==expected, 'consumed retained input changed: '+name)
    return True


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('command',choices=['freeze','verify'])
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--registered-utc')
    args=p.parse_args()
    if args.command=='freeze':
        require(args.registered_utc is not None, 'explicit registration timestamp required')
        prepare(args.output.resolve(),args.registered_utc)
    else:
        verify(args.output.resolve())
        print('Frozen design, evaluator, schedules and retained input hashes verify; collection remains NO-GO.')
