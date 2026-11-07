"""Bounded worker-counter qualification; no predictor or host-setting writes."""
import random
import contextlib
import io
from pathlib import Path
import nginx_rate_transfer_common as prior

ROOT = prior.ROOT
BASE = ROOT / 'analysis/runtime_io_nginx_worker_wait_qualification/generation-01'
FILES = ('diagnostic/nginx_worker_wait_common.py', 'diagnostic/nginx_worker_wait_model.py',
         'diagnostic/nginx_worker_wait_study.py', 'diagnostic/test_nginx_worker_wait.py',
         'diagnostic/start_nginx_worker_wait_qualification.sh',
         'docs/runtime_io_worker_wait_qualification_protocol_20261010.md')
PROTOCOL = dict(schema='nginx-worker-wait-qualification-v1', rates=[4, 8], policy='P0',
    quota_us=25000, period_us=100000, deadline_ns=20565395, warmup_count=25,
    boundary_count=20, measurement_count=300, blocks=6, arms=['off', 'on'],
    boundary_seconds=600, overhead_seconds=2700, cleanup_reserve_sec=120,
    cohort_reserve_sec=150, service_active_sec=120, settling_sec=10,
    quiet_sec=.1, max_read_bracket_ns=2000000, cpu_agreement_ns_per_offer=100000,
    idle_carryover_ns_per_offer=10000, max_observer_wall_ns=20000000,
    miss_equivalence_margin_pp=2, mean_equivalence_margin_ns=100000,
    paired_t_multiplier=4.774, paired_t_df=5, model_interval_coverage=.995,
    transition_min_pct=10, transition_max_pct=90, retries=0,
    boundary_offers=90, overhead_offers=7800, total_offers=7890,
    host_policy_writes=False, scheduler_switch_writes=False, stats_switch_required=0,
    predictive_usefulness_tested=False, qualification_only=True,
    population='all offered responses, ordinary failures as misses; throttling retained',
    observer='two identity-bracketed worker schedstat snapshots around warmup; serialization and provisional feature calculation before target',
    inference='Six paired block differences per rate; intervals conditional on approximately independent normal differences. No distribution-free or absolute counter accuracy guarantee.')
sha, read, save, require = prior.sha, prior.read, prior.save, prior.require
verify_evidence = prior.verify_evidence


def cfg(role, index, rate, arm, block=None):
    require(role in ('boundary', 'overhead') and rate in (4, 8) and arm in ('off', 'on'), 'Foreign qualification cell')
    require((role == 'boundary' and arm == 'on' and block is None) or
            (role == 'overhead' and block in range(1, 7)), 'Foreign qualification block')
    return dict(role=role, index=index, rate_rps=rate, arm=arm, policy='P0', block=block,
                profile=str(rate), interval_ns=1000000000 // rate, warmup_count=25,
                count=20 if role == 'boundary' else 300)


def schedule(seed):
    rng = random.Random(seed)
    boundary = [cfg('boundary', i, rate, 'on') for i, rate in enumerate((4, 8), 1)]
    overhead = []
    for block in range(1, 7):
        for rate in rng.sample([4, 8], 2):
            for arm in rng.sample(['off', 'on'], 2):
                overhead.append(cfg('overhead', len(overhead) + 1, rate, arm, block))
    return dict(seed=seed, boundary=boundary, overhead=overhead)


def sources():
    extra = ('analysis/worker_wait_features.py', 'analysis/test_worker_wait_features.py',
             'diagnostic/nginx_rate_transfer_study.py', 'diagnostic/nginx_rate_transfer_model.py',
             'diagnostic/nginx_power_confirmation_guard.py')
    return {p: sha(ROOT / p) for p in (*FILES, *extra)}


def verify_prepared(boot=True):
    verify_prior()
    seal = read(BASE / 'preparation-seal.json')
    for path, digest in seal['files_sha256'].items():
        require(sha(ROOT / path) == digest, 'Prepared qualification input changed: ' + path)
    require(read(BASE / 'protocol.json') == PROTOCOL, 'Qualification protocol changed')
    sched = read(BASE / 'schedule.json')
    require(sched == schedule(sched['seed']), 'Qualification schedule changed')
    if boot:
        import nginx_qualify as q
        import nginx_power_confirmation_guard as g
        require(q.h.common.baseline() == seal['baseline'], 'Prepared boot/topology changed')
        g.check_baseline(g.snapshot())
        require(g.snapshot() == read(BASE / 'policy-baseline.json'), 'Fixed policy changed')
        require(Path('/proc/sys/kernel/sched_schedstats').read_text().strip() == '0', 'Scheduler-statistics switch changed')
    return sched


def verify_prior():
    # Preserve the old checks, suppress their unrelated legacy status banner.
    with contextlib.redirect_stdout(io.StringIO()):
        prior.verify_prepared(False)
