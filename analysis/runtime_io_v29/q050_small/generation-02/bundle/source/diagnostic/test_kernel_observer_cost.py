import copy
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

import kernel_observer_common as c
import kernel_observer_analysis as analysis
import kernel_observer_cost as runner
import kernel_observer_coverage as coverage
import kernel_observer_supervisor as supervisor
from test_kernel_bridge import records, raw, META


class ProtocolTests(unittest.TestCase):
    def test_balanced_frozen_matrix(self):
        matrix=c.matrix()
        self.assertEqual(len(matrix),12)
        self.assertEqual([r['arm'] for r in matrix],['off','on','on','off']*3)
        self.assertEqual([r['order'] for r in matrix],list(range(1,13)))
        for p in range(1,7):
            a,z=[r for r in matrix if r['pair']==p]
            self.assertEqual({k:a[k] for k in c.WORKLOAD},{k:z[k] for k in c.WORKLOAD})

    def test_original_limits_not_bridge_fixture_limits(self):
        self.assertEqual(c.WORKLOAD['memory'],0); self.assertEqual(c.WORKLOAD['pids_limit'],0)
        text=Path(supervisor.__file__).read_text()
        self.assertNotIn("'--memory'",text); self.assertNotIn("'--pids-limit'",text)
        argv=c.service_argv('image',Path('/qualification'),'owned')
        self.assertNotIn('--memory',argv); self.assertNotIn('--pids-limit',argv)

    def test_finite_host_pid_default_is_preserved_and_frozen(self):
        limits={'cpu.max':'50000 100000','cpu.max.burst':'0','cpuset.cpus.effective':'2,4','memory.max':'max','pids.max':'18088'}
        host=dict(Memory=0,MemorySwap=0,PidsLimit=None)
        baseline=dict(limits=copy.deepcopy(limits),host_config=copy.deepcopy(host))
        c.validate_resources(limits,host,baseline)
        changed=dict(limits,**{'pids.max':'128'})
        with self.assertRaisesRegex(ValueError,'resource defaults'): c.validate_resources(changed,host,baseline)
        with self.assertRaisesRegex(ValueError,'resource defaults'): c.validate_resources(limits,dict(host,PidsLimit=128),baseline)
        with self.assertRaisesRegex(ValueError,'CPU'): c.validate_resources(dict(limits,**{'cpu.max.burst':'1'}),host,baseline)

    def test_arrivals_and_identity_accounting(self):
        vector=c.arrivals(); self.assertEqual(len(vector),6793)
        self.assertEqual(vector[0],0); self.assertLess(vector[-1],60*10**9)
        client=dict(total_scheduled=len(vector),requests=[dict(ID=i,ScheduledOffsetNs=n) for i,n in enumerate(vector)])
        self.assertEqual(c.arrival_vector(client),vector)
        client['requests'][3]['ScheduledOffsetNs']+=1
        with self.assertRaisesRegex(ValueError,'arrival'): c.arrival_vector(client)
        client['requests'][3]['ID']=2
        with self.assertRaisesRegex(ValueError,'identity'): c.arrival_vector(client)

    def test_ipc_rejects_arbitrary_and_out_of_order_operations(self):
        for request in (dict(op='exec'),dict(op='release'),dict(op='create',pid=1),dict(op='create',path='/tmp'),
                        dict(op='create',arm='on'),dict(op='finish')):
            with self.assertRaises(ValueError): c.Protocol(1).accept(request)
        p=c.Protocol(1)
        for op in ('create','observe','release','observe','end','finish'): self.assertEqual(p.accept(dict(op=op)),op)
        with self.assertRaises(ValueError): p.accept(dict(op='create'))

    def test_socket_subprocess_disconnect_and_timeout(self):
        a,b=socket.socketpair()
        program='import os,socket,sys; import kernel_observer_common as c; s=socket.socket(fileno=int(sys.argv[1])); c.send(s,c.receive(s)); s.close()'
        p=subprocess.Popen([sys.executable,'-c',program,str(b.fileno())],pass_fds=(b.fileno(),),cwd=c.ROOT/'diagnostic')
        b.close()
        try:
            c.send(a,dict(op='observe')); self.assertEqual(c.receive(a),dict(op='observe'))
            p.wait(timeout=5)
            with self.assertRaises(EOFError): c.receive(a)
        finally:
            a.close()
            if p.poll() is None: p.kill(); p.wait(timeout=5)
        a,b=socket.socketpair(); a.settimeout(.05)
        try:
            with self.assertRaises(socket.timeout): c.receive(a)
        finally: a.close(); b.close()

    def test_rejected_ipc_frame(self):
        a,b=socket.socketpair()
        try:
            a.sendall(b'\x00\x01\x00\x01')
            with self.assertRaisesRegex(ValueError,'frame'): c.receive(b)
        finally: a.close(); b.close()

    def test_seal_checks_extra_changed_and_symlink_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp); (d/'raw').write_text('retained'); c.seal(d); c.verify_seal(d)
            (d/'raw').write_text('changed')
            with self.assertRaises(ValueError): c.verify_seal(d)
            c.seal(d); (d/'extra').write_text('added')
            with self.assertRaises(ValueError): c.verify_seal(d)
            (d/'link').symlink_to(d/'raw')
            with self.assertRaises(ValueError): c.seal(d)

    def test_explicit_resume_retains_completed_no_performance_rerun(self):
        with tempfile.TemporaryDirectory() as tmp:
            session=Path(tmp); d=session/'trials/p1_off/attempt-1'; d.mkdir(parents=True)
            c.save(d/'complete.json',dict(valid=True)); c.save(d/'derived.json',dict(p99=99999)); c.seal(d)
            self.assertEqual(len(runner.pending(session,'resume')),11)
            self.assertNotIn('p1_off',[v['trial'] for v in runner.pending(session,'resume')])

    def test_live_status_never_hashes_evidence(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(c,'verify_seal',side_effect=AssertionError('live hashing')):
            runner.status(Path(tmp))


class ParserTests(unittest.TestCase):
    def test_valid_zero_throttle_pilot_capture(self):
        rows=[r for r in records() if r[0] not in ('T','U')]
        result=coverage.coverage(raw(rows),'',META,[])
        self.assertEqual(result['quota_intervals'],[])
        self.assertEqual(result['throttle_attempts'],0)

    def test_bad_loss_map_malformed_lifecycle_quota(self):
        for stderr in ('Lost 1 events','map exhausted error','WARNING: dropped events'):
            with self.assertRaises(ValueError): coverage.coverage(raw(records()),stderr,META,[])
        for rows in (records()[:-1],[r for r in records() if r[0]!='U'],[['S',2]],
                     [r for r in records() if r[0]!='F']):
            with self.assertRaises((ValueError,IndexError)): coverage.coverage(raw(rows),'',META,[])
        with self.assertRaises(ValueError): coverage.coverage(raw(records()).replace('END 1000 19','END 1000 20'),'',META,[])

    def test_attempts_separate_from_success_and_per_cpu_overlap(self):
        rows=records()+[['T',30,31,2,50,900,0,0]]
        result=coverage.coverage(raw(rows),'',META,[])
        self.assertEqual(result['throttle_attempts'],3); self.assertEqual(len(result['quota_intervals']),2)
        self.assertEqual([i['cpu'] for i in result['quota_intervals']],[2,4])

    def test_external_wakeup_origin_preserves_target_scope(self):
        rows=records()+[['W',17,7,101,2]]
        result=coverage.coverage(raw(rows),'',META,[])
        self.assertTrue(result['passed'])
        rows[-1][4]=3
        with self.assertRaises(ValueError): coverage.coverage(raw(rows),'',META,[])

    def test_quota_wrong_cgroup_and_open_pair(self):
        rows=records(); rows[5][4]=999
        with self.assertRaises(ValueError): coverage.coverage(raw(rows),'',META,[])

    def test_clock_generation_and_uncertainty(self):
        samples=[dict(label=f'{phase}_{i}',before_ns=10000+i,after_ns=10010+i,
                      server_ns=1000+i,generation=7) for phase in ('start','stop') for i in range(3)]
        mapping=dict(server_minus_client_lower_ns=100,server_minus_client_upper_ns=110)
        joined=coverage.clock_join(samples,mapping,7)
        self.assertEqual(joined['uncertainty_ns'],20)
        for mutation in ('generation','bound','composition','labels'):
            s=copy.deepcopy(samples); m=copy.deepcopy(mapping)
            if mutation=='generation': s[0]['generation']=8
            elif mutation=='bound':
                for v in s: v['after_ns']+=2_000_000
            elif mutation=='composition': m['server_minus_client_upper_ns']=3_000_000
            else: s[-1]['label']=s[0]['label']
            with self.assertRaises(ValueError): coverage.clock_join(s,m,7)


class ScreenTests(unittest.TestCase):
    def rows(self):
        return [dict(pair=p,arm=a,timely_500_fraction=.9,timely_1000_fraction=.95,failure_fraction=.005,
                     cpu_usec_per_completed_work=2000,p99_e2e_ms=1100) for p in range(1,7) for a in ('off','on')]

    def test_screen_all_pairs_and_sample_sd(self):
        r=analysis.compare(self.rows())
        self.assertEqual(r['decision'],'within_margins_requires_review')
        self.assertEqual(len(r['pairs']),6); self.assertEqual(r['paired_statistics']['cpu_ratio']['sample_sd'],0)
        self.assertFalse(r['observer_cost_qualified'])

    def test_one_failed_pair_cannot_hide_in_median(self):
        rows=self.rows(); rows[1]['p99_e2e_ms']=1300
        r=analysis.compare(rows); self.assertEqual(r['decision'],'effects_outside_margins')
        self.assertEqual(r['paired_statistics']['p99_ratio']['median'],1)
        self.assertGreater(r['paired_statistics']['p99_ratio']['sample_sd'],0)

    def test_incomplete_nonfinite_and_zero_metrics(self):
        self.assertEqual(analysis.compare(self.rows()[:-1])['decision'],'incomplete_evidence')
        for value in (None,0,float('nan'),float('inf')):
            rows=self.rows(); rows[0]['cpu_usec_per_completed_work']=value
            self.assertEqual(analysis.compare(rows)['decision'],'incomplete_evidence')

    def test_exact_margins_and_metric_formulas(self):
        rows=self.rows()
        for r in rows:
            if r['arm']=='on': r.update(timely_500_fraction=.91,timely_1000_fraction=.96,failure_fraction=.006,
                                       cpu_usec_per_completed_work=2100,p99_e2e_ms=1210)
        self.assertTrue(all(p['within_screen'] for p in analysis.compare(rows)['pairs']))
        config=c.matrix()[0]; requests=[dict(success=True,timely_500=True,timely_1000=True,e2e_ns=1_000_000,
                                              worker_observed=True,handler_observed=True),
                                         dict(success=False,timely_500=False,timely_1000=False,e2e_ns=5_000_000_000,
                                              worker_observed=True,handler_observed=False)]
        observations=dict(measurement_start=dict(before_ns=1,after_ns=2,cpu_stat=dict(usage_usec=100)),
                          measurement_stop=dict(before_ns=3,after_ns=4,cpu_stat=dict(usage_usec=700)))
        s=analysis.summary(config,{},dict(completed=2),requests,observations)
        self.assertEqual(s['failure_fraction'],.5); self.assertEqual(s['cpu_usec_per_completed_work'],300)
        self.assertEqual(s['p99_e2e_ms'],1)


class SupervisorResourceTests(unittest.TestCase):
    def service(self,directory):
        with patch.object(fixtures_root(),'root_state',return_value=dict(tracing_on='0')):
            return supervisor.OwnedService(Path(directory),c.matrix()[0],Path(directory),os.getuid(),os.getgid())

    def test_active_watchdog_and_worker_death(self):
        with tempfile.TemporaryDirectory() as tmp:
            service=self.service(tmp); service.started=time.monotonic()-361
            with self.assertRaisesRegex(TimeoutError,'watchdog'): service.guard(check_worker=False)
            service.started=time.monotonic()
            process=subprocess.Popen([sys.executable,'-c','pass']); process.wait(timeout=5); service.pid=process.pid
            with self.assertRaisesRegex(ValueError,'died'): service.guard()

    def test_bounded_pipe_retains_overflow_and_invalidates(self):
        with tempfile.TemporaryDirectory() as tmp:
            service=self.service(tmp)
            process=subprocess.Popen([sys.executable,'-c','import sys; sys.stdout.buffer.write(b"x"*200)'],stdout=subprocess.PIPE)
            service.logs['events.txt']=(Path(tmp)/'events.txt').open('wb')
            service.pipes={process.stdout.fileno():'events.txt'}; process.wait(timeout=5)
            try:
                with patch.object(c,'RAW_LIMIT',64):
                    with self.assertRaisesRegex(ValueError,'ceiling'): service.pump()
                self.assertEqual((Path(tmp)/'overflow.bin').read_bytes(),b'x'*200)
                self.assertTrue((Path(tmp)/'raw_limit_violation.json').exists())
            finally: service.logs['events.txt'].close(); process.stdout.close()

    def test_cleanup_only_owned_process_and_controls_verified(self):
        with tempfile.TemporaryDirectory() as tmp:
            service=self.service(tmp); group=Path(tmp)/'owned-group'; group.mkdir(); service.group=group
            service.container='owned-container'
            owned=subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)'])
            unrelated=subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)'])
            calls=[]
            def fixed_command(argv,timeout=20):
                calls.append(argv)
                self.assertIn('owned-container',argv)
                if argv[1]=='stop': owned.terminate(); owned.wait(timeout=5)
                if argv[1]=='rm': group.rmdir()
                return ''
            try:
                with patch.object(supervisor,'command',side_effect=fixed_command), \
                     patch.object(supervisor.fixtures,'root_state',return_value=dict(tracing_on='0')), \
                     patch.object(supervisor.fixtures,'wait_detached'), \
                     patch.object(supervisor.subprocess,'run',return_value=subprocess.CompletedProcess([],0,b'',b'')):
                    result=service.close('controlled disconnect')
                self.assertTrue(result['detached'] and result['container_removed'] and result['cgroup_removed'])
                self.assertIsNone(unrelated.poll()); self.assertEqual(len(calls),2)
            finally:
                for p in (owned,unrelated):
                    if p.poll() is None: p.terminate(); p.wait(timeout=5)

    def test_cleanup_root_control_change_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            service=self.service(tmp); service.group=Path(tmp)/'absent'
            with patch.object(supervisor.fixtures,'root_state',return_value=dict(tracing_on='1')), \
                 patch.object(supervisor.fixtures,'wait_detached'):
                with self.assertRaisesRegex(ValueError,'controls changed'): service.close()
            self.assertFalse(c.read(Path(tmp)/'cleanup.json')['root_controls_unchanged'])
            with self.assertRaisesRegex(ValueError,'remains unverified'): service.close()


def fixtures_root(): return supervisor.fixtures


if __name__=='__main__': unittest.main()
