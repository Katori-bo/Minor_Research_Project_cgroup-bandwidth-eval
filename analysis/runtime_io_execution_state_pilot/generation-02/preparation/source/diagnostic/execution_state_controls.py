"""Fixed-scope CPU bound control; no commands or arbitrary sysfs paths over IPC."""
from pathlib import Path
import time

SYS = Path('/sys/devices/system/cpu')
CPUS = (2,3,4,5)
FIELDS = ('scaling_driver','scaling_governor','energy_performance_preference',
          'scaling_min_freq','scaling_max_freq','boost','related_cpus',
          'cpuinfo_min_freq','cpuinfo_max_freq')


def snapshot(root=SYS):
    result={}
    for cpu in CPUS:
        base=root/f'cpu{cpu}'
        result[str(cpu)]={f:(base/'cpufreq'/f).read_text().strip() for f in FIELDS}
        result[str(cpu)]['siblings']=(base/'topology/thread_siblings_list').read_text().strip()
        result[str(cpu)]['nominal_freq_mhz']=(base/'acpi_cppc/nominal_freq').read_text().strip()
    return result


def plan(before):
    if set(before)!={str(c) for c in CPUS}: raise ValueError('wrong CPU scope')
    nominal=[]
    for cpu in CPUS:
        r=before[str(cpu)]
        if r['scaling_driver']!='amd-pstate-epp' or r['related_cpus']!=str(cpu):
            raise ValueError('unsupported driver or shared policy; redesign control')
        if r['siblings']!=('2-3' if cpu in (2,3) else '4-5'):
            raise ValueError('CPU sibling topology changed')
        nominal.append(int(r['nominal_freq_mhz'])*1000)
    target=(min(nominal)*80//100)//1000*1000
    low,high=target*99//100,target*101//100
    after={k:dict(v) for k,v in before.items()}
    for r in after.values():
        if not int(r['cpuinfo_min_freq'])<=low<=high<=int(r['cpuinfo_max_freq']):
            raise ValueError('conservative target outside supported range')
        r.update(scaling_min_freq=str(low),scaling_max_freq=str(high))
    return dict(automatic=before,constrained=after,target_khz=target,
                lower_khz=low,upper_khz=high,boost_changed=False)


def set_bounds(expected,root=SYS):
    # Raise maximum first if necessary, then lower minimum if necessary. This
    # also restores safely from a partially completed transition.
    for cpu in CPUS:
        base=root/f'cpu{cpu}/cpufreq'; want=expected[str(cpu)]
        low,high=int(want['scaling_min_freq']),int(want['scaling_max_freq'])
        current_low=int((base/'scaling_min_freq').read_text())
        current_high=int((base/'scaling_max_freq').read_text())
        if high>current_high: (base/'scaling_max_freq').write_text(str(high))
        if low<current_low: (base/'scaling_min_freq').write_text(str(low))
        (base/'scaling_max_freq').write_text(str(high))
        (base/'scaling_min_freq').write_text(str(low))


def restore(before,root=SYS):
    errors=[]
    # Attempt every policy even if another policy restoration fails.
    for cpu in CPUS:
        try:
            expected={str(c):dict(before[str(c)]) for c in CPUS}
            # Fixed per-policy implementation, preserving all untouched fields.
            base=root/f'cpu{cpu}/cpufreq'; r=expected[str(cpu)]
            low,high=int(r['scaling_min_freq']),int(r['scaling_max_freq'])
            if high>int((base/'scaling_max_freq').read_text()):
                (base/'scaling_max_freq').write_text(str(high))
            if low<int((base/'scaling_min_freq').read_text()):
                (base/'scaling_min_freq').write_text(str(low))
            (base/'scaling_max_freq').write_text(str(high))
            (base/'scaling_min_freq').write_text(str(low))
        except Exception as e: errors.append(f'cpu{cpu}: {e}')
    try:
        observed=snapshot(root)
        if observed!=before: errors.append('restoration readback differs from original snapshot')
    except Exception as e:
        observed=None; errors.append(str(e))
    return dict(restored=not errors,errors=errors,observed=observed,timestamp=time.time())
