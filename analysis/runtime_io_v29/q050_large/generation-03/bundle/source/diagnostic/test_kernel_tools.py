import unittest

import kernel_tools as tools


class InstallationGuardTests(unittest.TestCase):
    def row(self, name='perf', version='7.2.8-2', repository='extra'):
        return dict(name=name, version=version, download_bytes=100, repository=repository)

    def test_existing_package_replacement_is_refused(self):
        with self.assertRaises(ValueError):
            tools.validate_transaction([self.row()], {'perf': 'older'})

    def test_kernel_install_and_unexpected_dependencies_are_refused(self):
        for name in ('linux', 'linux-headers', 'glibc', 'unlisted-dependency'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                tools.validate_transaction([self.row(name)], {})

    def test_other_repository_and_duplicates_are_refused(self):
        with self.assertRaises(ValueError):
            tools.validate_transaction([self.row(repository='testing')], {})
        with self.assertRaises(ValueError):
            tools.validate_transaction([self.row(), self.row()], {})

    def test_post_install_requires_exact_delta_and_preserved_packages(self):
        plan = dict(installed_before={'linux': 'same'}, transaction=[self.row()])
        tools.validate_installation(plan, {'linux': 'same', 'perf': '7.2.8-2'})
        for after in ({'linux': 'changed', 'perf': '7.2.8-2'},
                      {'perf': '7.2.8-2'},
                      {'linux': 'same', 'perf': 'unexpected'},
                      {'linux': 'same', 'perf': '7.2.8-2', 'extra': '1'}):
            with self.subTest(after=after), self.assertRaises(ValueError):
                tools.validate_installation(plan, after)

    def test_available_scheduler_events_do_not_qualify_observation(self):
        value = dict(tools={k: {'returncode': 0} for k in ('perf','trace-cmd','bpftrace','bpftool')},
            tracefs=dict(available_events=dict(ok=True, text='\n'.join(tools.SCHED_EVENTS)),
                         quota_function_candidates=['throttle_cfs_rq']))
        result = tools.assessment(value)
        self.assertFalse(result['observation_qualified'])
        self.assertFalse(result['performance_batch_ready'])
        self.assertEqual(result['quota_event_candidates'], [])

    def test_denied_tracefs_and_missing_tool_remain_incomplete(self):
        value = dict(tools={'perf': dict(missing=True)}, tracefs=dict(
            available_events=dict(ok=False, error='denied'), quota_function_candidates=[]))
        self.assertEqual(tools.assessment(value)['status'], 'setup_incomplete')

    def test_trace_cmd_usage_version_is_recognized_without_hiding_errors(self):
        good=dict(returncode=255,stdout='\ntrace-cmd version 3.4.0 (not-a-git-repo)\nusage:\n',stderr='')
        self.assertTrue(tools.version_ok('trace-cmd',good))
        self.assertFalse(tools.version_ok('perf',good))
        self.assertFalse(tools.version_ok('trace-cmd',{**good,'stdout':'unrecognized option'}))
        self.assertFalse(tools.version_ok('trace-cmd',{**good,'stderr':'failed'}))


if __name__ == '__main__': unittest.main()
