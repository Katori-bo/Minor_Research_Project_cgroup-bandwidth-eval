"""One NGINX-only amendment, preserved lineage and pre-admission authentication."""
from pathlib import Path
import os
import subprocess
import sys
import time
import common as c
import cost


def original_ledger(root):
    root=Path(root).resolve();package=c.verify_package(root)
    ref=package['local_supplement'];parent=(root/ref['relative_parent_package']).resolve()
    c.require(parent.parent==root.parent and parent!=root,'keep preserved parent beside completion package')
    old=c.verify_package(parent)
    c.require(c.sha(parent/'runtime_seal.json')==ref['parent_package_seal_sha256'] and
              c.sha(parent/'scientific/plan.json')==ref['parent_scientific_plan_sha256'],'prior source changed')
    from assemble_returns import verify_return
    rows=[]
    for app in ('Go','NGINX'):
        directory=parent/'runs/host01'/app
        verify_return(directory,parent)
        c.require(c.sha(directory/'return_seal.json')==ref['prior_returns'][app],'prior return changed')
        finish=c.read(directory/'supervisor_finished.json')
        c.require(finish['allocation_closed'],'prior campaign still open')
        available=len(list((directory/'decisions').glob('*_score.json')))
        c.require(available==(18 if app=='Go' else 0),'prior outcome inventory differs')
        rows.append(dict(application=app,planned_windows=18,completed_target_windows=available,
            unavailable_target_windows=18-available,summary=finish,
            return_seal_sha256=c.sha(directory/'return_seal.json'),
            acquired_raw_offers=cost.acquired(directory),source_package=str(parent)))
    acceptance=parent/'runs/host01/amendment_acceptance.json';setup=parent/'runs/host01/setup/setup.json'
    c.require(c.sha(acceptance)==ref['prior_acceptance_sha256'] and c.sha(setup)==ref['prior_setup_sha256'],
              'prior acceptance/setup changed')
    original=c.read(acceptance)['original_attempt_ledger']
    # Resolve original v6 and its immutable v3/v4 returns without trusting only a copied ledger.
    v6=(parent/old['local_supplement']['relative_parent_package']).resolve()
    c.require(c.sha(v6/'runtime_seal.json')==old['local_supplement']['parent_package_seal_sha256'],
              'original v6 changed')
    for app in ('Go','NGINX'):
        origin=c.campaign_origin(v6,app)
        verify_return(origin/'runs/host01'/app,origin)
    known=c.read(root/'known_prior/return.json')
    c.require(known['primary_available_windows']==18 and len(known['primary_event_windows'])==1,
              'known Go result disclosure differs')
    return dict(original_study=original,prior_supplement_study_id='slo-local-supplement-01',
        prior_supplement_allocations=rows,prior_setup_cost=c.read(setup),known_Go_outcomes_disclosed=True,
        known_Go_primary_event_count=1,prior_nginx_outcomes_available=False,
        new_planned_windows=18,combined_attempt_ledger_slots=126,combined_planned_cap_sec=48600,
        replaces_prior_slots=False,primary_results_pooled=False)


def prelaunch(root,app,accepted,allocation_confirmed):
    c.require(accepted,'NGINX completion requires --amendment-accepted')
    c.require(allocation_confirmed,'native host requires --allocation-confirmed')
    c.require(app=='NGINX','NGINX-only amendment; Go cannot be repeated')
    root=Path(root).resolve();c.verify_package(root);original_ledger(root)
    state=root/'runs/host01'
    c.require(not (state/'NGINX').exists(),'campaign already consumed; no retry')
    c.require(not (state/'setup').exists(),'preserve setup attempt; no resume/overwrite')
    c.require(not (state/'auth_precheck').exists(),'preserve precheck attempt; no retry')


def accept(root,accepted):
    root=Path(root).resolve();package=c.verify_package(root)
    if 'local_supplement' not in package:return
    c.require(accepted,'NGINX completion requires --amendment-accepted (18 new slots; +2700 s cap)')
    plan=c.read(root/'scientific/plan.json');ledger=original_ledger(root)
    expected=dict(amendment_id=plan['id'],plan_sha256=c.sha(root/'scientific/plan.json'),
        package_seal_sha256=c.sha(root/'runtime_seal.json'),accepted=True,
        supplemental_planned_windows=18,additional_campaign_cap_sec=2700,original_attempt_ledger=ledger)
    path=root/'runs/host01/amendment_acceptance.json'
    if path.exists():
        saved=c.read(path);saved.pop('accepted_monotonic_ns',None)
        c.require(saved==expected,'existing amendment acceptance differs; preserve evidence')
    else:c.write(path,dict(expected,accepted_monotonic_ns=time.monotonic_ns()))


def audit_command(root,path):
    return ['sudo','-n',sys.executable,'-B',str(Path(root)/'diagnostic/leftover_observer_audit.py'),
            '--output',str(path)]


def readiness(root):
    """Validate exact new successful inventory, boot and freshness before allocation mkdir."""
    root=Path(root).resolve();path=root/'runs/host01/auth_precheck/success.json'
    c.require(path.exists(),'successful privileged precheck required before campaign admission')
    value=c.read(path)
    c.require(value['package_seal_sha256']==c.sha(root/'runtime_seal.json') and
              value['plan_sha256']==c.sha(root/'scientific/plan.json'),'precheck source differs')
    c.require(value['boot_id']==c.identity(os.getpid())['boot_id'],'precheck boot changed')
    age=time.monotonic_ns()-value['finished_ns']
    c.require(0<=age<=60*10**9,'precheck stale; preserve attempt without automatic retry')
    audit=root/'runs/host01/audits/NGINX_precheck.json'
    c.require(c.sha(audit)==value['audit_sha256'],'precheck inventory changed')
    c.require(not (path.parent/'failure.json').exists(),'failed precheck cannot admit a campaign')
    import leftover_observer_review as review
    result=review.review(audit)
    c.require(result==value['review'] and result['performance_eligible'],'precheck ownership review differs')
    return value


def precheck(root,accepted,confirmed):
    c.require(accepted,'NGINX completion requires --amendment-accepted')
    c.require(confirmed,'native host requires --allocation-confirmed')
    c.require(sys.stdin.isatty(),'privileged precheck requires external interactive terminal')
    root=Path(root).resolve();accept(root,accepted)
    from v31_common import require_desktop_absent
    require_desktop_absent();c.check_host(root)
    state=root/'runs/host01'
    c.require(not (state/'NGINX').exists(),'campaign already consumed; no retry')
    directory=state/'auth_precheck';directory.mkdir(parents=True)
    started=time.monotonic_ns();audit=state/'audits/NGINX_precheck.json'
    c.write(directory/'attempt.json',dict(started_ns=started,no_traffic=True,
        campaign_admitted=False,inventory_bound_sec=120,authentication_bound_sec=300,package_seal_sha256=c.sha(root/'runtime_seal.json')))
    try:
        authenticated_start=time.monotonic_ns()
        c.write(directory/'authentication_start.json',dict(started_ns=authenticated_start,bound_sec=300))
        subprocess.run(['sudo','-v'],check=True,timeout=300)
        c.write(directory/'authentication_end.json',dict(finished_ns=time.monotonic_ns(),
            elapsed_sec=(time.monotonic_ns()-authenticated_start)/1e9,successful=True))
        inventory_started=time.monotonic_ns()
        subprocess.run(audit_command(root,audit),check=True,timeout=120)
        import leftover_observer_review as review
        result=review.review(audit);c.require(result['performance_eligible'],'observer inventory ineligible')
        c.require(result['boot_id']==c.identity(os.getpid())['boot_id'],'audit boot changed')
        finished=time.monotonic_ns()
        c.write(directory/'success.json',dict(package_seal_sha256=c.sha(root/'runtime_seal.json'),
            plan_sha256=c.sha(root/'scientific/plan.json'),boot_id=result['boot_id'],finished_ns=finished,
            elapsed_sec=(finished-started)/1e9,inventory_elapsed_sec=(finished-inventory_started)/1e9,audit_sha256=c.sha(audit),review=result,
            no_traffic=True,campaign_admitted=False,readiness_cost_separate_from_campaign=True))
    except BaseException as exc:
        c.write(directory/'failure.json',dict(error=str(exc),elapsed_sec=(time.monotonic_ns()-started)/1e9,
            no_traffic=True,campaign_admitted=False));raise
    print('Privileged inventory precheck passed; admitting one NGINX campaign next.')


if __name__=='__main__':
    import argparse
    root=Path(__file__).resolve().parents[1]
    sys.path[:0]=[str(root/p) for p in ('runtime','diagnostic','scripts','analysis','slo')]
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['precheck'])
    parser.add_argument('--amendment-accepted',action='store_true')
    parser.add_argument('--allocation-confirmed',action='store_true')
    args=parser.parse_args();precheck(root,args.amendment_accepted,args.allocation_confirmed)
