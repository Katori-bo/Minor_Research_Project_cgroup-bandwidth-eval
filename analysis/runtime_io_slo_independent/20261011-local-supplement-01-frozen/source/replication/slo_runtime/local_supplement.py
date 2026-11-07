"""Explicit amendment acceptance and read-only original-attempt accounting."""
from pathlib import Path
import time

import common as c
import cost


def original_ledger(root):
    root=Path(root).resolve();package=c.verify_package(root)
    reference=package['local_supplement'];parent=(root/reference['relative_parent_package']).resolve()
    c.require(parent.parent==root.parent and parent!=root,'original package must remain beside supplement')
    old=c.verify_package(parent)
    c.require(c.sha(parent/'runtime_seal.json')==reference['parent_package_seal_sha256'],
              'original parent package changed')
    c.require(old['scientific_plan_sha256']==reference['parent_scientific_plan_sha256'] and
              old['host']==package['host'],'original scientific identity/host changed')
    rows=[]
    for app in old['host']['order']:
        origin=c.campaign_origin(parent,app);directory=origin/'runs'/old['host']['id']/app
        finish=c.read(directory/'supervisor_finished.json')
        c.require(finish['allocation_closed'],'original allocation is not closed')
        ref=reference['original_closed_attempts'][app]
        c.require(c.sha(directory/'return_seal.json')==ref['return_seal_sha256'] and
                  c.sha(origin/'runtime_seal.json')==ref['package_seal_sha256'],
                  'original closed evidence changed')
        setup=origin/'runs'/old['host']['id']/'setup/setup.json'
        c.require(setup.exists() and c.sha(setup)==ref['setup_sha256'],
                  'original setup cost record changed')
        if setup.exists():
            c.require(c.read(setup)['package_seal_sha256']==c.sha(origin/'runtime_seal.json'),
                      'original setup belongs to another package')
        rows.append(dict(application=app,source_package=str(origin),
            campaign_id=c.read(directory/'allocation.json')['campaign']['id'],
            planned_windows=18,unavailable_target_windows=18,
            source_package_seal_sha256=c.sha(origin/'runtime_seal.json'),
            return_seal_sha256=c.sha(directory/'return_seal.json'),summary=finish,
            acquired_raw_offers=cost.acquired(directory),
            original_acquisition_cost=c.read(directory/'acquisition_cost.json')
                if (directory/'acquisition_cost.json').exists() else None,
            original_preparation_cost=c.read(directory/'preparation_cost.json')
                if (directory/'preparation_cost.json').exists() else None,
            setup_cost=c.read(setup) if setup.exists() else None,
            preparation_is_subset_not_additive=True))
    return dict(parent_study_id='independent-slo-decision-v1',parent_planned_windows=72,
        preserved_local_unavailable_windows=36,pending_intel_windows=36,
        original_allocations=rows,supplement_replaces_original_slots=False,
        original_and_supplement_primary_results_pooled=False,
        combined_attempt_ledger_slots=108,combined_planned_cap_sec=45900)


def prelaunch(root,app,accepted,allocation_confirmed):
    """Read-only refusal before a launcher closes apps or begins setup."""
    root=Path(root).resolve()
    c.require(accepted,'local supplement requires --amendment-accepted')
    c.require(allocation_confirmed,'native host allocation requires --allocation-confirmed')
    package=c.verify_package(root);original_ledger(root)
    c.require(app in ('Go','NGINX'),'unknown supplemental application')
    state=root/'runs'/package['host']['id']
    c.require(not (state/app).exists(),'supplemental campaign already consumed; preserve it, no retry')
    setup=state/'setup'
    if app=='Go':
        c.require(not setup.exists(),'supplemental setup already attempted; preserve it, no automatic resume')
    else:
        c.require((setup/'setup.json').exists() and not (setup/'failure.json').exists(),
                  'successful supplemental setup required; first run Go')
        c.require(c.read(setup/'setup.json')['package_seal_sha256']==c.sha(root/'runtime_seal.json'),
                  'supplemental setup source differs')
        previous=state/'Go'
        c.require((previous/'supervisor_finished.json').exists() and
                  c.read(previous/'supervisor_finished.json')['allocation_closed'],
                  'close supplemental Go before NGINX')
        from assemble_returns import verify_return
        verify_return(previous,root)


def accept(root,accepted):
    """Called before setup/launch; an absent acknowledgment creates no state."""
    root=Path(root).resolve();package=c.verify_package(root)
    if 'local_supplement' not in package:return
    c.require(accepted,'local supplement requires --amendment-accepted (36 new slots; +15300 s campaign cap)')
    ledger=original_ledger(root);plan=c.read(root/'scientific/plan.json')
    expected=dict(amendment_id=plan['id'],plan_sha256=c.sha(root/'scientific/plan.json'),
        package_seal_sha256=c.sha(root/'runtime_seal.json'),accepted=True,
        supplemental_planned_windows=36,additional_campaign_cap_sec=15300,
        original_attempt_ledger=ledger)
    path=root/'runs'/package['host']['id']/'amendment_acceptance.json'
    if path.exists():
        saved=c.read(path);saved.pop('accepted_monotonic_ns',None)
        c.require(saved==expected,'existing amendment acceptance differs; preserve evidence')
    else:
        c.write(path,dict(expected,accepted_monotonic_ns=time.monotonic_ns()))
