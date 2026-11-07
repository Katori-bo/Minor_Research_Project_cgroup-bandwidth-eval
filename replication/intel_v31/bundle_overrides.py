"""Portable bundle preparation and verification, with fresh runtime qualification."""


def prepare_offline(session):
    if session.exists():
        raise ValueError('preserve existing generation; automatic overwrite/resume prohibited')
    c.verify_package()
    c.design()
    client = c.verify_client_build()
    sources = c.source_hashes()
    assets = c.read(c.ROOT / 'assets/retained_identity.json')
    session.mkdir(parents=True)
    out = session / 'bundle'
    out.mkdir()
    for name, expected in sources.items():
        target = out / 'source' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(c.ROOT / name, target)
        if c.digest(target) != expected:
            raise ValueError('source changed during snapshot')
    for name in ('gate', 'loadgen', 'image.server', 'publication_source.go', 'publication_build.json', 'counter'):
        shutil.copy2(c.ROOT / 'assets/binaries' / name, out / name)
    shutil.copytree(c.CLIENT_BUILD, out / 'client_build')
    shutil.copytree(c.DESIGN, out / 'scientific_design')
    tests = subprocess.run([sys.executable, '-B', '-m', 'unittest', 'discover', '-s', 'diagnostic',
                            '-p', 'test_v31_host02*.py', '-v'], cwd=c.ROOT,
                           capture_output=True, text=True, timeout=180)
    (out / 'tests.stdout').write_text(tests.stdout)
    (out / 'tests.stderr').write_text(tests.stderr)
    if tests.returncode:
        raise ValueError('host02 offline tests failed; see bundle/tests.stderr')
    exports = {}
    for cfg in c.matrix() + [c.warmup_config(x) for x in c.matrix() if x['traffic_pattern'] != 'idle'] + c.functional_configs():
        if cfg['traffic_pattern'] == 'idle':
            continue
        key = cfg['trial'] + ('_warmup' if cfg['duration_sec'] == 20 else '_measurement')
        target = out / 'compiled_vectors' / (key + '.json')
        target.parent.mkdir(exist_ok=True)
        argv = [str(out / 'loadgen'), '-duration', str(cfg['duration_sec']) + 's', '-rate', str(cfg['rate']),
                '-pattern', cfg['traffic_pattern'], '-burst-low', str(cfg['burst_low']),
                '-burst-high', str(cfg['burst_high']), '-burst-period', str(cfg['burst_period_sec']) + 's',
                '-burst-low-duration', str(cfg['burst_low_duration_sec']) + 's', '-schedule-output', str(target)]
        result = subprocess.run(argv, capture_output=True, text=True, timeout=10)
        if result.returncode or c.read(target) != c.schedule(cfg):
            raise ValueError('compiled schedule export failed: ' + result.stderr)
        exports[key] = dict(argv=argv, sha256=c.digest(target), count=len(c.schedule(cfg)))
    c.save(out / 'manifest.json', dict(assets, schema=31, host_id='host02', generation=session.name,
        matrix=c.matrix(), sources=sources, design_seal=c.digest(c.DESIGN / 'seal.json'),
        client_build_seal=c.digest(out / 'client_build/seal.json'), compiled_exports=exports,
        software_checks_passed=True, runtime_qualified=False, performance_run=False,
        resource_baseline=None, created=time.time()))
    if c.source_hashes() != sources:
        raise ValueError('sources changed during preparation')
    c.seal(out)
    verify.verify_bundle(session)
    print('HOST02 offline bundle verified: 16 calibration + 18 validation, runtime qualification pending.', flush=True)


def verify_bundle(session, current=True):
    c.verify_package()
    p = session / 'bundle'
    c.verify_seal(p)
    m = c.read(p / 'manifest.json')
    c.design()
    if (m['schema'] != 31 or m['host_id'] != 'host02' or m['matrix'] != c.matrix()
            or not m['software_checks_passed'] or m['runtime_qualified'] or m['performance_run']
            or m['resource_baseline'] is not None):
        raise ValueError('host02 bundle contract differs')
    if m['design_seal'] != c.digest(c.DESIGN / 'seal.json'):
        raise ValueError('host02 design changed')
    identity = c.read(c.ROOT / 'assets/retained_identity.json')
    for key in ('image', 'server_sha256', 'gate_sha256', 'loadgen_sha256', 'counter_sha256'):
        if m[key] != identity[key]:
            raise ValueError('retained executable identity differs')
    c.verify_client_build()
    c.verify_seal(p / 'client_build')
    c.verify_seal(p / 'scientific_design')
    if c.digest(p / 'client_build/seal.json') != m['client_build_seal']:
        raise ValueError('client build receipt changed')
    if c.files(p / 'scientific_design') != c.files(c.DESIGN):
        raise ValueError('design snapshot differs')
    for filename, key in [('gate', 'gate_sha256'), ('loadgen', 'loadgen_sha256'),
                          ('image.server', 'server_sha256'), ('counter', 'counter_sha256')]:
        if c.digest(p / filename) != m[key]:
            raise ValueError('bundled binary changed')
    if m['loadgen_sha256'] != c.design()['loadgen_sha256']:
        raise ValueError('scientific client changed')
    for name, expected in m['sources'].items():
        if c.digest(p / 'source' / name) != expected or c.digest(c.ROOT / name) != expected:
            raise ValueError('adapted source changed: ' + name)
    if c.source_hashes() != m['sources']:
        raise ValueError('adapted source inventory changed')
    expected = {}
    for cfg in c.matrix() + [c.warmup_config(x) for x in c.matrix() if x['traffic_pattern'] != 'idle'] + c.functional_configs():
        if cfg['traffic_pattern'] != 'idle':
            expected[cfg['trial'] + ('_warmup' if cfg['duration_sec'] == 20 else '_measurement')] = cfg
    if set(expected) != set(m['compiled_exports']):
        raise ValueError('compiled export inventory differs')
    for key, cfg in expected.items():
        path = p / 'compiled_vectors' / (key + '.json')
        receipt = m['compiled_exports'][key]
        if (c.digest(path) != receipt['sha256'] or c.read(path) != c.schedule(cfg)
                or receipt['count'] != len(c.schedule(cfg))):
            raise ValueError('compiled schedule differs')
    return m
