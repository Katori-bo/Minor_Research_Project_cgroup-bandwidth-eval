"""Build the empirical manuscript from retained V5 text and sealed results.

Editorial/figure generation only: no collection, new fit, or threshold changes.
Run with Python -B. Verification is in verify_empirical_paper.py.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'analysis/runtime_io_paper_finalization/20261008'
PAPER = ROOT / 'paper'
METHODS = [('whole', 'Whole-run'), ('idle_corrected', 'Idle-corrected'),
           ('busy', 'Busy'), ('regression', 'Linear'), ('quadratic', 'Quadratic')]
COLORS = ['#8c564b', '#9467bd', '#0072b2', '#777777', '#d55e00']
REFS = [
 ('linux', 'Linux Kernel Contributors. Control Group v2: CPU controller. Linux kernel documentation. Accessed 8 October 2026.', 'https://docs.kernel.org/admin-guide/cgroup-v2.html'),
 ('kumar', 'D. Kumar, L. Zhang and A. Tantawi. Enhanced Inferencing: Estimation of a Workload Dependent Performance Model. VALUETOOLS, 2009. DOI: 10.4108/ICST.VALUETOOLS2009.7799.', 'https://eudl.eu/pdf/10.4108/ICST.VALUETOOLS2009.7799'),
 ('zhang', 'Z. Zhang, S. Li and J. Zhou. Estimate Load-dependent Service Demand for Modern CPU. Information Technology Journal 12(4), 632–639, 2013. DOI: 10.3923/itj.2013.632.639.', 'https://scialert.net/fulltext/amp.php?doi=itj.2013.632.639'),
 ('mi', 'N. Mi, G. Casale, L. Cherkasova and E. Smirni. Sizing multi-tier systems with temporal dependence: benchmarks and analytic models. Journal of Internet Services and Applications 1, 117–134, 2010. DOI: 10.1007/s13174-010-0012-9.', 'https://link.springer.com/article/10.1007/s13174-010-0012-9'),
 ('casale', 'G. Casale, A. Kalbasi, D. Krishnamurthy and J. Rolia. Automatic Stress Testing of Multi-Tier Systems by Dynamic Bottleneck Switch Generation. Middleware, 2009.', 'https://dl.ifip.org/db/conf/middleware/middleware2009/CasaleKKR09.pdf'),
 ('cucinotta', 'T. Cucinotta, L. Abeni, M. Marinoni, R. Mancini and C. Vitucci. Strong Temporal Isolation Among Containers in OpenStack for NFV Services. IEEE Transactions on Cloud Computing 11(1), 763–778, 2023. DOI: 10.1109/TCC.2021.3116183.', 'https://retis.santannapisa.it/people/nino/publication/TCC23.pdf'),
]


def read(path):
    return json.loads((ROOT / path).read_text())


def figure_data():
    review = read('analysis/runtime_io_v28_result_review/20261008/report.json')
    raw_path = ROOT / 'analysis/runtime_io_v28/generation-01/analysis' / Path(review['original_report']).parent.name / 'report.json'
    original = json.loads(raw_path.read_text())
    rows = original['trial_accounting']
    points = [dict(trial=r['trial'], throughput_rps=r['throughput_rps'],
                   utilization=r['utilization']) for r in rows if r['role'] in ('idle', 'steady')]
    trials = []
    by_method = {k: {r['trial']: r for r in original['result']['methods'][k]['errors']} for k, _ in METHODS}
    for r in original['result']['methods']['busy']['errors']:
        trials.append(dict(trial=r['trial'], block=r['block'], observed_miss_pct=r['observed_miss_pct'],
            forecasts={k: by_method[k][r['trial']]['predicted_miss_pct'] for k, _ in METHODS}))
    return dict(schema=1, source_report=str(raw_path.relative_to(ROOT)),
                source_report_sha256=hashlib.sha256(raw_path.read_bytes()).hexdigest(),
                calibration_points=points, calibration_models=original['calibration']['methods'],
                validation_trials=trials, summary=review['methods'], advantages=review['advantages'])


def plots(data, directory=None):
    os.environ.setdefault('MPLCONFIGDIR', '/tmp/cpu-quota-paper-matplotlib')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    plt.rcParams.update({'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False,
                         'svg.fonttype': 'none'})
    figures = directory if directory is not None else OUT / 'figures'
    figures.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(7.2, 4.6), layout='constrained')
    ax.fill_between([0, 40], [-3, 37], [3, 43], color='#dddddd', alpha=.55)
    ax.plot([0, 40], [0, 40], color='black', lw=.9, linestyle='--')
    markers = ['s', 'x', 'o', '^', 'D']
    for (key, label), color, marker in zip(METHODS, COLORS, markers):
        ax.scatter([r['observed_miss_pct'] for r in data['validation_trials']],
                   [r['forecasts'][key] for r in data['validation_trials']],
                   label=label, c=color, marker=marker, s=36, alpha=.8,
                   linewidths=1, zorder=3)
    ax.set(xlim=(-1, 40), ylim=(-1, 65), xlabel='Observed deadline misses (%)',
           ylabel='Frozen forecast deadline misses (%)')
    ax.grid(alpha=.2); ax.legend(loc='upper left', frameon=True, ncol=2)
    for ext in ('png', 'svg'): fig.savefig(figures / ('deadline_forecasts.' + ext), dpi=180)
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(7.2, 4.6), layout='constrained')
    pts = data['calibration_points']; maximum = max(p['throughput_rps'] for p in pts)
    ax.scatter([p['throughput_rps'] for p in pts], [p['utilization'] for p in pts],
               s=32, color='black', label='Idle/steady observations', zorder=4)
    for key, color, label in [('regression', COLORS[3], 'Linear'), ('quadratic', COLORS[4], 'Quadratic')]:
        m = data['calibration_models'][key]
        for start, end, style in [(0, maximum, '-'), (maximum, 160, '--')]:
            xs = [start + (end-start)*i/100 for i in range(101)]
            ys = [m['intercept'] + m['demand_sec']*x + m['quadratic_sec2']*x*x for x in xs]
            ax.plot(xs, ys, style, color=color, lw=1.8, label=label if start == 0 else None)
        ax.scatter([m['capacity_rps']], [.5], c=color, marker='D', s=35)
    ax.axhline(.5, color='black', lw=.8, label='Configured allowance')
    ax.axvline(data['summary']['busy']['capacity_rps'], color=COLORS[2], linestyle=':',
               label='Separate busy-capacity estimate')
    ax.set(xlim=(-1, 162), ylim=(-.005, .65), xlabel='Completion throughput (jobs/s)',
           ylabel='CPU consumption (CPU-seconds / wall-second)')
    ax.grid(alpha=.2); ax.legend(loc='upper left', fontsize=8.5, frameon=True)
    for ext in ('png', 'svg'): fig.savefig(figures / ('calibration_curves.' + ext), dpi=180)
    plt.close(fig)


def manuscript():
    source = (ROOT / 'docs/runtime_io_short_working_draft_v5.md').read_text()
    begin = source.index('## Abstract')
    text = source[:source.index('\n\nVersion 5')] + '\n\n' + source[begin:]
    text = text.replace('(runtime_io_paper_supporting_material_20261008.md)', '(capacity_calibration_supporting_material.md)')
    text = re.sub(r'\]\((runtime_io_[^)]+)\)', r'](../docs/\1)', text)
    text = text.replace('CPU allowance is 50 ms per 100 ms with\nzero burst credit.',
        'CPU allowance is 50 ms per 100 ms with\nzero burst credit (`cpu.max=50000 100000`, `cpu.max.burst=0`). The Linux\nCPU controller defines a bandwidth ceiling [1]. The recorded service uses\nstock Go 1.26.1 on Linux 7.2.8-arch1-2; the host records `amd-pstate-epp`\nwith the `powersave` governor and `balance_performance` preference. Frequency\nis not fixed, and these settings do not isolate a frequency-related cause.')
    text = text.replace('Means use the declared independent calibration trials.',
        'Means use the declared independent calibration trials. CPU/job is computed\nseparately per mixed run before averaging; the estimator is not a pooled\nCPU/count ratio. Warm-up CPU is excluded. Each slot has 20 s warm-up at its\nlow rate, then full drain and a metrics reset before measurement. Idle and\nsteady measurement lasts 30 s. The four mixed calibration runs last 60 s:\nfour 15 s cycles with 10 s at 15 or 30 jobs/s and 5 s at 169.8 jobs/s.\nWhole-run CPU and wall time include measurement startup, terminal control\nand final drain. Mixed busy windows are [11.5,14.5) s plus 15 s per cycle.')
    text = text.replace('declared monotonicity checks. Quadratic fitting',
        'declared monotonicity checks. The capacity root must not exceed twice the\nmaximum measured calibration throughput. The linear fit has intercept\n0.0158658 CPU and slope 0.00384378 CPU-seconds/job. The selected quadratic\nfit is `U(X)=0.005276096 X - 0.000012853378 X²`, with CPU/wall-second units.\nIts root is 1.269 times the maximum measured throughput of 117.029 jobs/s;\nthe result involves extrapolation. Quadratic fitting')
    text = text.replace('The calibration budgets differ:',
        '![Calibration observations and retained fits](../analysis/runtime_io_paper_finalization/20261008/figures/calibration_curves.png)\n\n**Figure 1.** Twelve independent idle/steady observations and the retained\nlinear and quadratic fits. Dashed portions extend beyond the measured\nthroughput range. Diamonds mark roots at 0.5 CPU. The vertical line is the\nseparate mixed-run busy estimate; it is not a fitting constraint. No uncertainty\nband is inferred from this descriptive plot.\n\nThe calibration budgets differ:')
    text = text.replace('validation outcomes never fit or select a method.',
        'validation outcomes never fit or select a method. Warm-up and full-drain\nrules also apply to validation. Busy validation windows are [4.8,5.8) s\nplus 6 s per cycle, or [10,11.8) s plus 12 s per cycle; eligibility requires\na positive waiting queue throughout the clock-expanded interval. Validation\nchanges both the mixed calibration cycle length and its high offered rate.')
    text = text.replace('Here MAE is mean absolute error',
        '![Frozen forecasts and observed outcomes](../analysis/runtime_io_paper_finalization/20261008/figures/deadline_forecasts.png)\n\n**Figure 2.** Frozen forecasts against all-offer outcomes in all sixteen\nvalidation trials. The diagonal denotes exact agreement; the gray band spans\n±3 percentage points, the declared deadline-error tolerance. Repeated points\noverlap, including eight zero-miss trials. The band is a tolerance, not a\nconfidence interval. Idle-corrected forecasts nearly overlap whole-run forecasts.\n\nHere MAE is mean absolute error')
    # Avoid the arithmetic implication that current aggregate accounting identifies a mechanism.
    text = text.replace('how capacity measurement scope affects deadline forecasts', 'how capacity calibration affects deadline forecasts')
    text = text.replace('Linear utilization–throughput regression |', 'Linear CPU-based fit |')
    text = text.replace('Quadratic utilization–throughput benchmark |', 'Quadratic CPU-based fit |')
    text = text.replace('[Kumar et al., VALUETOOLS 2009](https://eudl.eu/pdf/10.4108/ICST.VALUETOOLS2009.7799),\n[Zhang et al., 2013](https://scialert.net/fulltext/amp.php?doi=itj.2013.632.639).', '[2,3].')
    text = text.replace('[Mi et al., 2010](https://link.springer.com/article/10.1007/s13174-010-0012-9),\n[Casale et al., 2009](https://dl.ifip.org/db/conf/middleware/middleware2009/CasaleKKR09.pdf),\n[Cucinotta et al., 2023](https://retis.santannapisa.it/people/nino/publication/TCC23.pdf).', '[4–6].')
    text = text.replace('Busy-period and burst-aware sizing also have precedents, as does aggregate\nutilization accounting.',
        'Burst-aware sizing and controlled bursty benchmark construction have\nprecedents [4,5]. Aggregate utilization accounting is also established in\nload-dependent inference [2,3].')
    # Remove working-version discussion from the scientific manuscript; preserve it in the guide.
    cut = text.index('Version 4 and its original\naudit remain historical records;')
    text = text[:cut] + '''These saved records support independent reproduction without performance recollection.

## 6. Conclusion

In the tested service, substituting whole-run CPU/job for busy capacity causes
substantial deadline-forecast error. A dedicated additive idle correction does
not repair that substitution. Busy calibration is accurate across the declared
prospective validation conditions, while a nonlinear CPU-only benchmark recovers
most of its accuracy. The busy-versus-quadratic advantage remains inconclusive
under the frozen minimum-effect criterion. These results support a bounded
empirical lesson: capacity calibration should be assessed against fresh deadline
outcomes and credible load-dependent alternatives. The responsible choice of
calibration outside the measured conditions remains open.

## References

'''
    text += '\n\n'.join(f'{i}. {label} [Primary source]({url}).' for i, (_, label, url) in enumerate(REFS, 1)) + '\n'
    (PAPER / 'capacity_calibration_empirical.md').write_text(text)
    support = (ROOT / 'docs/runtime_io_paper_supporting_material_20261008.md').read_text()
    support = support.replace('8 October 2026. Supporting record for the [version-5 manuscript](runtime_io_short_working_draft_v5.md).',
        '8 October 2026. Supporting record for the [final empirical manuscript](capacity_calibration_empirical.md). The version-5 supporting record is preserved in `docs/`.')
    support = re.sub(r'\]\((runtime_io_[^)]+)\)', r'](../docs/\1)', support)
    support += '''
## S7. Later novelty screens and finalization

The calibration-cost, passive-forecast, profiler-correction, CPU-attribution and
dynamic quota-update checks add no new validated method to the manuscript.
Their verdicts remain closed at the present gates. They are research-direction
records, not additional experimental validation for this paper.

- [Calibration-cost assessment](../docs/runtime_io_calibration_cost_assessment_20261008.md).
- [Passive-baseline assessment](../docs/runtime_io_passive_baseline_assessment_20261008.md).
- [Profiler-semantics assessment](../docs/runtime_io_profiler_semantics_gate_20261008.md).
- [CPU-attribution assessment](../docs/runtime_io_cpu_attribution_novelty_screen_20261008.md).
- [Dynamic quota-update assessment](../docs/runtime_io_quota_update_replay_assessment_20261008.md).
- [Final paper verification](../analysis/runtime_io_paper_finalization/20261008/report.json).
- [Offline reproduction and claim guide](capacity_calibration_reproducibility.md).

Finalization adds figures from saved observations, explicit calibration schedules,
recorded runtime/kernel settings and complete references. It does not collect
data, fit a new model, change thresholds, identify a causal mechanism or establish
superiority over full published estimators. Collection remains stopped and quota
period selection remains on hold. Any extension follows completion of this paper
and needs a separately justified concrete question.
'''
    (PAPER / 'capacity_calibration_supporting_material.md').write_text(support)
    return text


def escape(text):
    return ''.join({'\\':r'\textbackslash{}','&':r'\&','%':r'\%','$':r'\$',
                    '#':r'\#','_':r'\_','{':r'\{','}':r'\}','~':r'\textasciitilde{}',
                    '^':r'\textasciicircum{}','≤':r'$\leq$','≥':r'$\geq$',
                    '±':r'$\pm$','²':r'$^2$'}.get(c,c) for c in text)


def inline(text):
    tokens = []
    def token(raw):
        tokens.append(raw); return f'TOKENPLACEHOLDER{len(tokens)-1}END'
    text = re.sub(r'`([^`]+)`', lambda m: token(r'\texttt{' + escape(m[1]) + '}'), text)
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', lambda m: token(
        r'\href{' + m[2] + '}{' + escape(m[1]) + '}' if m[2].startswith('http') else escape(m[1])), text)
    text = re.sub(r'\*\*([^*]+)\*\*', lambda m: token(r'\textbf{' + escape(m[1]) + '}'), text)
    for citation, keys in [('[1]','linux'),('[2,3]','kumar,zhang'),('[4,5]','mi,casale'),('[4–6]','mi,casale,cucinotta')]:
        text = text.replace(citation, token(r'\cite{' + keys + '}'))
    text = escape(text)
    for i, raw in enumerate(tokens): text = text.replace(f'TOKENPLACEHOLDER{i}END',raw)
    return text


def tex_figure(data, calibration):
    """Embed vector plots using core LaTeX picture commands; no plot packages."""
    xmax = 160 if calibration else 40
    ymax = .65 if calibration else 65
    width, height, left, bottom = 130., 65., 18., 15.
    def point(x,y):return left+width*x/xmax,bottom+height*y/ymax
    def segment(x1,y1,x2,y2,color='black',thickness='.20mm'):
        a,b=point(x1,y1);c,d=point(x2,y2)
        return f'{{\\color{{{color}}}\\linethickness{{{thickness}}}\\qbezier({a:.5f},{b:.5f})({(a+c)/2:.5f},{(b+d)/2:.5f})({c:.5f},{d:.5f})}}\n'
    def marker(x,y,color,kind):
        a,b=point(x,y)
        shape={'square':r'\makebox(0,0){\rule{1.7mm}{1.7mm}}','cross':r'\makebox(0,0){$\times$}',
               'circle':r'\circle*{1.7}','triangle':r'\makebox(0,0){$\triangle$}',
               'diamond':r'\makebox(0,0){$\diamond$}'}[kind]
        return f'\\put({a:.5f},{b:.5f}){{\\color{{{color}}}{shape}}}\n'
    body=''
    if not calibration:
        for i in range(260):
            x=i*xmax/260;lo=max(0,x-3);hi=min(ymax,x+3);a,b=point(x,lo)
            body+=f'\\put({a:.5f},{b:.5f}){{\\color{{gray!15}}\\rule{{.51mm}}{{{height*(hi-lo)/ymax:.5f}mm}}}}\n'
    xs=[0,40,80,120,160] if calibration else [0,10,20,30,40]
    ys=[0,.1,.2,.3,.4,.5,.6] if calibration else [0,10,20,30,40,50,60]
    for x in xs:
        body+=segment(x,0,x,ymax,'gray!25','.10mm');a,b=point(x,0)
        body+=f'\\put({a:.5f},{b-3:.5f}){{\\makebox(0,0){{{x}}}}}\n'
    for y in ys:
        body+=segment(0,y,xmax,y,'gray!25','.10mm');a,b=point(0,y)
        label=f'{y:.1f}' if calibration else str(y)
        body+=f'\\put({a-3:.5f},{b:.5f}){{\\makebox(0,0)[r]{{{label}}}}}\n'
    body+=segment(0,0,xmax,0)+segment(0,0,0,ymax)
    xlabel='Completion throughput (jobs/s)' if calibration else r'Observed deadline misses (\%)'
    ylabel='CPU-seconds / wall-second' if calibration else r'Frozen forecast misses (\%)'
    body+=r'\put(83,3){\makebox(0,0){'+xlabel+'}}\n'
    body+=r'\put(1,47.5){\makebox(0,0){\rotatebox{90}{'+ylabel+'}}}\n'
    if calibration:
        for p in data['calibration_points']:body+=marker(p['throughput_rps'],p['utilization'],'black','circle')
        maximum=max(p['throughput_rps'] for p in data['calibration_points'])
        for key,color in [('regression','gray'),('quadratic','orange!85!black')]:
            m=data['calibration_models'][key]
            for start,end,dashed in [(0,maximum,False),(maximum,160,True)]:
                n=120
                for i in range(n):
                    if dashed and i%2:continue
                    x1=start+(end-start)*i/n;x2=start+(end-start)*(i+1)/n
                    y1=m['intercept']+m['demand_sec']*x1+m['quadratic_sec2']*x1*x1
                    y2=m['intercept']+m['demand_sec']*x2+m['quadratic_sec2']*x2*x2
                    body+=segment(x1,y1,x2,y2,color,'.30mm')
            body+=marker(m['capacity_rps'],.5,color,'diamond')
        body+=segment(0,.5,160,.5,'black','.15mm')
        b=data['summary']['busy']['capacity_rps']
        for i in range(0,80,2):body+=segment(b,ymax*i/80,b,ymax*(i+1)/80,'blue!65!black','.30mm')
        legends=[('black','Idle/steady observations'),('gray','Linear fit'),('orange!85!black','Quadratic fit'),('black','Configured allowance'),('blue!65!black','Separate busy estimate')]
        for i,(color,label) in enumerate(legends):
            x=20+(i%2)*68;y=105-(i//2)*6
            body += r'\put(' + str(x) + ',' + str(y) + r'){\color{' + color + r'}\rule{4mm}{.3mm}}\put(' + str(x+6) + ',' + str(y) + r'){\makebox(0,0)[l]{' + label + '}}' + '\n'
        caption='Twelve idle/steady calibration observations and retained fits. Dashed curves extend beyond the measured throughput range; diamonds mark capacity roots. Busy capacity is measured separately and does not constrain the fits. No uncertainty band is inferred.'
        label='fig:calibration'
    else:
        for i in range(0,80,2):body+=segment(xmax*i/80,xmax*i/80,xmax*(i+1)/80,xmax*(i+1)/80,'black','.15mm')
        for (key,label),color,kind in zip(METHODS,['brown','violet','blue!65!black','gray','orange!85!black'],['square','cross','circle','triangle','diamond']):
            for r in data['validation_trials']:body+=marker(r['observed_miss_pct'],r['forecasts'][key],color,kind)
        for i,((key,label),color) in enumerate(zip(METHODS,['brown','violet','blue!65!black','gray','orange!85!black'])):
            x=20+(i%2)*68;y=105-(i//2)*6
            body += r'\put(' + str(x) + ',' + str(y) + r'){\color{' + color + r'}\rule{4mm}{.3mm}}\put(' + str(x+6) + ',' + str(y) + r'){\makebox(0,0)[l]{' + label + '}}' + '\n'
        caption='Frozen forecasts and all-offer outcomes in all sixteen validation trials. The diagonal denotes agreement; the gray band is the declared $\\pm3$ percentage-point tolerance, not a confidence interval. Repeated points overlap, including eight zero-miss trials. Idle-corrected and whole-run points nearly overlap.'
        label='fig:forecasts'
    return '\\begin{figure}[htbp]\n\\centering\n{\\footnotesize\\setlength{\\unitlength}{1mm}\\begin{picture}(155,110)\n'+body+'\\end{picture}}\n\\caption{'+caption+'}\\label{'+label+'}\n\\end{figure}\n'


def latex(text, data):
    lines=text.splitlines(); out=[]; i=0; equations=0
    mathblocks=[r'\begin{align*}c_{\mathrm{whole}} &= C/N, & \mu_{\mathrm{whole}} &= q/\operatorname{mean}(c_{\mathrm{whole}}),\\\mu_{\mathrm{busy}} &= \operatorname{mean}(N_{\mathrm{window}}/T_{\mathrm{window}}).\end{align*}',
                r'\begin{align*}\mu_{\mathrm{idle}}&=(q-b_{\mathrm{idle}})/\operatorname{mean}((C-b_{\mathrm{idle}}T)/N),\\ U&=C/T,\qquad X=N/T,\\ U_{\mathrm{linear}}(X)&=b+dX,\\U_{\mathrm{quadratic}}(X)&=b+dX+eX^2,\\ \mu_{\mathrm{regression}}&=\text{admissible positive root of }U(X)=q.\end{align*}']
    while i<len(lines):
        line=lines[i]
        if line.startswith('# '): i+=1; continue
        if line=='## References': break
        if line=='## Abstract': out.append(r'\begin{abstract}'); i+=1; continue
        if line.startswith('## '):
            if line.startswith('## 1.'): out.append(r'\end{abstract}')
            title=re.sub(r'^\d+\.\s*','',line[3:]);out.append(r'\section{'+inline(title)+'}');i+=1;continue
        if line.startswith('### '):
            title=re.sub(r'^\d+\.\d+\s*','',line[4:]);out.append(r'\subsection{'+inline(title)+'}');i+=1;continue
        if line.startswith('```'):
            i+=1
            while not lines[i].startswith('```'):i+=1
            out.append(mathblocks[equations]);equations+=1;i+=1;continue
        if line.startswith('!['):
            calibration='Calibration observations' in line;out.append(tex_figure(data,calibration));i+=1
            while i<len(lines) and not lines[i].startswith('**Figure '):i+=1
            while i<len(lines) and lines[i].strip():i+=1
            continue
        if line.startswith('|'):
            rows=[]
            while i<len(lines) and lines[i].startswith('|'):
                row=[x.strip() for x in lines[i].strip('|').split('|')]
                if not all(re.fullmatch(r'[-:]+',x) for x in row):rows.append(row)
                i+=1
            n=len(rows[0]);out.append(r'\begin{table}[htbp]\centering\small\setlength{\tabcolsep}{5pt}\resizebox{\linewidth}{!}{\begin{tabular}{l'+'r'*(n-1)+'}\\toprule')
            for j,row in enumerate(rows):
                if j == 0 and n == 7:
                    out.append(r'Input & \shortstack{Capacity\\jobs/s} & \shortstack{Deadline\\MAE pp} & \shortstack{Max. deadline\\error pp} & \shortstack{Max. capacity\\error \%} & \shortstack{Deadline\\passes /16} & \shortstack{Capacity\\passes /16} \\')
                else:
                    out.append(' & '.join(inline(x) for x in row)+r' \\')
                if j==0:out.append(r'\midrule')
            caption = 'Frozen capacity inputs and validation errors in the final prospective comparison. pp denotes percentage points.' if n == 7 else 'Earlier prospective validation across work sizes and burst timescales. Each row summarizes four trials.'
            out.append(r'\bottomrule\end{tabular}}\caption{' + caption + r'}\end{table}');continue
        out.append(inline(line));i+=1
    preamble=r'''\documentclass[11pt,a4paper]{article}
\usepackage[margin=22mm]{geometry}
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage{lmodern,amsmath,booktabs,graphicx,microtype}
\usepackage{xcolor}
\usepackage[hidelinks,breaklinks]{hyperref}
\usepackage{url}
\setlength{\emergencystretch}{3em}
\title{Capacity Calibration and Deadline Forecasts Under a Fractional CPU Quota}
\author{}
\date{}
\begin{document}
\maketitle
'''
    bib='\\begin{thebibliography}{9}\n'+'\n'.join(r'\bibitem{'+key+'} '+escape(label)+r' \url{'+url+'}.' for key,label,url in REFS)+'\n\\end{thebibliography}\n\\end{document}\n'
    (PAPER/'capacity_calibration_empirical.tex').write_text(preamble+'\n'.join(out)+'\n'+bib)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--figures-only', type=Path, metavar='DIRECTORY')
    args=parser.parse_args()
    if args.figures_only is not None:
        directory=args.figures_only.resolve()
        if directory == OUT.resolve() or OUT.resolve() in directory.parents:
            raise ValueError('choose a separate figure output directory')
        plots(figure_data(), directory)
        print('Regenerated two saved-data figures in', directory)
        return
    if (OUT/'seal.json').exists():
        raise ValueError('preserve finalization artifacts; use --figures-only or verify_empirical_paper.py')
    OUT.mkdir(parents=True,exist_ok=True);PAPER.mkdir(exist_ok=True)
    data=figure_data();(OUT/'figure_data.json').write_text(json.dumps(data,indent=2)+'\n')
    text=manuscript();plots(data);latex(text,data)
    (OUT/'references.json').write_text(json.dumps([dict(key=k,reference=r,url=u) for k,r,u in REFS],indent=2)+'\n')
    print('Built Markdown, standalone LaTeX, supporting material and two saved-data figures; no measurements or new fits.')


if __name__=='__main__':main()
