def require_quiet_host():
    run.require_quiet_host()
    c.require_desktop_absent()

def bounded_settle(path, baseline=None, initial_idle=False, expected_power=None):
    start = time.monotonic()
    samples = []
    minimum = 600 if initial_idle else 60
    while True:
        require_quiet_host()
        elapsed = time.monotonic() - start
        settings = power_settings()
        if expected_power is not None and settings != comparable_power(expected_power):
            raise ValueError('power settings changed during settling')
        samples.append(dict(elapsed_sec=elapsed, timestamp=time.time(), temperatures=run.old.temperatures(), power_settings=settings))
        c.save(path, dict(policy=POLICY, samples=samples, accepted=False))
        i = 0
        while i + 1 < len(samples) and samples[i + 1]['elapsed_sec'] <= elapsed - 60:
            i += 1
        summary = window_summary(samples[i:], baseline)
        if elapsed >= minimum and summary and summary['stable']:
            c.save(path, dict(policy=POLICY, samples=samples, accepted=True, summary=summary))
            return summary
        if elapsed >= 1200:
            raise TimeoutError('frozen settling timeout1200s')
        if len(samples) % 12 == 1:
            print(f'Settling {path.parent.name}: {elapsed:.0f}s', flush=True)
        time.sleep(5)

def update(session, config, stage):
    if config.get('functional'):
        return
    c.save(session / 'progress.json', dict(trial=config['trial'], role=config['role'], order=config['order'], stage=stage, timestamp=time.time(), log=str(session)))
    print(f"{config['order']}/{len(c.matrix())} {config['trial']}: {stage}", flush=True)

def load(directory, service, seconds, name, session, config):
    config = c.warmup_config(config) if name == 'warmup' else config
    if config['traffic_pattern'] == 'idle':
        return capture_idle(directory, service, seconds, 'warmup_idle' if name == 'warmup' else 'idle', session, config)
    argv = [str(session / 'preparation/loadgen'), '-url', service.base + '/work?iterations=' + str(config['iterations']), '-duration', str(seconds) + 's', '-rate', str(config['rate']), '-pattern', config['traffic_pattern'], '-burst-low', str(config['burst_low']), '-burst-high', str(config['burst_high']), '-burst-period', str(config['burst_period_sec']) + 's', '-burst-low-duration', str(config['burst_low_duration_sec']) + 's', '-concurrency', '512', '-timeout', str(config['timeout_sec']) + 's', '-trace-client=true', '-output', str(directory / (name + '.json'))]
    c.save(directory / (name + '_argv.json'), argv)
    with (directory / (name + '.log')).open('x') as log:
        process = decision.spawn(directory, config, name, subprocess.Popen, argv, stdout=log, stderr=subprocess.STDOUT, preexec_fn=lambda: os.sched_setaffinity(0, {0, 1}))
        c.save(directory / (name + '_process.json'), c.process_identity(process.pid))
        try:
            until = time.monotonic() + seconds + 30
            next_report = 0
            while process.poll() is None:
                if not config.get('functional'):
                    require_quiet_host()
                service.observe()
                if time.monotonic() >= next_report:
                    update(session, config, name)
                    next_report = time.monotonic() + 10
                if time.monotonic() > until:
                    raise TimeoutError('bounded retained-client timeout')
                time.sleep(1)
            if process.returncode:
                raise ValueError('retained loadgen failed')
        finally:
            fixtures.stop(process, signal.SIGTERM)

def drain(service, seconds=100):
    until = time.monotonic() + seconds
    while True:
        service.observe()
        server = bridge.get(service.base, 'metrics')
        if not server['active_handlers'] and (not server['queue_len']) and (server['completed'] == server['admitted']):
            return server
        if time.monotonic() > until:
            raise TimeoutError('full service drain timeout')
        time.sleep(1)

def reset(service):
    with urllib.request.urlopen(urllib.request.Request(service.base + '/reset', data=b'', method='POST'), timeout=3) as response:
        if response.status != 204:
            raise ValueError('metrics reset failed')
    return dict(monotonic_ns=time.monotonic_ns(), health=bridge.get(service.base, 'health'))

def collect(session, directory, config, mode, functional=False):
    decision.before_trial(directory, config)
    directory.mkdir(parents=True, exist_ok=False)
    c.save(directory / 'config.json', config)
    c.save(directory / 'started.json', dict(monotonic_ns=time.monotonic_ns(), wall_time=time.time()))
    service = Service(session, config, directory)
    monitor = None
    counter = None
    counter_log = None
    failure = None
    try:
        if not functional:
            environment = c.read(session / 'environment.json')
            c.save(directory / 'environment.json', environment)
            require_quiet_host()
            update(session, config, 'settling')
            bounded_settle(directory / 'settling.json', environment['baseline_c'], expected_power=environment['power_settings'])
            c.capacity(session)
            if power_settings(include_profile=True) != environment['power_settings']:
                raise ValueError('power baseline changed')
        service.create()
        if not functional:
            monitor = HostMonitor(directory, lambda: (service.guard(), require_quiet_host()))
            monitor.start(service.group)
        service.release()
        if config['counter_probe']:
            counter_log = (directory / 'counter.log').open('x')
            argv = [str(session / 'preparation/counter'), '--path', str(service.group / 'cpu.stat'), '--output', str(directory / 'counter.raw.json')]
            c.save(directory / 'counter_argv.json', argv)
            counter = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=counter_log, preexec_fn=lambda: os.sched_setaffinity(0, {0, 1}))
            c.save(directory / 'counter_process.json', c.process_identity(counter.pid))
            service.counter_process = counter
            until = time.monotonic() + 2
            while True:
                service.guard()
                if time.monotonic() >= until:
                    raise TimeoutError('native counter readiness deadline')
                if select.select([counter.stdout], [], [], 0.005)[0]:
                    token = os.read(counter.stdout.fileno(), 6)
                    if token != b'READY\n':
                        raise ValueError('native readiness handshake failed')
                    c.save(directory / 'counter_readiness.json', dict(token='READY', received_monotonic_ns=time.monotonic_ns()))
                    break
        observations = dict(startup=service.observe())
        if not functional:
            load(directory, service, 20, 'warmup', session, config)
            c.save(directory / 'warmup_server_metrics.json', drain(service))
            if config['traffic_pattern'] != 'idle':
                c.validate_client(c.read(directory / 'warmup.json'), c.warmup_config(config))
        decision.warmup_ready(directory, config)
        update(session, config, 'reset')
        c.save(directory / 'reset.json', reset(service))
        anchors = bridge.anchors(service.base, 'start')
        observations['measurement_start'] = service.observe()
        load(directory, service, config['duration_sec'], 'loadgen', session, config)
        update(session, config, 'drain')
        server = drain(service)
        observations['measurement_stop'] = service.observe()
        anchors += bridge.anchors(service.base, 'stop')
        observations['final'] = service.observe()
        c.save(directory / 'host_server_anchors.json', anchors)
        c.save(directory / 'server_metrics.json', server)
        c.save(directory / 'observations.json', observations)
        if not functional and power_settings(include_profile=True) != environment['power_settings']:
            raise ValueError('power changed during trial')
        if counter:
            service.counter_process = None
            fixtures.stop(counter, signal.SIGINT)
            if counter.returncode:
                raise ValueError('counter sampler failed')
            counter.stdout.close()
            native.decode_file(directory / 'counter.raw.json', directory / 'counter.json', c.save)
            c.save(directory / 'counter.ready.json', c.read(directory / 'counter.json')['samples'][0])
            counter_log.close()
            counter = None
        if monitor:
            monitor.finish(observations['final']['after_ns'])
            monitor = None
        service.close()
        c.seal(directory)
        derived = analysis.replay(directory, functional)
        c.save(directory / 'derived.json', derived)
        if config['counter_probe']:
            verify.counter_input(session, directory, config)
        if not functional:
            phase = model.trial(derived, server, anchors, c.read(directory / 'counter.json') if config['counter_probe'] else None, config, c.design(), str(service.group / 'cpu.stat'))
            c.save(directory / 'phase_accounting.json', phase)
        if not functional and config['traffic_pattern'] != 'idle':
            for name in ('warmup', 'loadgen'):
                c.technical_client(c.read(directory / (name + '.json')))
        c.save(directory / 'complete.json', dict(valid=True, performance_run=not functional, functional=functional, finished=time.time(), finished_monotonic_ns=time.monotonic_ns()))
        c.seal(directory)
        return directory
    except BaseException as e:
        failure = str(e)
        c.save(directory / 'interruption.json', dict(error=failure, time=time.time(), traceback=traceback.format_exc()))
        raise
    finally:
        if counter:
            service.counter_process = None
            fixtures.stop(counter, signal.SIGINT)
            counter.stdout.close()
            counter_log.close()
        monitor_cleanup_error = None
        if monitor:
            try:
                monitor.stop()
            except Exception as e:
                monitor_cleanup_error = e
                c.save(directory / 'monitor_cleanup_failure.json', dict(error=str(e)))
        try:
            service.close(failure)
        except Exception as e:
            c.save(directory / 'cleanup_failure.json', dict(error=str(e)))
            if failure is None:
                raise
        finally:
            if failure:
                c.seal(directory)
        if monitor_cleanup_error is not None:
            raise monitor_cleanup_error
