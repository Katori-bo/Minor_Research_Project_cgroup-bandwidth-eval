"""Host adaptation tests: quota, source integrity, topology and complete outcomes."""
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, Mock
import shutil

import v31_common as c
import v31_model as model
import v31_service as service
import v31_study as study
import v31_raw as raw
import host02_platform as hardware
import host02_cli as cli


class Host02Tests(unittest.TestCase):
    def limits(self):
        return {'cpu.max': '25000 100000', 'cpu.max.burst': '0',
                'cpuset.cpus.effective': '2-3', 'memory.max': 'max', 'pids.max': '12345'}

    def host(self):
        return dict(Memory=0, MemorySwap=0, PidsLimit=None, CpuQuota=25000,
                    CpuPeriod=100000, CpusetCpus='2,3')

    def test_original_contract_and_fresh_namespace(self):
        d = c.design()
        self.assertEqual(d['primary_deadline_ms'], 10)
        self.assertEqual(d['validation_offers'], 12600)
        self.assertEqual(c.PARENT, c.ROOT / 'runs/host02/study')
        self.assertEqual({tuple(x['cpus']) for x in c.matrix()}, {(2, 3)})
        self.assertEqual({x['period_us'] for x in c.matrix()}, {100000})
        self.assertEqual({x['quota_us'] for x in c.matrix()}, {25000})
        self.assertEqual({x['iterations'] for x in c.matrix()}, {88000})
        self.assertEqual({x['rate'] for x in c.validation_configs()}, {5, 11, 19})

    def test_complete_response_failure_and_deadline_equality(self):
        values = [dict(success=True, e2e_ns=10000000),
                  dict(success=True, e2e_ns=10000001), dict(success=False, e2e_ns=None)]
        self.assertEqual(model.complete_probability(values, 10), 2 / 3)
        self.assertEqual(model.complete_probability(values, 12), 1 / 3)
        with self.assertRaises(ValueError):
            model.complete_probability([], 10)
        with self.assertRaises(ValueError):
            model.complete_probability([dict(success=True, e2e_ns=-1)], 10)

    def test_service_command_mapping_and_no_extra_resource_limits(self):
        argv = c.service_argv('image', Path('/tmp/qualification'), 'container', c.matrix()[0])
        self.assertEqual(argv[argv.index('--cpuset-cpus') + 1], '2,3')
        self.assertEqual(argv[argv.index('--cpu-quota') + 1], '25000')
        self.assertEqual(argv[argv.index('--cpu-period') + 1], '100000')
        self.assertIn('WORKER_YIELD=0', argv)
        self.assertNotIn('--memory', argv)
        self.assertNotIn('--pids-limit', argv)

    def test_new_host_defaults_required_and_not_imported_from_original(self):
        limits, host = self.limits(), self.host()
        baseline = c.resource_baseline(limits, host, c.matrix()[0])
        c.validate_resources(limits, host, baseline, c.matrix()[0])
        for bad in (None, dict(baseline, limits=dict(limits, **{'pids.max': '18088'}))):
            with self.assertRaises(ValueError):
                c.validate_resources(limits, host, bad, c.matrix()[0])
        for field, bad in [('cpu.max', '50000 100000'), ('cpu.max.burst', '1000'),
                           ('cpuset.cpus.effective', '2,4'), ('pids.max', '10')]:
            with self.subTest(field=field), self.assertRaises(ValueError):
                c.resource_baseline(dict(limits, **{field: bad}), host, c.matrix()[0])

    def test_cpu_list_parser_accepts_lists_ranges_and_mixed_notation(self):
        for value, expected in [('2,3', {2, 3}), ('2-3', {2, 3}),
                                ('0-1,4,6-7', {0, 1, 4, 6, 7}),
                                ('3,2,2', {2, 3}), ('2-2,3\n', {2, 3})]:
            with self.subTest(value=value):
                self.assertEqual(c.parse_cpu_list(value), expected)

    def test_resource_preflight_accepts_equivalent_cpu_formats_and_keeps_raw_evidence(self):
        for effective in ('2-3', '2,3'):
            for requested in ('2,3', '2-3'):
                with self.subTest(effective=effective, requested=requested):
                    limits = dict(self.limits(), **{'cpuset.cpus.effective': effective})
                    host = dict(self.host(), CpusetCpus=requested)
                    baseline = c.resource_baseline(limits, host, c.matrix()[0])
                    self.assertEqual(baseline['limits'], limits)
                    self.assertEqual(baseline['limits']['cpuset.cpus.effective'], effective)
                    c.validate_resources(limits, host, baseline, c.matrix()[0])

    def test_resource_preflight_rejects_wrong_missing_and_malformed_cpu_sets(self):
        for value in (None, '', '2', '2,4', '2-4', '0-3', '3-2', '-2,3',
                      '2,,3', '2-', '2-3-4', '2,3,', '2:3', 'two', 23):
            with self.subTest(value=value, field='effective'), self.assertRaises(ValueError):
                c.resource_baseline(dict(self.limits(), **{'cpuset.cpus.effective': value}),
                                    self.host(), c.matrix()[0])
            with self.subTest(value=value, field='requested'), self.assertRaises(ValueError):
                c.resource_baseline(self.limits(), dict(self.host(), CpusetCpus=value), c.matrix()[0])

    def test_range_format_does_not_bypass_quota_period_or_burst_checks(self):
        for field, bad in [('cpu.max', '50000 100000'), ('cpu.max', '25000 50000'),
                           ('cpu.max.burst', '1000')]:
            with self.subTest(field=field, bad=bad), self.assertRaises(ValueError):
                c.resource_baseline(dict(self.limits(), **{field: bad}), self.host(), c.matrix()[0])
        for field, bad in [('CpuQuota', 50000), ('CpuPeriod', 50000)]:
            with self.subTest(field=field), self.assertRaises(ValueError):
                c.resource_baseline(self.limits(), dict(self.host(), **{field: bad}), c.matrix()[0])

    def test_topology_exact_siblings_and_physical_separation(self):
        topo = {str(i): dict(core=str(i % 4), package='0',
                siblings=f'{i % 4},{i % 4 + 4}') for i in range(8)}
        with patch.object(hardware, 'topology', return_value=topo):
            self.assertEqual(hardware.check_topology(), topo)
        bad = copy.deepcopy(topo)
        bad['3']['core'] = '0'
        with patch.object(hardware, 'topology', return_value=bad), self.assertRaises(RuntimeError):
            hardware.check_topology()

    def test_only_own_package_source_inventory_is_used(self):
        c.verify_package()
        source = c.source_hashes()
        self.assertIn('start_v31_host02.sh', source)
        self.assertNotIn('scripts/start_fresh.sh', source)
        self.assertNotIn('diagnostic/start_v31.sh', source)
        self.assertEqual(service.LABEL, 'research.v31.host02.owner')

    def test_monitor_counts_preserved(self):
        self.assertEqual(c.monitor_minimum(dict(duration_sec=30)), 45)
        self.assertEqual(c.monitor_minimum(dict(duration_sec=60)), 80)

    def test_supplied_host_prerequisites_accept_without_starting_a_service(self):
        import json
        import os
        identity = c.read(c.ROOT / 'assets/retained_identity.json')
        original_read = Path.read_text
        original_dir = Path.is_dir
        info = dict(ServerVersion='29.1.3', CgroupVersion='2', CgroupDriver='systemd',
                    SecurityOptions=['name=apparmor', 'name=seccomp'])
        used = []

        def read(path, *args, **kwargs):
            supplied = {'/proc/cpuinfo': 'model name: Intel(R) Core(TM) i5-10300H CPU @ 2.50GHz',
                        '/sys/fs/cgroup/cgroup.controllers': 'cpuset cpu io memory pids',
                        '/etc/os-release': 'PRETTY_NAME="Ubuntu 26.04.1 LTS"'}
            return supplied.get(str(path), '') if str(path) in supplied else original_read(path, *args, **kwargs)

        def command(argv):
            used.append(argv)
            if argv[:2] == ['bpftool', 'version']:
                return 'bpftool v7.7.0'
            if argv[:2] == ['docker', 'info']:
                return json.dumps(info)
            if argv[:3] == ['docker', 'context', 'inspect']:
                return '[{"Endpoints":{"docker":{"Host":"unix:///var/run/docker.sock"}}}]'
            if argv[:3] == ['docker', 'image', 'inspect']:
                return json.dumps([dict(Id=identity['image'], Architecture='amd64', Os='linux')])
            raise AssertionError('unexpected command: ' + str(argv))

        with patch.object(cli.os, 'geteuid', return_value=1000), \
             patch.object(cli.os, 'sched_getaffinity', return_value=set(range(8))), \
             patch.object(cli.platform, 'system', return_value='Linux'), \
             patch.object(cli.platform, 'machine', return_value='x86_64'), \
             patch.object(cli.hardware, 'check_topology', return_value={}), \
             patch.object(cli.hardware, 'temperatures', return_value={'coretemp:package': 40}), \
             patch.object(cli.shutil, 'which', return_value='/usr/bin/tool'), \
             patch.object(cli.shutil, 'disk_usage', return_value=Mock(free=25 * 1024**3)), \
             patch.object(cli, 'command', side_effect=command), \
             patch.object(cli.subprocess, 'run', return_value=Mock(stdout='none\n')), \
             patch.object(cli, 'power_settings', return_value=dict(external_power={'AC': '1'}, desktop_profile='balanced')), \
             patch.object(cli.c, 'capacity'), patch.object(Path, 'read_text', read), \
             patch.object(Path, 'is_dir', lambda path: True if str(path) == '/sys/kernel/tracing' else original_dir(path)), \
             patch.dict(os.environ, {'DOCKER_HOST': ''}):
            report = cli.check()
        self.assertFalse(report['collection_started'])
        self.assertFalse(report['runtime_qualified'])
        self.assertTrue(report['service_image_checked'])
        self.assertFalse(any('create' in argv or 'run' in argv or 'start' in argv for argv in used))

    def test_package_payload_mutation_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'diagnostic').mkdir()
            (root / 'scripts').mkdir()
            (root / 'analysis').mkdir()
            (root / 'diagnostic/sample.py').write_text('initial\n')
            c.save(root / 'package.json', dict(source_files=['diagnostic/sample.py']))
            c.save(root / 'package_seal.json', dict(files_sha256={
                'package.json': c.digest(root / 'package.json'),
                'diagnostic/sample.py': c.digest(root / 'diagnostic/sample.py')}))
            with patch.object(c, 'ROOT', root):
                c.verify_package()
                (root / 'diagnostic/sample.py').write_text('changed\n')
                with self.assertRaises(ValueError):
                    c.verify_package()

    def test_runtime_preflight_freezes_fresh_defaults_before_functional_cases(self):
        limits, host = self.limits(), self.host()
        expected = c.resource_baseline(limits, host, c.matrix()[0])
        baseline = dict(boot_id='synthetic-boot', kernel='synthetic-kernel', topology={})
        previous = dict(image='synthetic-image', resource_baseline=None, matrix=c.matrix())
        with tempfile.TemporaryDirectory() as temp:
            session = Path(temp)
            (session / 'bundle').mkdir()
            (session / 'bundle/seal.json').write_text('{}\n')
            for name in ('gate', 'loadgen', 'image.server', 'publication_source.go', 'publication_build.json', 'counter'):
                (session / 'bundle' / name).write_text('synthetic\n')

            class FakeService:
                def __init__(self, session, cfg, directory):
                    self.directory = directory
                    self.expected_limits = limits
                def create(self):
                    c.save(self.directory / 'initial.json', dict(resource_baseline=expected))
                def close(self):
                    return None

            calls = []
            def collect(_session, directory, cfg, mode, functional):
                self.assertEqual(c.read(session / 'preparation/manifest.json')['resource_baseline'], expected)
                self.assertTrue(functional)
                directory.mkdir(parents=True)
                c.save(directory / 'marker.json', dict(software_fixture=True))
                c.seal(directory)
                calls.append(cfg['trial'])
                return directory

            with patch.object(study.verify, 'verify_bundle', return_value=previous), \
                 patch.object(study, 'require_quiet_host'), patch.object(study.run.old, 'check_topology'), \
                 patch.object(study, 'start_watchdog', return_value=(Mock(), Mock())), \
                 patch.object(study.fixtures, 'stop'), patch.object(study.c, 'capacity'), \
                 patch.object(study.c, 'baseline', return_value=baseline), \
                 patch.object(study, 'command', return_value='[{"Id":"synthetic-image"}]'), \
                 patch.object(study, 'Service', FakeService), patch.object(study, 'collect', side_effect=collect), \
                 patch.object(study.verify, 'verify_preparation'):
                study.prepare_runtime(session)
            manifest = c.read(session / 'preparation/manifest.json')
            self.assertTrue(manifest['functional_passed'])
            self.assertEqual(manifest['resource_baseline'], expected)
            self.assertEqual(len(calls), 6)
            self.assertIsNone(previous['resource_baseline'])

    def test_all_six_historical_functional_fixtures_replay_under_declared_adapter(self):
        # These remain labelled historical software fixtures. No workload or
        # current-host measurement is created; adapted JSON lives in temp only.
        base = c.ROOT / 'assets/software_fixtures'
        self.assertFalse(c.read(base / 'role.json')['host02_measurements'])
        with tempfile.TemporaryDirectory() as temp:
            session = Path(temp)
            (session / 'preparation').mkdir()
            c.save(session / 'preparation/manifest.json', dict(software_fixture=True))
            for cfg in c.functional_configs():
                original = base / cfg['trial']
                directory = session / 'preparation/functional' / cfg['trial']
                directory.mkdir(parents=True)
                argv_path = original / 'loadgen_argv.json'
                old_session = c.read(argv_path)[0].split('/preparation/loadgen')[0] if argv_path.exists() else ''
                old_directory = c.read(argv_path)[-1].removesuffix('/loadgen.json') if argv_path.exists() else ''

                def adapt(value):
                    if isinstance(value, str):
                        if value == '2,4':
                            return '2,3'
                        if old_directory and value.startswith(old_directory):
                            return str(directory) + value[len(old_directory):]
                        if old_session and value.startswith(old_session):
                            return str(session) + value[len(old_session):]
                        return value
                    if isinstance(value, list):
                        return [adapt(v) for v in value]
                    if isinstance(value, dict):
                        out = {k: adapt(v) for k, v in value.items()}
                        for key in ('cpus', 'affinity'):
                            if out.get(key) == [2, 4]:
                                out[key] = [2, 3]
                        if out.get('cpu.max') == '50000 100000':
                            out['cpu.max'] = '25000 100000'
                        return out
                    return value

                for path in original.glob('*.json'):
                    c.save(directory / path.name, adapt(c.read(path)))
                self.assertEqual(c.read(directory / 'config.json'), cfg)
                (directory / 'qualification').mkdir()
                shutil.copy2(c.ROOT / 'assets/binaries/gate', directory / 'qualification/gate')
                shutil.copy2(c.ROOT / 'assets/binaries/image.server', directory / 'container.server')
                c.seal(directory)
                with self.subTest(case=cfg['trial']):
                    self.assertEqual(raw.replay(directory, True), c.read(original / 'derived.json'))
                    snapshots = c.read(directory / 'thread_snapshots.json')
                    snapshots[0]['affinity'] = [2, 4]
                    c.save(directory / 'thread_snapshots.json', snapshots)
                    c.seal(directory)
                    with self.assertRaises(ValueError):
                        raw.replay(directory, True)


if __name__ == '__main__':
    unittest.main()
