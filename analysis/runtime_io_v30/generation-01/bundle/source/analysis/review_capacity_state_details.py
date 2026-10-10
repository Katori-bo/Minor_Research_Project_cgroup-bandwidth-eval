#!/usr/bin/env python3
"""Read saved processing-wall/frequency records; no new observation or workload."""
from pathlib import Path
import statistics
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'diagnostic'))
import v23_common as c
from v23_raw import distribution
from kernel_bridge_analysis import clock_join


def review(session):
    refs=c.read(session/'predictions/manifest.json')['calibration_refs'];result=[]
    for name,ref in refs.items():
        d=c.resolve(session,ref['path']);c.verify_seal(d)
        if c.digest(d/'seal.json')!=ref['seal']:raise ValueError('retained calibration changed')
        derived=c.read(d/'derived.json');mapping=derived['clocks'];server=c.read(d/'server_metrics.json')
        origin=mapping['client_test_start_ns']+(mapping['server_minus_client_lower_ns']+mapping['server_minus_client_upper_ns'])/2
        joined=clock_join(c.read(d/'host_server_anchors.json'),mapping,server['clock_generation'])
        start=c.read(d/'started.json');epoch_offset=start['wall_time']-start['monotonic_ns']/1e9
        host_client=(joined['kernel_minus_client_lower_ns']+joined['kernel_minus_client_upper_ns'])/2
        monitor=c.read(d/'monitor.json');phases={}
        for label,(a,b) in [('busy',(6.5,9.5)),('low',(1,4))]:
            times=[j['processing_ns']/1e6 for j in server['events']
                   if a<=((j['worker_start_ns']-origin)/1e9)%10<b]
            samples=[r for r in monitor if 0<=((r['timestamp']-epoch_offset)*1e9-host_client-mapping['client_test_start_ns'])/1e9<60
                     and a<=(((r['timestamp']-epoch_offset)*1e9-host_client-mapping['client_test_start_ns'])/1e9)%10<b]
            freq={cpu:dict(n=len(values),mean_mhz=statistics.mean(values) if values else None)
                  for cpu in ('cpu2','cpu4')
                  for values in [[r['freqs_mhz'][cpu] for r in samples if cpu in r['freqs_mhz']]]}
            phases[label]=dict(worker_start_midpoint_phase_processing_wall_ms=distribution(times),
                approximate_monitor_phase_frequency=freq)
        result.append(dict(trial=name,size=c.read(d/'config.json')['size'],source_seal=ref['seal'],phases=phases))
    return dict(schema=1,rows=result,script_sha256=c.digest(Path(__file__)),performance_run=False,
        interpretation='Low-phase processing-wall medians exceed busy medians, but busy wall time includes quota stalls in its upper tail. This does not identify a CPU-cost cause. Existing one-second frequency samples are not attributed to the CPU running each job and cannot establish a frequency explanation.',
        limitations='Midpoint phase selection; approximate rounded-epoch monitor alignment with assumed wall-clock constancy; no per-job CPU, cycles/instructions, executed frequency or runtime activity attribution.')


if __name__=='__main__':
    out=ROOT/'analysis/runtime_io_capacity_state_details/20261007'
    if out.exists():raise ValueError('preserve existing review')
    value=review(c.PARENT/'generation-01');out.mkdir(parents=True);c.save(out/'report.json',value);c.seal(out)
    print(out/'report.json')
