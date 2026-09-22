#!/usr/bin/env python3
"""Analyse matrix runs only, preserving all experimental factors in plots."""
import json
import sys
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns


def main(session):
    rows = []
    for path in sorted((session / 'raw').glob('*/result.json')):
        d = json.loads(path.read_text())
        c, lg, cg = d['config'], d['loadgen_metrics'], d['cgroup_metrics']
        rows.append(dict(c, p99_ms=lg['end_to_end_latency_summary']['p99_ms'],
                         p50_ms=lg['end_to_end_latency_summary']['p50_ms'],
                         p95_ms=lg['end_to_end_latency_summary']['p95_ms'],
                         cpu_usage_cores=cg['cpu_usage_cores'], throttling_fraction=cg['throttling_fraction'],
                         successful_rps=lg['successful_throughput_rps'],
                         failed=lg['total_errors'] + lg['total_503'],
                         flags=';'.join(d['quality_flags'])))
    if not rows:
        raise SystemExit('No matrix results. Calibration and pilot are intentionally excluded.')
    out = session / 'processed'
    out.mkdir(exist_ok=True)
    df = pd.DataFrame(rows)
    df.to_csv(out / 'summary.csv', index=False)
    df['period'] = df.period_us.map(lambda p: 'Unlimited' if not p else f'{p // 1000}ms')
    sns.set_theme(style='whitegrid')
    for load, subset in df.groupby('load'):
        grid = sns.catplot(data=subset, x='period', y='p99_ms', col='pattern', row='workers',
                           kind='point', order=['10ms', '50ms', '100ms', '250ms', 'Unlimited'],
                           errorbar=('ci', 95), seed=42, height=2.5, aspect=1.5)
        grid.set_axis_labels('CPU quota period', 'Run p99 latency (ms)')
        grid.figure.savefig(out / f'latency_{load}.png', dpi=200, bbox_inches='tight')
        plt.close(grid.figure)
    # No fitting incomplete designs or treating Unlimited as a numeric period.
    expected = json.loads((session / 'matrix.json').read_text())
    complete = {r['run_id'] for r in expected} == set(df.run_id) and not df['flags'].str.len().any()
    if complete:
        import numpy as np
        import statsmodels.formula.api as smf
        limited = df[df.period_us > 0].copy()
        limited['log_p99'] = np.log(limited.p99_ms)
        fit = smf.ols('log_p99 ~ C(period_us)*C(workers)*C(pattern)*C(load)', data=limited).fit(cov_type='HC3')
        (out / 'regression.txt').write_text(str(fit.summary()) + '\nExploratory factor model; check residuals and multiplicity before inference.\n')
    print(f'{len(df)}/300 matrix records. Complete unflagged design: {complete}. Output: {out}')


if __name__ == '__main__':
    main(Path(sys.argv[1]).resolve())
