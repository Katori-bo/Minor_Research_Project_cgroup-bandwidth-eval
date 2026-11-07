"""Isolated retained collector adapters. Importing this module never starts traffic.

The caller supplies a qualified retained apparatus namespace. This integration
does not replace runtime preparation, host guards or the external supervisor.
Only the named collection functions are compiled: historical campaign/retry
entry points are deliberately absent. No retained module globals are mutated.
"""
import ast
import hashlib
import json
import os
from pathlib import Path
import time

import evaluation as e


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_bytes())


def save(path, value):
    with Path(path).open('x') as out:
        json.dump(value, out, sort_keys=True, indent=2, allow_nan=False)
        out.write('\n')
        out.flush()
        os.fsync(out.fileno())
    descriptor = os.open(Path(path).parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


class DurableBarrier(e.DecisionBarrier):
    """Add directory-entry durability to the unchanged scientific evaluator."""
    def write(self, filename, value):
        save(self.directory / filename, value)


class OfferReader:
    """Validate exact inherited schedules before extracting ordinary durations."""
    def __init__(self, application, namespace):
        e.require(application in ('Go', 'NGINX'), 'unknown application')
        self.application, self.ns = application, namespace

    def values(self, raw, cfg, warmup=False):
        if self.application == 'Go':
            c = self.ns['c']
            actual = c.warmup_config(cfg) if warmup else cfg
            offsets = c.validate_client(raw, actual)
            c.technical_client(raw)
            rows = {row['ID']: row for row in raw['requests']}
            result = [rows[i]['EndToEndLatencyNs'] if i in rows and
                      not rows[i]['Error'] and rows[i]['StatusCode'] == 200 else None
                      for i in range(len(offsets))]
        else:
            rows = self.ns['model'].outcomes(raw, cfg, 'warmup' if warmup else 'measurement')
            # Wrong content/framing is corruption, not ordinary failure. Match
            # the retained integrity exit, including decoded hash/echo errors.
            e.require(not any(not row['success'] and
                (source['DecodeError'] or (source['Status'] > 0 and not source['Error']))
                for row, source in zip(rows, raw['Rows'])), 'response integrity failed')
            if warmup:
                e.require(all(row['success'] for row in rows), 'warmup outcome unavailable')
            result = [row['e2e_ns'] if row['success'] else None for row in rows]
        e.validate_values(result)
        return result


class CampaignBudget:
    """Admission/child checks in addition to the retained external watchdog."""
    def __init__(self, application, started_ns, clock=time.monotonic_ns):
        self.cap_ns = {'Go': 12600, 'NGINX': 2700}[application] * 10**9
        self.started_ns, self.clock = started_ns, clock

    def check(self, reserve_sec=120):
        e.require(self.clock() + reserve_sec * 10**9 <= self.started_ns + self.cap_ns,
                  'campaign budget exhausted; preserve attempt, no replacement')


class ForecastHook:
    """A single-use window hook; it sees only the warmup before spawning target."""
    def __init__(self, barrier, reader, configs, budget, boot, stop_child,
                 clock=time.monotonic_ns):
        self.barrier, self.reader = barrier, reader
        self.configs = {self.key(cfg): cfg for cfg in configs}
        e.require(len(self.configs) == len(configs) == 18, 'exact 18 target slots required')
        self.budget, self.boot, self.stop_child, self.clock = budget, boot, stop_child, clock
        self.used, self.pending = set(), {}

    def key(self, cfg):
        if self.reader.application == 'Go':
            return cfg['trial']
        return 'b%d_%s' % (cfg['block'], cfg['profile'])

    def is_target(self, cfg):
        return cfg['role'] == 'validation' and not cfg.get('functional', False)

    def before_trial(self, directory, cfg):
        if not self.is_target(cfg):
            return
        key = self.key(cfg)
        e.require(hasattr(self.barrier, 'reference'), 'freeze calibration before target warmup')
        e.require(sha(self.barrier.directory / 'calibration.json') == self.barrier.calibration_hash,
                  'frozen calibration changed before target warmup')
        e.require(key in self.configs and cfg == self.configs[key], 'foreign target configuration')
        e.require(key not in self.used, 'target slot already consumed; no retry or resume')
        self.used.add(key)  # A failed startup/warmup consumes the slot too.
        self.budget.check(480 if self.reader.application == 'Go' else 250)
        self.pending[key] = dict(directory=Path(directory))

    def warmup_ready(self, directory, cfg):
        if not self.is_target(cfg):
            return
        key = self.key(cfg)
        pending = self.pending[key]
        e.require(pending['directory'] == Path(directory), 'foreign trial directory')
        path = Path(directory) / 'warmup.json'
        data = path.read_bytes()
        values = self.reader.values(json.loads(data), cfg, warmup=True)
        # Called only after the retained full service drain succeeds.
        available = self.clock()
        pending.update(values=values, warmup_sha256=hashlib.sha256(data).hexdigest(),
                       available_ns=available)

    def spawn(self, directory, cfg, phase, popen, *args, **kwargs):
        self.budget.check()
        if not self.is_target(cfg) or phase not in ('loadgen', 'measurement'):
            return popen(*args, **kwargs)
        key, boot = self.key(cfg), self.boot()
        pending = self.pending[key]
        e.require('values' in pending and 'spawned' not in pending, 'validated warmup required once')
        e.require(boot == self.barrier.boot_id, 'boot changed before target creation')
        e.require(sha(Path(directory) / 'warmup.json') == pending['warmup_sha256'], 'warmup changed')
        receipt = self.barrier.freeze_warmup(key, pending['values'], pending['available_ns'])
        save(self.barrier.directory / (key + '_inputs.json'), dict(
            warmup_file_sha256=pending['warmup_sha256'], config_sha256=e.digest(cfg),
            application=self.reader.application))
        self.barrier.prepare_target_start(key, receipt)
        self.budget.check()
        # Recheck time immediately before entering Popen, after durable writes.
        permit_ns = read(self.barrier.directory / (key + '_permit.json'))['permit_monotonic_ns']
        pending['spawned'] = True
        before = self.clock()
        e.require(before - pending['available_ns'] <= 10**9, 'barrier expired before Popen')
        e.require(before > permit_ns,
                  'target creation must follow permit')
        child = popen(*args, **kwargs)
        try:
            save(self.barrier.directory / (key + '_child.json'), dict(
                pid=child.pid, forecast_sha256=receipt, boot_id=boot,
                target_spawn_before_ns=before))
            self.barrier.record_target_release(key, receipt, before, self.boot())
        except BaseException:
            # If Popen succeeded but provenance failed, the retained load loop
            # has not received the process. Clean this owned child here.
            self.stop_child(child)
            raise
        return child


def adapt_source(source, application):
    """Exact, auditable edits; source drift is an error rather than a loose patch."""
    def once(old, new):
        nonlocal source
        e.require(source.count(old) == 1, 'ambiguous retained collector adaptation: ' + old)
        source = source.replace(old, new)
    if application == 'Go':
        once('    directory.mkdir(parents=True, exist_ok=False)\n',
             '    decision.before_trial(directory, config)\n    directory.mkdir(parents=True, exist_ok=False)\n')
        once("        if config['traffic_pattern']!='idle':c.validate_client(c.read(directory/'warmup.json'), c.warmup_config(config))\n",
             "        if config['traffic_pattern']!='idle':c.validate_client(c.read(directory/'warmup.json'), c.warmup_config(config))\n        decision.warmup_ready(directory, config)\n")
        once('        process = subprocess.Popen(argv, stdout=log, stderr=subprocess.STDOUT,',
             '        process = decision.spawn(directory, config, name, subprocess.Popen, argv, stdout=log, stderr=subprocess.STDOUT,')
        keep = {'require_quiet_host', 'bounded_settle', 'update', 'load', 'drain', 'reset', 'collect'}
    else:
        once('    case.mkdir()\n', '    decision.before_trial(case, cfg)\n    case.mkdir()\n')
        once("        c.require(q.drained(before_status), 'Study warmup did not drain')\n",
             "        c.require(q.drained(before_status), 'Study warmup did not drain')\n        decision.warmup_ready(case, cfg)\n")
        once('            self.client = subprocess.Popen(argv, stdout=output, stderr=error, start_new_session=True)',
             '            self.client = decision.spawn(self.directory, self.cfg, prefix, subprocess.Popen, argv, stdout=output, stderr=error, start_new_session=True)')
        keep = {'Service', 'analyze', 'identity', 'trial', 'replay_case'}
    tree = ast.parse(source)
    tree.body = [node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name in keep]
    e.require({node.name for node in tree.body} == keep, 'retained collector functions missing')
    return ast.unparse(tree) + '\n'


def bind(adapted_source, retained_namespace, hook):
    """Clone the collection globals; never monkey-patch historical modules."""
    loaded = {node.id for node in ast.walk(ast.parse(adapted_source))
              if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)}
    namespace = {name: value for name, value in retained_namespace.items() if name in loaded}
    namespace['decision'] = hook
    namespace['__name__'] = 'isolated_slo_collector'
    exec(compile(adapted_source, '<isolated-slo-collector>', 'exec'), namespace)
    return namespace


def replay_window(barrier_directory, reader, cfg, directory, plan_hash, campaign_id, boot_id):
    """Replay receipts and raw offers before scoring a complete window.

    Retained raw/server/resource replay remains a separate required input to
    classify primary-domain vs applicability-exit or corrupt/partial windows.
    """
    base, directory = Path(barrier_directory), Path(directory)
    key = cfg['trial'] if reader.application == 'Go' else 'b%d_%s' % (cfg['block'], cfg['profile'])
    cal, f, permit, release, child, inputs = [read(base / name) for name in
        ('calibration.json', key+'_forecast.json', key+'_permit.json', key+'_release.json',
         key+'_child.json', key+'_inputs.json')]
    h = sha(base / (key + '_forecast.json'))
    e.require(all(record['forecast_sha256'] == h for record in (permit, release, child)), 'forecast byte identity differs')
    e.require(all(record['boot_id'] == boot_id for record in (cal, f, permit, release, child)), 'boot identity differs')
    e.require(all(record['plan_hash'] == plan_hash and record['campaign_id'] == campaign_id for record in (cal, f)), 'campaign/plan identity differs')
    e.require(f['window_id'] == permit['window_id'] == release['window_id'] == key, 'window identity differs')
    e.require(inputs['config_sha256'] == e.digest(cfg) and inputs['application'] == reader.application, 'raw configuration differs')
    e.require(inputs['warmup_file_sha256'] == sha(directory / 'warmup.json'), 'raw warmup changed')
    warm = reader.values(read(directory / 'warmup.json'), cfg, warmup=True)
    e.require(e.digest(warm) == f['warmup_sha256'] and e.digest(cal['reference']) == cal['input_sha256'], 'raw input digest differs')
    cells = e.calibration_predictions(cal['reference'], [cell['deadline_ns'] for cell in cal['cells'] if cell['label'].startswith('fixed/')])
    e.require(cells == cal['cells'] and e.warmup_predictions(cal['reference'], warm, cells) == f['cells'], 'forecast arithmetic replay differs')
    before = release['target_spawn_before_ns']
    e.require(child['target_spawn_before_ns'] == before and
        f['warmup_available_ns'] <= f['sealed_monotonic_ns'] <= permit['permit_monotonic_ns'] < before and
        before - f['warmup_available_ns'] <= 10**9, 'prospective clock order differs')
    target_name = 'loadgen.json' if reader.application == 'Go' else 'measurement.json'
    target = reader.values(read(directory / target_name), cfg)
    return [dict(label=cell['label'], deadline_ns=cell['deadline_ns'], methods={
        method: dict(forecast=value, score=e.score(value, target, cell['deadline_ns']))
        for method, value in cell['methods'].items()})
        for cell in f['cells']]
