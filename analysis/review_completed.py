"""Reproduce the completed-session audit and exploratory trial-level analysis.

Usage: venv/bin/python analysis/review_completed.py results/sessions/20260921-202841
Raw files are read only. Outputs go to SESSION/processed/review/.
The unit of replication is a trial, never an individual request.
The narrative is specific to the frozen 20260921-202841 dataset, not a general report template.
"""
import bisect
import hashlib
from importlib.metadata import version
import json
import math
import os
from pathlib import Path
import sys

os.environ.setdefault('MPLCONFIGDIR', '/tmp/quota-review-matplotlib')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats
import statsmodels.formula.api as smf
from statsmodels.stats.multitest import multipletests

PERIODS = [10000, 50000, 100000, 250000, 0]
LABELS = ['10 ms', '50 ms', '100 ms', '250 ms', 'Unlimited']
FACTORS = ['period_us', 'workers', 'load', 'pattern']
EXPECTED_RAW_DIGEST = 'a3b0a13fd81a75ad9c07b49e928dfbb0aeeb85e8822ef9800f76b53990a6a591'


def read(p):
    return json.loads(p.read_text())


def dump(p, x):
    p.write_text(json.dumps(x, indent=2, allow_nan=False) + '\n')


def main(session):
    if session.name != '20260921-202841':
        raise ValueError('This completed-study review is specific to session 20260921-202841.')
    root = session.parents[2]
    out = session / 'processed/review'
    out.mkdir(parents=True, exist_ok=True)
    matrix = read(session / 'matrix.json')
    baseline = read(session / 'environment.json')['baseline_c']['k10temp:Tctl']
    accepted = sorted(d['samples'][-1]['timestamp'] for p in session.glob('resume-settling-*.json')
                      if (d := read(p)).get('accepted'))
    issues, rows, manifest = [], [], {}
    expected_ids = {c['run_id'] for c in matrix}
    actual_ids = {p.parent.name for p in (session / 'raw').glob('*/result.json')}
    assert expected_ids == actual_ids and len(matrix) == 300
    for i, cfg in enumerate(matrix, 1):
        directory = session / 'raw' / cfg['run_id']
        r = read(directory / 'result.json')
        lg = read(directory / 'loadgen.json')
        mon = read(directory / 'monitor.json')
        limits = read(directory / 'limits.json')
        settle = read(directory / 'settling.json')
        for p in directory.iterdir():
            if p.is_file():
                manifest[str(p.relative_to(session))] = hashlib.sha256(p.read_bytes()).hexdigest()
        def check(condition, message):
            if not condition:
                issues.append({'run': i, 'run_id': cfg['run_id'], 'issue': message})
        check(all(r['config'][k] == v for k, v in cfg.items()), 'matrix/config mismatch')
        check(r['run_id'] == cfg['run_id'] and not r['quality_flags'], 'ID or quality flags')
        check(r['config']['duration_sec'] == 60 and r['config']['warmup_sec'] == 20, 'duration/warmup')
        check({k: v for k, v in lg.items() if k != 'requests'} == r['loadgen_metrics'], 'loadgen/report mismatch')
        req = lg['requests']
        ok = [q for q in req if q['StatusCode'] == 200 and not q['Error']]
        e2e = np.sort([q['EndToEndLatencyNs'] for q in ok])
        check(len(req) == lg['total_completed'] == lg['total_dispatched'], 'completed request count')
        check(len(ok) == lg['total_success'] == lg['end_to_end_latency_summary']['count'], 'success count')
        check(lg['total_scheduled'] == lg['total_dispatched'] + lg['client_dropped'], 'scheduled count')
        check(len(req) == lg['total_success'] + lg['total_503'] + lg['total_errors'], 'outcome accounting')
        check(sum(q['StatusCode'] == 503 and not q['Error'] for q in req) == lg['total_503'], 'raw 503 count')
        for pct in (50, 95, 99):
            value = float(e2e[math.ceil(pct / 100 * len(e2e)) - 1]) / 1e6
            check(abs(value - lg['end_to_end_latency_summary'][f'p{pct}_ms']) < 1e-9, f'p{pct} mismatch')
        check(lg['client_dropped'] == lg['missed_arrivals'] == 0, 'generator loss/late arrival')
        check(lg['dispatch_lag_summary']['p99_ms'] <= 2, 'generator p99 delay')
        check(len(mon) == r['monitor_samples'] and len(mon) >= 42, 'monitor coverage')
        expected_power = {k: v for k, v in r['power_before'].items() if k != 'desktop_profile'}
        check(r['power_before'] == r['power_after'], 'power change at boundaries')
        check(all(m['power_settings'] == expected_power for m in mon), 'power change during trial')
        check(settle['accepted'] and r['temperatures_before']['stable'], 'starting temperature not accepted')
        thermal = r['temperatures_before']['sensors']['k10temp:Tctl']
        check(abs(thermal['mean_c'] - baseline) <= 3 + 1e-9 and thermal['range_c'] <= 2
              and abs(thermal['slope_c_per_min']) <= 1, 'starting temperature out of policy')
        own = [v for k, v in limits.items() if 'docker-' in k]
        check(len(own) == 1, 'own cgroup missing')
        expected_max = f"{cfg['quota_us']} {cfg['period_us']}" if cfg['period_us'] else 'max 100000'
        check(own[0]['cpu.max'] == expected_max and own[0]['cpu.max.burst'] == '0'
              and own[0]['cpuset.cpus.effective'] == '2,4', 'own cgroup limits')
        check(all(v['cpu.max'].startswith('max ') for k, v in limits.items() if 'docker-' not in k), 'ancestor cap')
        delta = r['cgroup_metrics']['delta']
        check(all(delta[k] == r['cgroup_final'][k] - r['cgroup_initial'].get(k, 0) for k in delta), 'counter delta')
        temps = [m['temps_c']['k10temp:temp1_input'] for m in mon]
        row = dict(cfg, order=i, timestamp=r['timestamp_start'],
                   segment_raw=bisect.bisect_right(accepted, r['trial_timestamp_start']),
                   p99_ms=lg['end_to_end_latency_summary']['p99_ms'],
                   p95_ms=lg['end_to_end_latency_summary']['p95_ms'],
                   p50_ms=lg['end_to_end_latency_summary']['p50_ms'],
                   successful_rps=lg['successful_throughput_rps'], scheduled=lg['total_scheduled'],
                   success=lg['total_success'], errors=lg['total_errors'], rejected=lg['total_503'],
                   lag_p99_ms=lg['dispatch_lag_summary']['p99_ms'],
                   cpu_cores=r['cgroup_metrics']['cpu_usage_cores'],
                   throttle_fraction=r['cgroup_metrics']['throttling_fraction'] or 0,
                   nr_throttled=delta['nr_throttled'], start_temp_c=thermal['mean_c'],
                   mean_temp_c=float(np.mean(temps)), max_temp_c=max(temps),
                   monitor_samples=len(mon), drain_elapsed_s=lg['elapsed_including_drain_sec'],
                   host_cpu_pct=float(np.mean([m['cpu_util_pct']['cpu'] for m in mon])),
                   client_cpu_peak_pct=max(max(m['cpu_util_pct']['cpu0'], m['cpu_util_pct']['cpu1']) for m in mon),
                   power_variant=hashlib.sha256(json.dumps(r['power_before'], sort_keys=True).encode()).hexdigest()[:10])
        rows.append(row)
    # The accompanying narrative describes this frozen dataset. Refuse silent reuse
    # after raw-data edits; a changed dataset needs a new scientific interpretation.
    if hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest() != EXPECTED_RAW_DIGEST:
        raise ValueError('Raw dataset changed; review the narrative before running this study-specific analysis.')
    df = pd.DataFrame(rows)
    df['segment'] = pd.factorize(df.segment_raw, sort=True)[0] + 1
    df['failure_fraction'] = (df.errors + df.rejected) / df.scheduled
    df['log_p99'] = np.log(df.p99_ms)
    df['cell'] = df[FACTORS].astype(str).agg('_'.join, axis=1)
    assert df.groupby(FACTORS).size().eq(5).all() and df.cell.nunique() == 60
    # Cross-check the initial pipeline output, without modifying it.
    initial = pd.read_csv(session / 'processed/summary.csv').set_index('run_id')
    for metric in ('p99_ms', 'p95_ms', 'p50_ms', 'successful_rps'):
        assert np.allclose(initial.loc[df.run_id, metric], df[metric], atol=1e-8, rtol=0)
    df.to_csv(out / 'trial_review.csv', index=False)
    grouped = df.groupby(FACTORS, sort=True)
    cell = grouped.agg(n=('p99_ms', 'size'), mean_p99_ms=('p99_ms', 'mean'),
                       median_p99_ms=('p99_ms', 'median'), min_p99_ms=('p99_ms', 'min'),
                       max_p99_ms=('p99_ms', 'max'), sd_p99_ms=('p99_ms', 'std'),
                       mean_p50_ms=('p50_ms', 'mean'), mean_throttle_fraction=('throttle_fraction', 'mean'),
                       mean_cpu_cores=('cpu_cores', 'mean'), mean_successful_rps=('successful_rps', 'mean'),
                       total_scheduled=('scheduled', 'sum'), total_errors=('errors', 'sum'),
                       total_rejected=('rejected', 'sum')).reset_index()
    cell['cv_p99'] = cell.sd_p99_ms / cell.mean_p99_ms
    cell.to_csv(out / 'condition_summary.csv', index=False)
    # Exploratory contrasts on log(run p99). Independent repeats, not paired by r1...r5.
    contrasts = []
    def contrast(name, a, b, labels):
        x, y = np.log(a.p99_ms.to_numpy()), np.log(b.p99_ms.to_numpy())
        vx, vy = np.var(x, ddof=1) / len(x), np.var(y, ddof=1) / len(y)
        se = np.sqrt(vx + vy)
        dof = (vx + vy)**2 / (vx**2 / (len(x)-1) + vy**2 / (len(y)-1))
        diff = np.mean(x) - np.mean(y)
        radius = stats.t.ppf(.975, dof) * se
        contrasts.append(dict(comparison=name, **labels, ratio=float(np.exp(diff)),
                              ci_low=float(np.exp(diff-radius)), ci_high=float(np.exp(diff+radius)),
                              p=float(stats.ttest_ind(x, y, equal_var=False).pvalue)))
    for (w, load, pattern), g in df.groupby(['workers', 'load', 'pattern']):
        contrast('250ms / 10ms', g[g.period_us==250000], g[g.period_us==10000],
                 dict(workers=w, load=load, pattern=pattern))
    for (period, load, pattern), g in df.groupby(['period_us', 'load', 'pattern']):
        contrast('4 workers / 1 worker', g[g.workers==4], g[g.workers==1],
                 dict(period_us=period, load=load, pattern=pattern))
    for (period, w, load), g in df.groupby(['period_us', 'workers', 'load']):
        contrast('bursty / steady', g[g.pattern=='bursty'], g[g.pattern=='steady'],
                 dict(period_us=period, workers=w, load=load))
    ct = pd.DataFrame(contrasts)
    ct['p_holm_62'] = multipletests(ct.p, method='holm')[1]
    ct.to_csv(out / 'exploratory_contrasts.csv', index=False)
    # Segment offsets after conditioning on every treatment cell. Under-load temperature
    # is deliberately not adjusted away: it can be an outcome of the treatment.
    base = smf.ols('log_p99 ~ C(cell)', data=df).fit(cov_type='HC3')
    adjust = smf.ols('log_p99 ~ C(cell) + C(segment) + start_temp_c', data=df).fit(cov_type='HC3')
    timefit = smf.ols('log_p99 ~ C(cell) + order', data=df).fit(cov_type='HC3')
    sensitivity = {'base_r_squared':base.rsquared, 'adjusted_r_squared':adjust.rsquared,
                   'adjusted_condition_number':adjust.condition_number,
                   'residual_lag1_correlation':float(pd.Series(base.resid).autocorr()),
                   'order_multiplier_per_100_trials':float(np.exp(timefit.params['order']*100)),
                   'order_p':float(timefit.pvalues['order']), 'coefficients':{}}
    for name in adjust.params.index:
        if 'segment' in name or name == 'start_temp_c':
            ci = adjust.conf_int().loc[name]
            sensitivity['coefficients'][name] = dict(ratio=float(np.exp(adjust.params[name])),
                                                     low=float(np.exp(ci[0])), high=float(np.exp(ci[1])),
                                                     p=float(adjust.pvalues[name]))
    # Compare condition means standardized to the same observed segment/temp distribution.
    means = []
    for _, row in cell.iterrows():
        template = df[['segment','start_temp_c']].copy()
        treatment = df[(df.period_us==row.period_us)&(df.workers==row.workers)&
                       (df.load==row.load)&(df.pattern==row.pattern)]
        template['cell'] = treatment.cell.iloc[0]
        means.append(dict(**{k:row[k] for k in FACTORS},
                          raw_geomean_p99_ms=float(np.exp(treatment.log_p99.mean())),
                          standardized_geomean_p99_ms=float(np.exp(adjust.predict(template).mean()))))
    pd.DataFrame(means).to_csv(out / 'segment_sensitivity.csv', index=False)
    segments = df.groupby('segment').agg(first_order=('order','min'),last_order=('order','max'),
                trials=('order','size'), start=('timestamp','min'), end=('timestamp','max'),
                min_start_c=('start_temp_c','min'),max_start_c=('start_temp_c','max'))
    segments.to_csv(out / 'collection_segments.csv')
    dump(out / 'sensitivity.json', sensitivity)
    (out / 'sensitivity_models.txt').write_text(str(adjust.summary())+'\n\n'+str(timefit.summary())+'\n')
    audit = dict(session=session.name, trials=len(df), conditions=len(cell), repeats_per_condition=5,
                 issues=issues, totals={k:int(df[k].sum()) for k in ['scheduled','success','errors','rejected']},
                 p99_range_ms=[float(df.p99_ms.min()),float(df.p99_ms.max())],
                 max_dispatch_lag_p99_ms=float(df.lag_p99_ms.max()),
                 monitor_samples_range=[int(df.monitor_samples.min()),int(df.monitor_samples.max())],
                 start_temperature_range_c=[float(df.start_temp_c.min()),float(df.start_temp_c.max())],
                 max_observed_temperature_c=float(df.max_temp_c.max()),
                 unlimited_throttle_events=int(df.loc[df.period_us==0,'nr_throttled'].sum()),
                 collection_segments=len(segments), power_variants=int(df.power_variant.nunique()),
                 max_cell_cv=float(cell.cv_p99.max()), cells_cv_over_10pct=int((cell.cv_p99>.1).sum()),
                 recorded_resume_attempts=len(list(session.glob('resume-settling-*.json'))),
                 archived_trial_attempts=len(list((session/'interrupted-trials').glob('*/failure.json'))))
    original_hashes = read(session / 'metadata.json')['source_sha256']
    audit['original_source_mismatches'] = [name for name, digest in original_hashes.items()
        if not (root/name).is_file() or hashlib.sha256((root/name).read_bytes()).hexdigest() != digest]
    audit['runtime_versions'] = {'python':sys.version.split()[0],
        **{name:version(name) for name in ['numpy','pandas','scipy','statsmodels','matplotlib']}}
    audit['raw_manifest_digest'] = EXPECTED_RAW_DIGEST
    audit['percentile_definition'] = 'Nearest-rank p99 of successful requests; run is unit of replication'
    dump(out / 'audit.json', audit)
    if issues or audit['original_source_mismatches']:
        raise ValueError('Audit failed: inspect audit.json before interpreting this dataset.')
    dump(out / 'raw_sha256.json', manifest)
    plt.rcParams.update({'font.size':10, 'axes.spines.top':False, 'axes.spines.right':False})
    for load in ['moderate','high']:
        fig, axes = plt.subplots(3,2,figsize=(11,9),sharex=True,sharey=True)
        for wi,w in enumerate([1,2,4]):
            for pi,pattern in enumerate(['steady','bursty']):
                ax=axes[wi,pi]
                g=df[(df.load==load)&(df.workers==w)&(df.pattern==pattern)]
                for j,period in enumerate(PERIODS):
                    vals=g[g.period_us==period].p99_ms.to_numpy()
                    ax.scatter(j+np.linspace(-.12,.12,5),vals,color='#246c91',s=25,alpha=.7)
                    ax.plot([j-.23,j+.23],[np.median(vals)]*2,color='#b34220',lw=2)
                ax.set_yscale('log'); ax.grid(axis='y',alpha=.2)
                ax.set_title(f'{w} worker'+('s' if w>1 else '')+f' · {pattern}')
                ax.set_xticks(range(5),LABELS,rotation=15)
                if pi==0: ax.set_ylabel('Successful-request p99 (ms)')
        fig.suptitle(f'{load.capitalize()} load: five trials per condition\nDots: individual run p99; red bar: median across runs',fontsize=13)
        fig.tight_layout(rect=(0,0,1,.94))
        fig.savefig(out/f'p99_{load}.png',dpi=180); fig.savefig(out/f'p99_{load}.pdf'); plt.close(fig)
    fig, axes = plt.subplots(3,2,figsize=(11,8),sharex=True,sharey=True)
    for wi,w in enumerate([1,2,4]):
        for pi,pattern in enumerate(['steady','bursty']):
            ax=axes[wi,pi]
            g=df[(df.load=='high')&(df.workers==w)&(df.pattern==pattern)]
            for j,period in enumerate(PERIODS):
                vals=100*g[g.period_us==period].failure_fraction.to_numpy()
                ax.scatter(j+np.linspace(-.12,.12,5),vals,color='#b34220',s=25,alpha=.7)
                ax.plot([j-.23,j+.23],[np.mean(vals)]*2,color='#333333',lw=2)
            ax.set_title(f'{w} worker'+('s' if w>1 else '')+f' · {pattern}')
            ax.set_xticks(range(5),LABELS,rotation=15); ax.grid(axis='y',alpha=.2)
            if pi==0: ax.set_ylabel('Failed scheduled requests (%)')
    fig.suptitle('High load: queue rejections and request errors\nDots: individual trials; black bar: mean across five trials',fontsize=13)
    fig.tight_layout(rect=(0,0,1,.94)); fig.savefig(out/'failures_high.png',dpi=180)
    fig.savefig(out/'failures_high.pdf'); plt.close(fig)
    fig,axes=plt.subplots(2,1,figsize=(11,7),sharex=True)
    axes[0].scatter(df.order,df.start_temp_c,s=10,label='Pretrial mean')
    axes[0].scatter(df.order,df.mean_temp_c,s=10,label='Under-load mean',alpha=.5)
    axes[0].axhspan(baseline-3,baseline+3,color='green',alpha=.1,label='Permitted starting band')
    axes[0].set_ylabel('Tctl (°C)'); axes[0].legend(ncol=3,fontsize=9)
    axes[1].scatter(df.order,base.resid,s=12,color='#246c91'); axes[1].axhline(0,color='gray',lw=1)
    axes[1].set_ylabel('Log p99 residual\nafter condition means'); axes[1].set_xlabel('Randomized matrix order')
    for x in segments.first_order.iloc[1:]:
        for ax in axes: ax.axvline(x-.5,color='gray',linestyle=':',lw=1)
    fig.suptitle('Temperature and collection interruptions\nDotted lines: resumed collection segments; no trials excluded')
    fig.tight_layout(); fig.savefig(out/'collection_diagnostics.png',dpi=180); plt.close(fig)
    def table(headers, data):
        return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+
                         ['| '+' | '.join(map(str,row))+' |' for row in data])
    def latency_table(load,pattern):
        subset=cell[(cell.load==load)&(cell.pattern==pattern)].set_index(['period_us','workers'])
        return table(['Period','1 worker','2 workers','4 workers'],
            [[label]+[f"{subset.loc[(period,w),'mean_p99_ms']:.2f}" for w in [1,2,4]]
             for period,label in zip(PERIODS,LABELS)])
    failure_data=[]
    for period,label in zip(PERIODS,LABELS):
        vals=[]
        for w in [1,2,4]:
            g=df[(df.period_us==period)&(df.workers==w)&(df.load=='high')&(df.pattern=='bursty')]
            vals.append(f'{100*(g.errors.sum()+g.rejected.sum())/g.scheduled.sum():.2f}%')
        failure_data.append([label]+vals)
    unstable=cell[cell.cv_p99>.1]
    report = f'''# Completed experiment: interpretation and audit

Session `{session.name}`. All 300 trials and all 60 conditions are included, with five
repetitions per condition. The 10% CV threshold below is a descriptive variability
screen added during analysis, not an exclusion rule or a predeclared hypothesis test.

## Main interpretation

The effect of quota period depends on offered load, traffic pattern, and worker count.
Moderate traffic usually has p99 near 6–7 ms. High steady traffic is sensitive to the
10 ms period. Under high bursty traffic, every capped condition has much higher tails
than its uncapped comparison. The 100 ms period with four workers is especially poor.
The data do not support a universal claim that a longer period always improves latency.

## Measurement audit

- Matrix/configuration and raw request accounting checks: {len(issues)} discrepancies.
- Scheduled requests: {audit['totals']['scheduled']:,}; successful: {audit['totals']['success']:,}.
- HTTP 503 queue rejections: {audit['totals']['rejected']:,}; request errors: {audit['totals']['errors']}.
- Successful-request p50, p95 and p99 were recalculated from every trial's raw requests
  using the generator's nearest-rank rule and checked against both saved summaries.
- No generator missed arrivals or client drops; worst run dispatch-lag p99:
  {audit['max_dispatch_lag_p99_ms']:.3f} ms. Monitor coverage: 58–60 samples per run.
- All accepted pretrial means were within the original temperature band; observed
  range: {df.start_temp_c.min():.2f}–{df.start_temp_c.max():.2f} C.
- Cgroup limits, CPU affinity, uncapped recorded ancestors, power consistency within
  each trial, and counter deltas were checked. Unlimited trials have zero own throttling.
- Original experiment source/binary hash mismatches: {len(audit['original_source_mismatches'])}.

These checks establish internal consistency, not absence of all measurement bias.
The latency summaries cover successful requests only. Failures remain separate outcomes;
the study does not claim a p99 for all offered requests including timeouts or rejections.

## High steady traffic

Arithmetic mean of five run p99 values, in milliseconds; this is not a pooled request p99.

{latency_table('high','steady')}

The 10 ms two-worker and four-worker means are influenced by rare severe runs. Their
median run p99 values are 127.96 and 215.01 ms, while maxima are 1296.25 and 1423.29 ms.
Those two severe runs also contain all 810 steady-traffic queue rejections. Keep those
observations; do not remove them as inconvenient outliers.

## High bursty traffic

Arithmetic mean of five run p99 values (ms):

{latency_table('high','bursty')}

Failed requests as a percentage of all scheduled requests, summed over five trials:

{table(['Period','1 worker','2 workers','4 workers'],failure_data)}

The 250 ms period improves high-burst tails over 10 ms most clearly for one and two
workers. With four workers, those periods overlap in their repeated-run distributions.
At 100 ms, moving from one to four workers raises mean run p99 from 828.76 to 4302.71 ms.
This comparison is an observed interaction. Scheduler runtime allocation, queue dynamics,
and application/runtime scheduling are possible mechanisms; this experiment alone does
not isolate their individual contributions.

All 17 recorded request errors are HTTP client timeouts while awaiting headers, in high
bursty 100 ms conditions with two or four workers. The client timeout is five seconds.
High burst peaks are 169.815 requests/s, above the 133.19 requests/s calibration reference.
Thus transient overload is deliberately possible even though the mean rate is 113.21.
That reference capacity was measured for one worker at a 100 ms period, not every condition.

## Moderate traffic and repeatability

Moderate steady means range from 6.57 to 6.63 ms. Moderate bursty means are approximately
6.50–6.64 ms except 10 ms with two workers (18.37 ms; individual runs 6.54–40.92 ms).
No moderate trial recorded a rejection or request error. Six conditions have a run-p99
CV above 10%; all are listed below. Small differences of a few hundredths of a millisecond
should not be promoted to general operational recommendations.

{table(['Period (us)','Workers','Load','Pattern','Min p99','Mean p99','Max p99','CV'],
       [[int(r.period_us),int(r.workers),r.load,r.pattern,f'{r.min_p99_ms:.2f}',f'{r.mean_p99_ms:.2f}',
         f'{r.max_p99_ms:.2f}',f'{100*r.cv_p99:.1f}%'] for r in unstable.itertuples()])}

## Exploratory uncertainty and interruption sensitivity

`exploratory_contrasts.csv` reports geometric-mean p99 ratios for 62 comparisons:
12 period contrasts (250/10 ms), 20 worker contrasts (4/1), and 30 burst/steady contrasts.
Welch t intervals and tests use log(run p99), with five independent repetitions per side.
Repetition labels are not treated as matched pairs. P values are adjusted together with
Holm's method across all 62 comparisons. The 95% intervals are unadjusted, pointwise
intervals. These comparisons were selected after data collection and are exploratory.
With five trials, distributional assumptions are weakly checkable; retain the raw dots.

For high bursty traffic, 250/10 ms ratios are 0.446 (95% interval 0.425–0.467) with one
worker and 0.553 (0.534–0.572) with two workers. Their Holm-adjusted p values are below
0.00001. With four workers the ratio is 0.912 (0.704–1.180), which does not establish
a reliable advantage for either period.

There are five collection segments: trials 1–93, 94–95, 96–99, 100–177, and 178–300.
The saved USB-C inventory amendment begins at trial 94. A post hoc model of log p99
using a separate mean for every condition, plus segment and starting temperature,
changes standardized condition geometric means by -1.59% to +2.90%. The last-segment
multiplier relative to the first is 0.993 (95% interval 0.919–1.072).
A separate model's order multiplier per 100 trials is 1.013 (p=0.523).
These checks find no clear overall shift, but do not establish equivalence across
reboots or rule out condition-specific confounding. Segments with two and four trials
provide little independent information. Under-load temperatures are shown as outcomes,
not adjusted away as if they necessarily preceded the treatment.

The original automatic regression is an exploratory saturated factor model. Its high
R-squared does not establish causality or generalization; its individual coefficient
p values are not the main evidence used here. Throttled-period fraction is a ratio of
counter increments, not the fraction of requests throttled or wall-clock time stalled.

## Reproduction and files

From the repository root, run:

```bash
venv/bin/python analysis/review_completed.py results/sessions/{session.name}
```

This script only reads the session inputs and writes `processed/review/`. It does not
alter the experiment runner or its preserved provenance. `raw_sha256.json` records raw
trial file hashes; `audit.json` records checks; `condition_summary.csv` gives all 60 cells;
`trial_review.csv` retains trial order, segment and environmental summaries. PNG and PDF
latency and failure figures show all repetitions. `collection_diagnostics.png` shows
starting and under-load temperature plus residuals in trial order.

## Next research step

Use these completed-session findings to replace the exploratory draft's legacy rates,
tables and universal recommendations. Before submission, complete related work and
independently replicate the variable or extreme conditions (10 ms high steady, 10 ms
moderate bursty with two workers, and 100/250 ms high bursty with multiple workers).
Any new protocol or baseline belongs in a separate session with its own provenance.
'''
    (out/'interpretation.md').write_text(report)
    print(json.dumps(audit,indent=2))
    print('\nMean run p99 (ms):\n',cell.pivot(index=['load','pattern','workers'],columns='period_us',values='mean_p99_ms').round(2).to_string())


if __name__ == '__main__':
    main(Path(sys.argv[1]).resolve())
