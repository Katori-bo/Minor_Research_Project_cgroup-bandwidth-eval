import unittest
from inspect_scheduler_handoffs import handoffs


def ev(g,old,new,t,actor=-1,p=0,stack=''):
    return dict(target_g=g,old=old,new=new,time_ns=t,actor_g=actor,p=p,Stack=stack)


class HandoffTests(unittest.TestCase):
    def fixture(self):
        return [ev(7,'Runnable','Running',10),
                ev(0,'Waiting','Runnable',20,7,stack='main.(*service).runJob'),
                ev(7,'Running','Waiting',30),ev(0,'Runnable','Running',40)]

    def test_same_p_handoff_preserves_zero_id_and_boundary(self):
        result=handoffs(self.fixture(),40,41)
        self.assertEqual(result['counts']['worker_reply_handoffs'],1)
        self.assertEqual(result['examples'][0]['target_start']['target_g'],0)
        self.assertFalse(handoffs(self.fixture(),0,40)['counts'].get('worker_reply_handoffs'))

    def test_old_wakeup_or_other_p_does_not_prove_direct_handoff(self):
        for field,value in [('time_ns',5),('p',1),('actor_g',9)]:
            rows=self.fixture();rows[1][field]=value
            rows.sort(key=lambda e:e['time_ns'])
            self.assertFalse(handoffs(rows,0,100)['counts'].get('same_P_waker_then_handoff'))

    def test_snapshot_and_intervening_dispatch(self):
        rows=self.fixture()
        rows.insert(2,ev(0,'Runnable','Runnable',25))
        self.assertEqual(handoffs(rows,0,100)['counts']['worker_reply_handoffs'],1)
        rows=self.fixture()
        rows.insert(3,ev(8,'Runnable','Running',35))
        self.assertFalse(handoffs(rows,0,100)['counts'].get('worker_reply_handoffs'))


if __name__=='__main__':
    unittest.main()
