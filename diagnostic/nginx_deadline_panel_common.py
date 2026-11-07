"""Fresh calibration-defined deadline-panel study; prior evidence stays sealed."""
import contextlib
import io
import itertools
import random
from pathlib import Path
import nginx_power_confirmation_common as previous

ROOT=previous.ROOT
old=previous.old
BASE=ROOT/'analysis/runtime_io_nginx_deadline_panel/generation-01'
POLICIES=previous.POLICIES
CELLS=previous.CELLS
FILES=('diagnostic/nginx_deadline_panel_common.py','diagnostic/nginx_deadline_panel_guard.py',
    'diagnostic/nginx_deadline_panel_model.py','diagnostic/nginx_deadline_panel_study.py',
    'diagnostic/test_nginx_deadline_panel.py','diagnostic/start_nginx_deadline_panel.sh',
    'docs/runtime_io_nginx_deadline_panel_protocol_20261010.md')
PROTOCOL=dict(schema='nginx-deadline-panel-v1',policies=POLICIES,target_cpu=2,
    governor='powersave',quota_us=25000,period_us=100000,rates=[4,8],
    calibration_rate=5,calibration_cohorts=4,calibration_count=400,blocks=6,
    validation_count=300,warmup_count=25,qualification_count=20,
    qualification_lifetime_count=400,quantiles=['1/10','1/4','1/2','3/4','9/10'],
    quantile_rule='floor(q*(n-1)), all offered outcomes; failure mass at infinity',
    historical_deadline_ns=20565395,settling_sec=10,service_active_sec=120,
    within_service_reserve_sec=8,policy_lease_sec=150,qualification_total_sec=600,
    campaign_total_sec=2700,cohort_reserve_sec=150,cleanup_reserve_sec=120,retries=0,
    scientific_measurement_offers=8800,scientific_total_offers=9500,
    qualification_total_offers=1030,total_offers=10530,
    accuracy_upper_reference_pp=5,primary_t_multiplier=3.164,primary_interval_coverage=.975,
    primary_score='Per policy and block, max over five cutoffs of the mean absolute all-offer error across rates4/8; six blocks',
    primary_family='Two matched-policy accuracy intervals; Bonferroni coverage >=95% conditional on independent approximately normal block scores. Calibration uncertainty not propagated.',
    descriptive_t_multiplier=2.571,improvement_reference_pp=2,
    stats_switch_required=0,fixed_frequency=False,new_estimator=False,
    population='All offers under the declared quota including throttling',
    failed_offers='Misses at every finite deadline; no success-only renormalization',
    observers='Original stock client/cgroup controls, policy boundary readbacks and CPU3 procstat; no worker sampler',
    equal_acquisition_for_methods=True,all_deadline_population_guarantee=False)
sha,read,require,save=previous.sha,previous.read,previous.require,previous.save
verify_evidence=previous.verify_evidence


def sources():
    extra=('diagnostic/nginx_power_confirmation_study.py','diagnostic/nginx_power_confirmation_model.py',
        'diagnostic/nginx_prediction_study.py','diagnostic/test_nginx_power_confirmation.py')
    return {name:sha(ROOT/name) for name in (*FILES,*extra)}


def config(role,index,policy,rate,block=None):
    require(role in ('qualification','qualification_lifetime','calibration','validation'),'Foreign role')
    require(policy in POLICIES and type(rate) is int and rate in (4,5,8),'Foreign treatment')
    require(type(index) is int and index>0,'Foreign index')
    require((role in ('calibration','qualification_lifetime'))==(rate==5),'Foreign calibration/lifetime rate')
    require((role=='validation' and type(block) is int and block in range(1,7)) or
            (role!='validation' and block is None),'Foreign block')
    return dict(role=role,index=index,policy=policy,rate_rps=rate,
        interval_ns=1000000000//rate,block=block,count=PROTOCOL[role+'_count'],
        warmup_count=25,profile={4:'A',5:'B',8:'C'}[rate])


def schedule(seed):
    rng=random.Random(seed)
    orders=sorted(set(itertools.permutations(['P0','P0','P1','P1'])))
    calibration=[config('calibration',i,p,5) for i,p in enumerate(rng.choice(orders),1)]
    validation=[]
    for b in range(1,7):
        first=len(validation)
        validation.extend(config('validation',first+j,p,r,b) for j,(p,r) in enumerate(rng.sample(CELLS,4),1))
    qualification=[config('qualification',i,p,r) for i,(p,r) in enumerate(CELLS,1)]
    qualification.extend(config('qualification_lifetime',i,p,5) for i,p in enumerate(('P0','P1'),5))
    return dict(seed=seed,qualification=qualification,calibration=calibration,validation=validation)


def verify_prior():
    with contextlib.redirect_stdout(io.StringIO()):
        previous.verify_prepared(False)
    previous.verify_evidence(previous.BASE/'campaign')
    require(read(previous.BASE/'campaign/summary.json')['complete'],'Complete prior power study required')


def verify_prepared(boot=True):
    verify_prior()
    seal=read(BASE/'preparation-seal.json');lineage=read(BASE/'lineage.json')
    require(sha(previous.BASE/'campaign/evidence-seal.json')==lineage['prior_power_evidence_sha256'],
        'Prior power evidence changed')
    require(sha(ROOT/'analysis/runtime_io_deadline_scope/20261010/seal.json')==lineage['development_scope_seal_sha256'],
        'Development scope assessment changed')
    require(read(BASE/'protocol.json')==PROTOCOL,'Panel protocol changed')
    sched=read(BASE/'schedule.json');require(sched==schedule(sched['seed']),'Panel schedule changed')
    for name,digest in seal['files_sha256'].items():require(sha(ROOT/name)==digest,'Prepared panel input changed: '+name)
    if boot:
        import nginx_qualify as q
        import nginx_deadline_panel_guard as guard
        require(seal['baseline']==q.h.common.baseline(),'Panel boot/topology changed')
        actual=guard.snapshot();guard.check_baseline(actual)
        require(actual==read(BASE/'policy-baseline.json'),'Panel prepared policy baseline changed')
        require(Path('/proc/sys/kernel/sched_schedstats').read_text().strip()=='0','Scheduler switch changed')
    return sched
