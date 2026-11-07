"""Fresh Go preparation and inherited raw/capacity/timing qualification."""
import json
import os
from pathlib import Path
import shutil
import time

import common as r
import v31_common as c
import v31_study as retained
import v31_verify as verify
import v31_model as model
import v31_raw as raw
from v31_service import Service,command
import collectors as adapters


class Backend:
    application='Go'
    def __init__(self,root,directory):
        self.root,self.directory=Path(root),Path(directory)
        self.session=self.directory/'session'
        self.reader=adapters.OfferReader('Go',vars(retained))
        self.source=(self.root/'adapted/go_collector.py').read_text()
        self.namespace=None

    def prepare(self):
        r.check_host(self.root,control_pinned=True);retained.require_quiet_host()
        self.session.mkdir()
        shutil.copytree(self.root/'assets/go_bundle',self.session/'bundle')
        previous=verify.verify_bundle(self.session)
        out=self.session/'preparation';out.mkdir()
        try:
            for name in ('gate','loadgen','image.server','publication_source.go','publication_build.json','counter'):
                shutil.copy2(self.session/'bundle'/name,out/name)
            c.capacity(self.session)
            image=json.loads(command(['docker','image','inspect',previous['image']]))[0];c.save(out/'image.json',image)
            manifest=dict(previous,bundle_seal=c.digest(self.session/'bundle/seal.json'),baseline=c.baseline(),
                functional_passed=False,performance_run=False,runtime_qualified=True,created=time.time())
            c.save(out/'manifest.json',manifest)
            d=out/'resource_preflight';d.mkdir();service=Service(self.session,c.functional_configs()[0],d)
            try:
                service.create();manifest['resource_baseline']=c.read(d/'initial.json')['resource_baseline']
                c.save(out/'manifest.json',manifest)
                c.save(d/'observed.json',dict(gate_released=False,performance_run=False,limits=service.expected_limits))
            finally:service.close()
            functional={}
            for cfg in c.functional_configs():
                retained.require_quiet_host()
                d=retained.collect(self.session,out/'functional'/cfg['trial'],cfg,'functional',True)
                verify.verify_trial(self.session,d,manifest,True)
                functional[cfg['trial']]=dict(path=str(d.relative_to(out)),seal=c.digest(d/'seal.json'))
            manifest.update(functional=functional,functional_passed=True,created=time.time())
            c.save(out/'manifest.json',manifest);c.seal(out);verify.verify_preparation(self.session)
        except BaseException as exc:
            c.save(out/'preparation_failure.json',dict(error=str(exc)));c.seal(out);raise

    def begin(self,hook):
        verify.verify_preparation(self.session);retained.require_quiet_host()
        observer=r.read(self.directory/'observer.json')
        import leftover_observer_review
        review=leftover_observer_review.review(observer['path'])
        r.require(review==observer['review'] and review['performance_eligible'],'fresh observer review changed')
        prep=c.read(self.session/'preparation/manifest.json')
        import datetime
        audit=c.read(Path(observer['path']))
        r.require(audit['boot_id']['text'].strip()==prep['baseline']['boot_id'] and
            audit['kernel']==prep['baseline']['kernel'] and
            datetime.datetime.fromisoformat(audit['at']).timestamp()>=prep['created'], 'observer inventory predates fresh preparation/boot')
        retained.environment(self.session)
        self.namespace=adapters.bind(self.source,vars(retained),hook)
        reset=self.namespace['reset']
        def counted_reset(service):
            import kernel_service_bridge as bridge
            bridge.HTTP_CALLS['POST reset']=bridge.HTTP_CALLS.get('POST reset',0)+1
            return reset(service)
        self.namespace['reset']=counted_reset

    def configs(self,role):
        return c.calibration_configs() if role=='calibration' else c.validation_configs()

    def case(self,cfg):return self.session/'slots'/cfg['trial']/'attempt-01'

    def collect(self,cfg):
        verify.verify_preparation(self.session);verify.verify_environment(self.session)
        case=self.case(cfg);failure=None
        try:self.namespace['collect'](self.session,case,cfg,'run')
        except ValueError as exc:
            # The inherited dispatch gate runs after all raw/phase records were
            # written. A complete trusted dispatch exit is retained adverse.
            if str(exc)!='technical client dispatch timing failure':raise
            failure=str(exc)
        derived=raw.replay(case)
        r.require(derived==c.read(case/'derived.json'),'Go raw replay changed')
        phase=model.trial(derived,c.read(case/'server_metrics.json'),c.read(case/'host_server_anchors.json'),
            None,cfg,c.design(),c.read(case/'initial.json')['cgroup']+'/cpu.stat')
        r.require(phase==c.read(case/'phase_accounting.json'),'Go phase replay changed')
        if failure is None:verify.verify_trial(self.session,case,c.read(self.session/'preparation/manifest.json'))
        return dict(config=cfg,derived=derived,phase=phase,dispatch_exit=failure is not None,
                    domain_exits=(['dispatch_gate'] if failure else [])+
                        (['inherited_scientific_domain'] if cfg['role']=='validation' and not phase['scientific_domain_pass'] else []))

    def reference(self,cohorts,plan):
        configs=c.calibration_configs()
        r.require([row['config'] for row in cohorts]==configs,'all 16 fresh Go calibration slots required')
        refs={cfg['trial']:dict(path=str(self.case(cfg).relative_to(self.session)),seal=c.digest(self.case(cfg)/'seal.json')) for cfg in configs}
        values=[row['phase'] for row in cohorts]
        prerequisite=model.fit_calibration(self.session,values,refs)
        c.save(self.directory/'go_calibration_prerequisite.json',prerequisite)
        r.require(prerequisite.get('usable') and prerequisite.get('timing_status')=='available',
                  'inherited Go capacity/timing prerequisite unavailable')
        reference=[]
        selected=plan['Go']['complete_reference_trials']
        for row in cohorts:
            if row['config']['trial'] in selected:
                reference.extend(record['e2e_ns'] if record['success'] else None for record in row['derived']['requests'])
        r.require(len(reference)==plan['Go']['reference_offers_expected_if_qualified'],'Go reference offer conservation differs')
        return reference

    def target_values(self,case,cfg):
        # Raw replay has established complete accounting before this call. A
        # measurement dispatch exit is not allowed to erase its all-offer label.
        class CompleteReader(adapters.OfferReader):
            def values(inner,record,config,warmup=False):
                if warmup:return super().values(record,config,True)
                offsets=c.validate_client(record,config);rows={x['ID']:x for x in record['requests']}
                return [rows[i]['EndToEndLatencyNs'] if i in rows and not rows[i]['Error'] and
                        rows[i]['StatusCode']==200 else None for i in range(len(offsets))]
        return CompleteReader('Go',vars(retained))
