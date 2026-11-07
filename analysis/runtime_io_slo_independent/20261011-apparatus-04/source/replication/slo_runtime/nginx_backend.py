"""Fresh stock-NGINX qualification/calibration with retained complete-body guards."""
from pathlib import Path
import time

import common as r
import nginx_common as n
import nginx_prediction_common as c
import nginx_prediction_study as retained
import collectors as adapters


class Backend:
    application='NGINX'
    def __init__(self,root,directory):
        self.root,self.directory=Path(root),Path(directory)
        self.reader=adapters.OfferReader('NGINX',vars(retained))
        self.source=(self.root/'adapted/nginx_collector.py').read_text()
        self.namespace=None

    def prepare(self):
        check=r.check_host(self.root,control_pinned=True);n.inputs()
        r.write(self.directory/'runtime_preparation.json',dict(check=check,
            software_checked=True,runtime_qualified=False,traffic_started=False))

    def begin(self,hook):
        n.inputs();retained.h.desktop_absent()
        observer=r.read(self.directory/'observer.json')
        import leftover_observer_review
        review=leftover_observer_review.review(observer['path'])
        r.require(review==observer['review'] and review['performance_eligible'] and
                  review['boot_id'].strip()==r.baseline()['boot_id'],'fresh NGINX observer review unavailable')
        self.namespace=adapters.bind(self.source,vars(retained),hook)

    def configs(self,role):return c.configs('pilot' if role=='qualification' else role)
    def case(self,cfg):return self.directory/cfg['role']/('cohort-'+str(cfg['index']))

    def collect(self,cfg):
        n.inputs();retained.h.desktop_absent();time.sleep(10)
        case=self.case(cfg);case.parent.mkdir(parents=True,exist_ok=True)
        result=self.namespace['trial'](case,cfg,True)
        replay=self.namespace['replay_case'](case,cfg)
        r.require(replay==result,'NGINX raw/resource replay changed')
        return result

    def reference(self,cohorts,plan):
        r.require([row['config'] for row in cohorts]==c.configs('calibration'),'four fresh NGINX calibration cohorts required')
        r.require(all(not row['domain_exits'] for row in cohorts),'NGINX calibration applicability exit')
        reference=[]
        for row in cohorts:
            reference.extend(record['e2e_ns'] if record['success'] else None for record in row['outcomes'])
        r.require(len(reference)==1600,'NGINX reference offer conservation differs')
        return reference

    def target_values(self,case,cfg):return self.reader
