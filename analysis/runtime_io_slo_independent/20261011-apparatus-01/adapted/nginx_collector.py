class Service(q.Service):
    """Reuse frozen stock startup, procfs guards, watchdog and owned cleanup."""

    def __init__(self, directory, performance, cfg):
        super().__init__(directory, performance)
        self.cfg = cfg

    def collect(self, prefix, count):
        interval = self.cfg['interval_ns']
        argv = [str(c.n.SOFTWARE / 'client'), '--url', self.base + '/compress', '--prefix', prefix, '--count', str(count), '--interval-ns', str(interval)]
        with (self.directory / (prefix + '.json')).open('x') as output, (self.directory / (prefix + '.stderr')).open('x') as error:
            self.client = decision.spawn(self.directory, self.cfg, prefix, subprocess.Popen, argv, stdout=output, stderr=error, start_new_session=True)
            c.save(self.directory / 'client-ownership.json', h.process_identity(self.client.pid))
            until = time.monotonic() + count * interval / 1000000000.0 + 12
            try:
                while self.client.poll() is None:
                    self.guard()
                    if time.monotonic() > until:
                        raise TimeoutError('Study client drain deadline')
                    time.sleep(0.25)
                c.require(self.client.returncode == 0, 'Study client failed')
            finally:
                if self.client.poll() is None:
                    h.bridge.stop_known(self.client)

def analyze(case):
    cfg = c.read(case / 'study-config.json')
    c.require(cfg == c.config(cfg['role'], cfg['index'], cfg['profile'], cfg['block']), 'Foreign study cohort configuration')
    warm = model.outcomes(c.read(case / 'warmup.json'), cfg, 'warmup')
    c.require(all((r['success'] for r in warm)), 'Warmup outcome unavailable')
    outcomes = model.outcomes(c.read(case / 'measurement.json'), cfg)
    counts = c.read(case / 'measurement-counters.json')
    delta = {k: counts['after'][k] - counts['before'][k] for k in counts['before']}
    c.require(delta == counts['delta'] and all((v >= 0 for v in delta.values())), 'Study counter replay failed')
    c.require(c.read(case / 'measurement-before.json') == counts['before'], 'Study before counters differ')
    window = c.read(case / 'status-window.json')
    before, afters = (window['before'], window['after_checks'])
    c.require(q.drained(before) and afters and q.drained(afters[-1]), 'Study requests did not drain')
    c.require(all((a['requests'] <= b['requests'] for a, b in zip([before, *afters], afters))), 'Study status counters reversed')
    requests = afters[-1]['requests'] - before['requests'] - len(afters)
    lower = sum((r['response_headers_observed'] for r in outcomes))
    upper = sum((not r['dropped'] for r in outcomes))
    c.require(lower <= requests <= upper, 'Study request conservation failed')
    lag = sorted((r['dispatch_lag_ns'] for r in outcomes if not r['dropped']))
    p99 = lag[math.ceil(0.99 * len(lag)) - 1] if lag else None
    maximum = max(lag) if lag else None
    exits = []
    if delta['nr_throttled'] or delta['throttled_usec']:
        exits.append('measurement_throttling')
    if any((r['dropped'] for r in outcomes)):
        exits.append('client_inflight_cap')
    if not lag or p99 > 2000000 or maximum > 10000000:
        exits.append('dispatch_gate')
    if cfg['role'] != 'validation' and (not all((r['success'] for r in outcomes))):
        exits.append('unsuccessful_calibration_or_qualification_offer')
    raw = c.read(case / 'measurement.json')['Rows']
    if any((not r['success'] and (row['DecodeError'] or (row['Status'] > 0 and (not row['Error']))) for r, row in zip(outcomes, raw))):
        exits.append('response_integrity')
    return dict(config=cfg, offers=len(outcomes), successful=sum((r['success'] for r in outcomes)), unsuccessful=sum((not r['success'] for r in outcomes)), outcomes=outcomes, measurement_counter_delta=delta, domain_exits=exits, dispatch_p99_ns=p99, dispatch_max_ns=maximum, stock_request_accounting=dict(observed=requests, lower=lower, upper=upper, exact=lower == upper == requests), queue_observed=False, scientific_collection=cfg['role'] in ('calibration', 'validation'))

def identity(case):
    q.identity(case)
    c.require(c.read(case / 'study-sources-at-start.json') == c.sources(), 'Study source identity changed')

def trial(case, cfg, performance, forecast_ref=None):
    decision.before_trial(case, cfg)
    case.mkdir()
    c.save(case / 'study-config.json', cfg)
    c.save(case / 'sources-at-start.json', c.n.source_hashes())
    c.save(case / 'study-sources-at-start.json', c.sources())
    c.save(case / 'trial-start.json', dict(monotonic=time.monotonic(), forecast_ref=forecast_ref))
    service = Service(case, performance, cfg)
    try:
        service.start()
        service.collect('warmup', cfg['warmup_count'])
        before_status = service.status()
        c.require(q.drained(before_status), 'Study warmup did not drain')
        decision.warmup_ready(case, cfg)
        c.save(case / 'threads-before.json', service.guard())
        before = h.fixtures.stat(service.group)
        c.save(case / 'measurement-before.json', before)
        afters = []
        try:
            service.collect('measurement', cfg['count'])
            until = time.monotonic() + 3
            while True:
                afters.append(service.status())
                c.save(case / 'status-window.json', dict(before=before_status, after_checks=afters))
                if q.drained(afters[-1]):
                    break
                if time.monotonic() > until:
                    raise TimeoutError('Study measured requests did not drain')
                time.sleep(0.05)
        finally:
            after = h.fixtures.stat(service.group)
            c.save(case / 'measurement-counters.json', dict(before=before, after=after, delta={k: after[k] - before[k] for k in before}))
        c.save(case / 'threads-after.json', service.guard())
        result = analyze(case)
        c.save(case / 'result.json', result)
    except BaseException as exc:
        c.save(case / 'failure.json', dict(error=str(exc), traceback=traceback.format_exc()))
        raise
    finally:
        try:
            service.close()
        finally:
            q.evidence_seal(case)
    identity(case)
    return result

def replay_case(case, cfg, forecast_ref=None):
    c.verify_evidence(case)
    identity(case)
    c.require(c.read(case / 'study-config.json') == cfg, 'Study case selection differs')
    start = c.read(case / 'trial-start.json')
    c.require(start['forecast_ref'] == forecast_ref, 'Forecast barrier reference differs')
    if forecast_ref is not None:
        c.require(start['monotonic'] >= forecast_ref['sealed_monotonic'], 'Validation preceded frozen forecast')
    value = analyze(case)
    c.require(value == c.read(case / 'result.json'), 'Study raw replay differs')
    return value
