#!/usr/bin/env python3
"""Create an isolated, sealed Intel host02 V31 handoff. Never collect traffic."""
import argparse
import ast
import copy
import difflib
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / 'replication/intel_v31'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def replace_function(source, name, replacement):
    matches = [n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name == name]
    if len(matches) != 1:
        raise ValueError('ambiguous source adaptation: ' + name)
    node = matches[0]
    lines = source.splitlines(keepends=True)
    return ''.join(lines[:node.lineno - 1]) + replacement.rstrip() + '\n' + ''.join(lines[node.end_lineno:])


def function(template, name):
    source = (TEMPLATES / template).read_text()
    node = next(n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name == name)
    return '\n'.join(source.splitlines()[node.lineno - 1:node.end_lineno])


def build(output, image_archive):
    if output.exists():
        raise ValueError('preserve existing package directory; choose a new staging path')
    sys.path[:0] = [str(ROOT / 'diagnostic'), str(ROOT / 'scripts'), str(ROOT / 'analysis')]
    import v31_common as original
    original.verify_seal(ROOT / 'analysis/runtime_io_v31/generation-01/bundle')
    science = original.design()
    retained = original.read(ROOT / 'analysis/runtime_io_v31/generation-01/bundle/manifest.json')
    protected = original.read(ROOT / 'analysis/runtime_io_slo_decision/20261011/protected_current_sha256.json')
    for name, expected in protected.items():
        if digest(ROOT / name) != expected:
            raise ValueError('protected current file changed: ' + name)
    output.mkdir(parents=True)
    # Stage sources first; after adaptations retain their static local import closure.
    for folder in ('diagnostic', 'scripts', 'analysis'):
        (output / folder).mkdir()
        for path in (ROOT / folder).glob('*.py'):
            shutil.copy2(path, output / folder / path.name)
    for name in ('main.go', 'main_test.go', 'go.mod', 'parallelism_clock.go', 'parallelism_clock_test.go'):
        target = output / 'diagnostic/v27r2_loadgen' / name
        target.parent.mkdir(exist_ok=True)
        shutil.copy2(ROOT / 'diagnostic/v27r2_loadgen' / name, target)
    assets = output / 'assets'
    assets.mkdir()
    binary = assets / 'binaries'
    binary.mkdir()
    bundle = ROOT / 'analysis/runtime_io_v31/generation-01/bundle'
    for name in ('gate', 'loadgen', 'image.server', 'publication_source.go', 'publication_build.json', 'counter'):
        shutil.copy2(bundle / name, binary / name)
    shutil.copytree(bundle / 'client_build', assets / 'client_build')
    # Historical functional fixtures are software inputs, never calibration
    # or host02 measurements. Adaptation occurs only in test temporary dirs.
    historical_cases = ROOT / 'analysis/runtime_io_v31/generation-01/preparation/functional'
    for folder in sorted(historical_cases.iterdir()):
        original.verify_seal(folder)
        target = assets / 'software_fixtures' / folder.name
        target.mkdir(parents=True)
        for file in folder.glob('*.json'):
            if file.name != 'seal.json':
                shutil.copy2(file, target / file.name)
    save(assets / 'software_fixtures/role.json', dict(role='historical host01 functional software fixtures only',
        host02_measurements=False, fresh_calibration_inputs=False))
    shutil.copy2(image_archive, assets / 'service-image.tar')
    save(assets / 'original_complete_design.json', science)
    transferred = copy.deepcopy(science)
    transferred['secondary_models'].append('ordinary_complete_response_cdf')
    for cfg in transferred['calibration_configs'] + transferred['validation_configs']:
        cfg['cpus'] = [2, 3]
    transferred['host_transfer'] = dict(host_id='host02', cpu='Intel Core i5-10300H',
        server_cpus=[2, 3], control_cpus=[0, 1], new_host_resource_baseline=True,
        secondary_comparator='all offers from the four timing calibration cohorts; failed offers are misses',
        response_pool_trimmed=False, science_changed_except_secondary_comparator=False,
        runtime_qualification_pending=True)
    design = assets / 'scientific_design'
    shutil.copytree(original.DESIGN / 'schedules', design / 'schedules')
    save(design / 'design.json', transferred)
    original.seal(design)
    identity = {k: retained[k] for k in ('image', 'server_sha256', 'loadgen_sha256', 'gate_sha256', 'counter_sha256')}
    identity.update(retained_bundle_seal=digest(bundle / 'seal.json'),
        retained_design_seal=digest(original.DESIGN / 'seal.json'),
        image_archive_sha256=digest(assets / 'service-image.tar'),
        original_complete_design_sha256=digest(assets / 'original_complete_design.json'))
    save(assets / 'retained_identity.json', identity)
    adaptations = {}

    def adapt(name, transformer):
        path = output / name
        before = path.read_text()
        after = transformer(before)
        ast.parse(after)
        path.write_text(after)
        adaptations[name] = dict(original_sha256=hashlib.sha256(before.encode()).hexdigest(),
                                 adapted_sha256=digest(path))

    def once(text, before, after):
        if text.count(before) != 1:
            raise ValueError('unexpected adaptation anchor: ' + before[:80])
        return text.replace(before, after)

    def common(text):
        for name in ('design', 'source_hashes', 'owned_directory'):
            text = replace_function(text, name, '# Moved to declared host02 apparatus overrides below.')
        return text + '\n\n' + (TEMPLATES / 'common_overrides.py').read_text()
    adapt('diagnostic/v31_common.py', common)

    def study(text):
        text = replace_function(text, 'prepare_offline', function('bundle_overrides.py', 'prepare_offline'))
        needle = "try:\n            service.create();c.save(d/'observed.json',dict(gate_released=False,performance_run=False,limits=service.expected_limits))"
        replacement = "try:\n            service.create()\n            manifest['resource_baseline']=c.read(d/'initial.json')['resource_baseline']\n            c.save(out/'manifest.json',manifest)\n            c.save(d/'observed.json',dict(gate_released=False,performance_run=False,limits=service.expected_limits))"
        return once(text, needle, replacement)
    adapt('diagnostic/v31_study.py', study)

    def verifier(text):
        text = replace_function(text, 'verify_bundle', function('bundle_overrides.py', 'verify_bundle'))
        return once(text, "('image','server_sha256','loadgen_sha256','gate_sha256','resource_baseline','sources','design_seal')",
                          "('image','server_sha256','loadgen_sha256','gate_sha256','sources','design_seal')")
    adapt('diagnostic/v31_verify.py', verifier)

    def service(text):
        text = once(text, "LABEL = 'research.v31.owner'", "LABEL = 'research.v31.host02.owner'")
        text = once(text, "self.container = 'quota-v31-'", "self.container = 'quota-v31-host02-'")
        text = once(text, "os.sched_getaffinity(self.pid) != {2, 4}", "os.sched_getaffinity(self.pid) != {2, 3}")
        needle = "        c.validate_resources(limits, inspect['HostConfig'], self.manifest['resource_baseline'], self.config)"
        return once(text, needle,
            "        if self.manifest['resource_baseline'] is None:\n"
            "            if self.directory != self.session/'preparation/resource_preflight':\n"
            "                raise ValueError('only unreleased preflight may establish host defaults')\n"
            "            self.manifest['resource_baseline']=c.resource_baseline(limits,inspect['HostConfig'],self.config)\n" + needle)
    adapt('diagnostic/v31_service.py', service)
    adapt('diagnostic/v31_campaign.py', lambda text: once(text,
        "PARENT=c.ROOT/'analysis/runtime_io_v31_campaign'", "PARENT=c.ROOT/'runs/host02/campaign'"))
    adapt('diagnostic/v31_raw.py', lambda text: once(text, "s['affinity'] != [2,4]", "s['affinity'] != [2,3]"))
    # Only the live thread-snapshot primitive changes; unused tracing methods remain historical.
    adapt('diagnostic/kernel_service_bridge.py', lambda text: replace_function(text, 'snapshot',
        function_from_source(ROOT / 'diagnostic/kernel_service_bridge.py', 'snapshot').replace('{2,4}', '{2,3}').replace('affinity=[2,4]', 'affinity=[2,3]')))
    adapt('scripts/experiment.py', lambda text: replace_function(replace_function(text, 'check_topology',
        "def check_topology():\n    from host02_platform import check_topology as check\n    return check()"), 'temperatures',
        "def temperatures():\n    from host02_platform import temperatures as read\n    return read()"))
    adapt('diagnostic/v29_monitor.py', lambda text: replace_function(text, 'get_temperatures',
        "def get_temperatures():\n    from host02_platform import temperatures\n    return temperatures()"))

    def model(text):
        text = once(text, "PRIMARY='joint_calibration_cdf'", "PRIMARY='joint_calibration_cdf'\nRESPONSE='ordinary_complete_response_cdf'")
        text = once(text, 'paired=[];cohorts={};contract=', 'paired=[];cohorts={};complete=[];contract=')
        text = once(text, "        for r in requests:\n            if not r['success']", "        complete.extend(dict(trial=trial,id=r['id'],success=r['success'],e2e_ns=r['e2e_ns']) for r in requests)\n        for r in requests:\n            if not r['success']")
        text = once(text, "        timing_trial_count=len(cohorts)", "        complete_response_samples=complete,complete_response_offers=len(complete),\n        complete_response_failures=sum(not r['success'] for r in complete),\n        complete_response_membership_difference=[dict(trial=r['trial'],id=r['id']) for r in complete\n            if (r['trial'],r['id']) not in {(s['trial'],s['id']) for s in paired}],\n        timing_trial_count=len(cohorts)")
        text = once(text, "    for method,label in (('busy',FLUID)",
            "    vectors[RESPONSE]={str(ms):[complete_probability(cal['complete_response_samples'],ms)]*len(offsets) for ms in c.DEADLINES_MS}\n    for method,label in (('busy',FLUID)")
        text += '\n\ndef complete_probability(samples,ms):\n'
        text += "    if not samples:raise ValueError('complete calibration response pool must be nonempty')\n"
        text += "    for r in samples:\n        if r['success'] and (r['e2e_ns'] is None or not math.isfinite(r['e2e_ns']) or r['e2e_ns']<0):raise ValueError('invalid complete response sample')\n"
        text += "    return sum(not r['success'] or r['e2e_ns']>ms*1000000 for r in samples)/len(samples)\n"
        return text
    adapt('diagnostic/v31_model.py', model)

    test = (output / 'diagnostic/test_v31.py').read_text()
    test = test.replace("self.assertEqual(v31_service.LABEL,'research.v31.owner')", "self.assertEqual(v31_service.LABEL,'research.v31.host02.owner')")
    test = once(test, "        import v30_common as prior\n        for a,b in zip(c.calibration_configs(),prior.calibration_configs()):\n            self.assertEqual(dict(a,trial=b['trial']),b)",
        "        original=c.read(c.ROOT/'assets/original_complete_design.json')\n        for a,b in zip(c.calibration_configs(),original['calibration_configs']):\n            self.assertEqual(dict(a,cpus=[2,4]),b)")
    test = once(test, "paired_samples=samples,\n            capacity_sensitivity", "paired_samples=samples,complete_response_samples=[dict(success=True,e2e_ns=r['total_ns']) for r in samples],\n            capacity_sensitivity")
    (output / 'diagnostic/test_v31_host02_science.py').write_text(test)
    shutil.copy2(TEMPLATES / 'test_host02.py', output / 'diagnostic/test_v31_host02_apparatus.py')
    shutil.copy2(TEMPLATES / 'platform_helpers.py', output / 'scripts/host02_platform.py')
    shutil.copy2(TEMPLATES / 'host02_cli.py', output / 'scripts/host02_cli.py')
    shutil.copy2(TEMPLATES / 'return_results.py', output / 'scripts/return_results.py')
    for name in ('setup_v31_host02.sh', 'start_v31_host02.sh'):
        shutil.copy2(TEMPLATES / name, output / name)
    shutil.copy2(TEMPLATES / 'README.md', output / 'README.md')

    # Recursively retain only repository modules imported by the intended entry points.
    search = [output / folder for folder in ('diagnostic', 'scripts', 'analysis')]
    seeds = [output / 'diagnostic' / name for name in
        ('v31_study.py', 'v31_campaign.py', 'v31_service.py', 'v29_monitor.py',
         'leftover_observer_audit.py', 'leftover_observer_review.py',
         'test_v31_host02_science.py', 'test_v31_host02_apparatus.py')]
    seeds += [output / 'scripts' / name for name in ('host02_cli.py', 'return_results.py')]
    keep = set()
    todo = list(seeds)
    while todo:
        path = todo.pop()
        if path in keep:
            continue
        keep.add(path)
        for node in ast.walk(ast.parse(path.read_text())):
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module] if isinstance(node, ast.ImportFrom) and node.module else []
            for name in names:
                for parent in search:
                    candidate = parent / (name.split('.')[0] + '.py')
                    if candidate.exists():
                        todo.append(candidate)
                        break
    for parent in search:
        for path in parent.glob('*.py'):
            if path not in keep:
                path.unlink()  # These are only files just staged into a new output.
    source_files = sorted(str(p.relative_to(output)) for p in keep)
    source_files += ['setup_v31_host02.sh', 'start_v31_host02.sh']
    save(output / 'adaptations.json', adaptations)
    diffs = []
    for name in adaptations:
        diffs += list(difflib.unified_diff((ROOT / name).read_text().splitlines(True),
            (output / name).read_text().splitlines(True), fromfile='historical/' + name, tofile='host02/' + name))
    (output / 'adaptations.patch').write_text(''.join(diffs))
    save(output / 'package.json', dict(schema=1, package_name=output.name, date='2026-10-19',
        apparatus_revision='cpuset01',
        expected_host='Intel i5-10300H, native Ubuntu, reported sibling pairs',
        source_files=source_files, retained_identity=identity, protected_current_sha256=protected,
        independent_replication_received=False, runtime_qualified=False,
        original_data_copied_as_new_calibration=False, observer_methods_reopened=False,
        primary_contract_unchanged=True, secondary_complete_response_comparator_predeclared=True))
    seal_package(output)
    for p in keep:
        ast.parse(p.read_text(), filename=str(p))
    for name in ('setup_v31_host02.sh', 'start_v31_host02.sh'):
        subprocess.run(['bash', '-n', str(output / name)], check=True)
    check = subprocess.run([sys.executable, '-B', str(output / 'scripts/host02_cli.py'), 'verify-package'],
                           cwd=output, capture_output=True, text=True, timeout=60)
    if check.returncode:
        raise ValueError(check.stdout + check.stderr)
    tests = subprocess.run([sys.executable, '-B', '-m', 'unittest', 'discover', '-s', 'diagnostic',
                            '-p', 'test_v31_host02*.py', '-v'], cwd=output,
                           capture_output=True, text=True, timeout=180)
    (output / 'offline-tests.stdout').write_text(tests.stdout)
    (output / 'offline-tests.stderr').write_text(tests.stderr)
    if tests.returncode:
        raise ValueError('Offline test failure:\n' + tests.stdout + tests.stderr)
    # Preparing a temporary bundle exports schedules only, never starts Docker/workloads.
    prepare = subprocess.run([sys.executable, '-B', 'diagnostic/v31_study.py', 'prepare-offline',
        '--directory', str(output / 'runs/host02/study/generation-01')], cwd=output,
        capture_output=True, text=True, timeout=300)
    (output / 'offline-prepare.stdout').write_text(prepare.stdout)
    (output / 'offline-prepare.stderr').write_text(prepare.stderr)
    if prepare.returncode:
        raise ValueError('Offline preparation failure:\n' + prepare.stdout + prepare.stderr)
    shutil.rmtree(output / 'runs')  # Remove only this builder's just-created software-check bundle.
    for name, expected in protected.items():
        if digest(ROOT / name) != expected:
            raise ValueError('protected file changed during handoff preparation: ' + name)
    save(output / 'offline-validation.json', dict(source_syntax_passed=True, shell_syntax_passed=True,
        unit_tests_passed=True, full_compiled_export_and_bundle_replay_passed=True,
        no_containers_started=True, host02_runtime_qualified=False,
        protected_current_files_unchanged=True))
    seal_package(output)
    print('Package prepared and offline checked at ' + str(output))


def function_from_source(path, name):
    source = path.read_text()
    node = next(n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name == name)
    return '\n'.join(source.splitlines()[node.lineno - 1:node.end_lineno])


def seal_package(output):
    save(output / 'package_seal.json', dict(files_sha256={str(p.relative_to(output)): digest(p)
        for p in sorted(output.rglob('*')) if p.is_file() and p.name != 'package_seal.json'
        and 'runs' not in p.relative_to(output).parts and '__pycache__' not in p.parts}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--image-archive', type=Path, required=True)
    args = parser.parse_args()
    build(args.output.absolute(), args.image_archive.absolute())


if __name__ == '__main__':
    main()
