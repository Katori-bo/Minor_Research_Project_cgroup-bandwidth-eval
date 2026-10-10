#!/usr/bin/env python3
"""Exploratory replay of saved V23 counters; never collects workload data."""
import bisect
import datetime
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'diagnostic'))
import v23_common as c
from kernel_bridge_analysis import clock_join


def review(session):
    c.verify_seal(session/'predictions')
    calibration = c.read(session/'predictions/calibration.json')
    refs = c.read(session/'predictions/manifest.json')['calibration_refs']
    rows = []
    for name, ref in refs.items():
        d = c.resolve(session, ref['path']); c.verify_seal(d)
        if c.digest(d/'seal.json') != ref['seal']:
            raise ValueError('calibration reference changed')
        cfg = c.read(d/'config.json'); derived = c.read(d/'derived.json')
        server = c.read(d/'server_metrics.json'); mapping = derived['clocks']
        joined = clock_join(c.read(d/'host_server_anchors.json'), mapping, server['clock_generation'])
        start = c.read(d/'started.json'); monitor = c.read(d/'monitor.json')
        # Historical monitor lacks timestamps bracketing the actual cpu.stat read.
        # This alignment/interpolation is an exploratory approximation only.
        epoch_offset = start['wall_time'] - start['monotonic_ns']/1e9
        host_client_mid = (joined['kernel_minus_client_lower_ns'] + joined['kernel_minus_client_upper_ns'])/2
        xs = [(r['timestamp']-epoch_offset)*1e9-host_client_mid-mapping['client_test_start_ns'] for r in monitor]
        ys = [r['cgroup_cpu_stat']['usage_usec'] for r in monitor]
        if any(b<=a for a,b in zip(xs,xs[1:])) or any(b<a for a,b in zip(ys,ys[1:])):
            raise ValueError('historical counter/time sequence is invalid')
        origin = mapping['client_test_start_ns']+(mapping['server_minus_client_lower_ns']+mapping['server_minus_client_upper_ns'])/2
        ends = sorted((j['completion_ns']-origin)/1e9 for j in server['events'])
        def interp(sec):
            ns=sec*1e9; i=bisect.bisect_right(xs,ns)
            if not 0<i<len(xs):raise ValueError('window outside retained monitor coverage')
            return ys[i-1]+(ys[i]-ys[i-1])*(ns-xs[i-1])/(xs[i]-xs[i-1])
        phases={}
        for label,(a,b) in [('busy',(6.5,9.5)),('low',(1,4))]:
            usage=sum(interp(b+10*k)-interp(a+10*k) for k in range(6))
            count=sum(bisect.bisect_left(ends,b+10*k)-bisect.bisect_left(ends,a+10*k) for k in range(6))
            phases[label]=dict(interpolated_usage_usec=usage,midpoint_completions=count,
                illustrative_cpu_usec_per_completion=usage/count,illustrative_delivered_cpu_fraction=usage/18e6)
        whole=derived['summary']['cpu_usec_per_completed_work']
        mu=calibration['sizes'][cfg['size']]['mu_busy']
        rows.append(dict(trial=name,size=cfg['size'],source_seal=ref['seal'],whole_cohort_cpu_usec_per_job=whole,
            incompatible_combination_implied_cpu_fraction=mu*whole/1e6,phases=phases,
            illustrative_whole_over_busy=whole/phases['busy']['illustrative_cpu_usec_per_completion']))
    return dict(schema=1,at=datetime.datetime.now(datetime.timezone.utc).isoformat(),rows=rows,
        prediction_seal=c.digest(session/'predictions/seal.json'),script_sha256=c.digest(Path(__file__)),
        performance_run=False,causal_mechanism_established=False,
        warning='Exploratory linear interpolation of rounded epoch sample labels. Actual historical counter-read timestamps are unobserved; wall-clock constancy is assumed, not established. These phase numbers are not bounded measurements, confirmatory evidence, forecasts, or per-job CPU attribution.',
        interpretation='Retained counters suggest busy CPU is approximately 0.5 and busy-window CPU/completion is lower than whole-cohort CPU/job. V24 must test this with precise monotonic brackets and observer controls.')


if __name__=='__main__':
    out=ROOT/'analysis/runtime_io_capacity_mismatch_review/20261007'
    if out.exists():raise ValueError('preserve existing review; use a new directory for revisions')
    value=review(c.PARENT/'generation-01');out.mkdir(parents=True)
    c.save(out/'report.json',value);c.seal(out)
    print(out/'report.json')
