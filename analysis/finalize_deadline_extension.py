"""Generate saved-result figures and standalone LaTeX for the extension.

No collection, new fit or scientific threshold changes. Run with Python -B.
After sealing finalization, only --figures-only in a separate directory is allowed.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'analysis/runtime_io_deadline_extension_finalization/20261010'
PAPER = ROOT / 'paper'
REVIEW = ROOT / 'analysis/runtime_io_deadline_boundary_prior_work_review/20261010'
TITLE = 'Deadline Forecasting Under a Fractional CPU Quota: Prospective Comparisons and Application-Transfer Limits'
CAPTION = ('Three separate prospective comparisons. Bars show equal-profile/block '
           'mean absolute miss-fraction error. The NGINX point and interval show '
           'the declared conditional six-block mean-error interval; small points '
           'are its six block errors. The dashed line is its 5 pp upper-interval '
           'criterion. Endpoints, domains, comparators and criteria differ; '
           'these panels do not establish a common model ranking.')


def read(path):
    return json.loads((ROOT / path).read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def figure_data():
    v30 = read('analysis/runtime_io_v30_result_review/20261009-generation01/report.json')
    v31 = read('analysis/runtime_io_v31_result_review/20261009-generation01/report.json')
    nginx = read('analysis/runtime_io_nginx_prediction/generation-01/campaign/comparison.json')
    return dict(schema=1, no_new_fit=True,
        v30=dict(deadline_ms=25, fluid_busy_mae_pp=v30['secondary_deadline_mae_pp']['25']['fluid_busy'],
                 periodic_delay_mae_pp=v30['primary_equal_profile_mae_pp']),
        v31=dict(deadline_ms=10,
                 periodic_delay_mae_pp=v31['deadline_grid']['periodic_uniform_phase_calibrated_delay']['10']['mae_pp'],
                 paired_cdf_mae_pp=v31['deadline_grid']['joint_calibration_cdf']['10']['mae_pp']),
        nginx=dict(deadline_ms=nginx['primary_deadline_ns'] / 1e6,
                   mean_block_mae_pp=nginx['mean_block_mae_pp'],
                   conditional_interval_pp=nginx['conditional_model_based_95_interval_pp'],
                   block_errors_pp=[sum(e['absolute_error_pp'] for e in nginx['errors']
                                      if e['block'] == b) / 3 for b in range(1, 7)],
                   upper_interval_criterion_pp=5),
        caption=CAPTION)


def plots(data, directory):
    os.environ.setdefault('MPLCONFIGDIR', '/tmp/deadline-extension-matplotlib')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size': 10, 'svg.fonttype': 'none',
                         'axes.spines.top': False, 'axes.spines.right': False})
    directory.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, 3, figsize=(10.5, 3.5), layout='constrained')
    panels = [('V30: Go, 25 ms', ['Constant-rate\nFIFO', 'Periodic\n+ delay'],
               [data['v30']['fluid_busy_mae_pp'], data['v30']['periodic_delay_mae_pp']],
               ['#777777', '#0072b2']),
              ('V31: Go, 10 ms', ['Periodic\n+ delay', 'Paired\nempirical CDF'],
               [data['v31']['periodic_delay_mae_pp'], data['v31']['paired_cdf_mae_pp']],
               ['#0072b2', '#d55e00'])]
    for ax, (title, labels, values, colors) in zip(axes, panels):
        ax.bar(range(2), values, color=colors, width=.6)
        for i, value in enumerate(values):
            ax.text(i, value + 1.3, f'{value:.3f}', ha='center', fontsize=10)
        ax.set(xticks=range(2), xticklabels=labels, ylim=(0, 82),
               title=title, ylabel='Mean absolute error (pp)')
        ax.set_axisbelow(True); ax.grid(axis='y', alpha=.2)
    ax = axes[2]; n = data['nginx']; low, high = n['conditional_interval_pp']
    ax.axhline(5, color='#a11c24', linestyle='--', lw=1.2)
    ax.scatter([-.18 + i * .072 for i in range(6)], n['block_errors_pp'],
               c='black', s=15, alpha=.65, label='Block errors')
    ax.errorbar([0], [n['mean_block_mae_pp']],
                yerr=[[n['mean_block_mae_pp'] - low], [high - n['mean_block_mae_pp']]],
                fmt='o', color='#d55e00', capsize=6, lw=2)
    ax.text(.20, n['mean_block_mae_pp'], f"{n['mean_block_mae_pp']:.3f}", va='center')
    ax.text(.20, high, f'{high:.3f}', va='center', fontsize=9)
    ax.text(.20, low, f'{low:.3f}', va='center', fontsize=9)
    ymax = max(12, max(n['block_errors_pp']) + 1)
    ax.set(xlim=(-.45, .55), ylim=(0, ymax), xticks=[0],
           xticklabels=['Full-response\nempirical CDF'],
           title='NGINX: 20.565395 ms', ylabel='Mean absolute error (pp)')
    ax.grid(axis='y', alpha=.2)
    ax.text(.5, -.24, 'Conditional 95% interval; criterion upper <= 5 pp',
            transform=ax.transAxes, ha='center', fontsize=8)
    for extension in ('png', 'svg'):
        fig.savefig(directory / f'prospective_comparisons.{extension}', dpi=180)
    plt.close(fig)


def escape(value):
    return ''.join({'\\': r'\textbackslash{}', '&': r'\&', '%': r'\%', '$': r'\$',
                    '#': r'\#', '_': r'\_', '{': r'\{', '}': r'\}',
                    '~': r'\textasciitilde{}', '^': r'\textasciicircum{}',
                    '≤': r'$\leq$', '≥': r'$\geq$', '±': r'$\pm$',
                    '–': r'\textendash{}', '—': r'\textemdash{}',
                    '|': r'\textbar{}'}.get(c, c) for c in value)


def inline(value):
    tokens = []
    def token(tex):
        tokens.append(tex); return f'INLINEPLACEHOLDER{len(tokens)-1}END'
    value = re.sub(r'`([^`]+)`', lambda m: token(r'\path{' + m[1] + '}'), value)
    value = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', lambda m: token(
        r'\href{' + m[2] + '}{' + escape(m[1]) + '}'
        if m[2].startswith('https://') else escape(m[1])), value)
    value = re.sub(r'\*\*([^*]+)\*\*', lambda m: token(r'\textbf{' + escape(m[1]) + '}'), value)
    value = escape(value)
    for i, tex in enumerate(tokens):
        value = value.replace(f'INLINEPLACEHOLDER{i}END', tex)
    return value


def vector_figure(data):
    """Self-contained vector counterpart, using core LaTeX picture commands."""
    out = [r'\begin{figure}[htbp]\centering',
           r'{\footnotesize\setlength{\unitlength}{1mm}\begin{picture}(160,87)']
    def label(x, y, value, alignment='c'):
        out.append('\\put(%.3f,%.3f){\\makebox(0,0)[%s]{%s}}' % (x, y, alignment, value))
    def line(x1, y1, x2, y2, color='black', width='.2mm'):
        out.append(f'{{\\color{{{color}}}\\linethickness{{{width}}}'
                   f'\\qbezier({x1:.3f},{y1:.3f})({(x1+x2)/2:.3f},{(y1+y2)/2:.3f})({x2:.3f},{y2:.3f})}}')
    n = data['nginx']; maxima = [82, 82, max(12, max(n['block_errors_pp']) + 1)]
    for panel, origin in enumerate([8, 62, 116]):
        scale = 48 / maxima[panel]
        line(origin, 22, origin + 38, 22); line(origin, 22, origin, 70)
        ticks = [0, 20, 40, 60, 80] if panel < 2 else [0, 5, 10, 15]
        for tick in ticks:
            if tick <= maxima[panel]:
                y = 22 + tick * scale
                line(origin, y, origin + 38, y, 'gray!25', '.1mm')
                label(origin-1.5, y, str(tick), 'r')
        if panel < 2:
            values = ([data['v30']['fluid_busy_mae_pp'], data['v30']['periodic_delay_mae_pp']]
                      if panel == 0 else [data['v31']['periodic_delay_mae_pp'], data['v31']['paired_cdf_mae_pp']])
            colors = ['gray', 'blue!65!black'] if panel == 0 else ['blue!65!black', 'orange!85!black']
            for j, (value, color) in enumerate(zip(values, colors)):
                x = origin + 5 + 18*j
                out.append(f'\\put({x:.3f},22){{\\color{{{color}}}\\rule{{9mm}}{{{value*scale:.4f}mm}}}}')
                label(x+4.5, 24+value*scale, f'{value:.3f}')
            label(origin+19, 79, 'V30: Go, 25 ms' if panel == 0 else 'V31: Go, 10 ms')
            label(origin+9.5, 17, 'Constant-rate' if panel == 0 else 'Periodic')
            label(origin+9.5, 13, 'FIFO' if panel == 0 else '+ delay')
            label(origin+27.5, 17, 'Periodic' if panel == 0 else 'Paired')
            label(origin+27.5, 13, '+ delay' if panel == 0 else 'CDF')
        else:
            x = origin+14
            for j, value in enumerate(n['block_errors_pp']):
                out.append(f'\\put({x-5+j*2:.3f},{22+value*scale:.3f}){{\\color{{black}}\\circle*{{.9}}}}')
            lo, hi = n['conditional_interval_pp']
            line(x, 22+lo*scale, x, 22+hi*scale, 'orange!85!black', '.4mm')
            for value in [lo, hi]:
                line(x-2, 22+value*scale, x+2, 22+value*scale, 'orange!85!black', '.4mm')
                label(x+5, 22+value*scale, f'{value:.3f}', 'l')
            out.append(f'\\put({x:.3f},{22+n["mean_block_mae_pp"]*scale:.3f}){{\\color{{orange!85!black}}\\circle*{{1.7}}}}')
            label(x+5, 22+n['mean_block_mae_pp']*scale, f'{n["mean_block_mae_pp"]:.3f}', 'l')
            for j in range(0, 38, 4):
                line(origin+j, 22+5*scale, origin+j+2, 22+5*scale, 'red!65!black')
            label(origin+19, 79, 'NGINX: 20.565395 ms')
            label(origin+19, 17, 'Full-response CDF')
            label(origin+19, 13, r'Conditional 95\% interval')
    label(80, 4, 'Mean absolute miss-fraction error (percentage points); independent panel scales')
    out += [r'\end{picture}}', r'\caption{' + escape(CAPTION) + r'}\label{fig:primary}', r'\end{figure}']
    return '\n'.join(out)


def references():
    result = [s for s in json.loads((REVIEW/'sources.json').read_text())['sources']
              if s['id'] in {f'S{i:02d}' for i in range(1, 7)}]
    # Full author lines were verified from the primary PDFs during the review.
    names = {'S03': 'Tommaso Cucinotta; Luca Abeni; Mauro Marinoni; Riccardo Mancini; Carlo Vitucci',
             'S04': 'Ahsan Ali; Riccardo Pinciroli; Feng Yan; Evgenia Smirni'}
    for source in result:
        if source['id'] in names: source['authors'] = names[source['id']]
    return result


def reference_label(source):
    who = source.get('authors', source.get('author'))
    return f"{who}. {source['title']}. {source.get('venue', source.get('version'))}."


def latex(text, data):
    lines = text[text.index('## Abstract'):].splitlines(); out=[]; i=0; abstract=False
    while i < len(lines):
        line = lines[i]
        if line == '## References': break
        if line == '## Abstract':
            out.append(r'\begin{abstract}'); abstract=True; i+=1; continue
        if line.startswith('## '):
            if abstract: out.append(r'\end{abstract}'); abstract=False
            title = re.sub(r'^\d+\.\s*', '', line[3:])
            out.append(r'\section{' + inline(title) + '}'); i+=1; continue
        if line.startswith('### '):
            out.append(r'\subsection{' + inline(line[4:]) + '}'); i+=1; continue
        if line.startswith('!['):
            out.append(vector_figure(data)); i+=1
            while i<len(lines) and not lines[i].startswith('**Figure 1.**'): i+=1
            while i<len(lines) and lines[i].strip(): i+=1
            continue
        if re.match(r'^\d+\. ', line):
            out.append(r'\begin{enumerate}')
            while i<len(lines):
                line=lines[i]
                if re.match(r'^\d+\. ',line):
                    out.append(r'\item '+inline(re.sub(r'^\d+\. ', '',line)))
                elif line.startswith('   '): out.append(inline(line.strip()))
                elif line.strip(): break
                i+=1
            out.append(r'\end{enumerate}'); continue
        if line.startswith('|'):
            rows=[]
            while i<len(lines) and lines[i].startswith('|'):
                row=[x.strip() for x in lines[i].strip('|').split('|')]
                if not all(re.fullmatch(r'[-:]+',x) for x in row): rows.append(row)
                i+=1
            n=len(rows[0]); weights=[.28]+[.72/(n-1)]*(n-1)
            spec=''.join(r'>{\raggedright\arraybackslash}p{'+f'{.90*w:.5f}'+r'\linewidth}' for w in weights)
            out.append(r'{\small\setlength{\tabcolsep}{2pt}\begin{longtable}{'+spec+r'}\toprule')
            for j,row in enumerate(rows):
                out.append(' & '.join(inline(x) for x in row)+r' \\')
                if j==0: out.append(r'\midrule\endhead')
            out.append(r'\bottomrule\end{longtable}}'); continue
        out.append(inline(line)); i+=1
    preamble=r'''\documentclass[11pt,a4paper]{article}
\usepackage[margin=22mm]{geometry}
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage{lmodern,amsmath,booktabs,longtable,array,graphicx,microtype,xcolor}
\usepackage[hidelinks,breaklinks]{hyperref}
\usepackage{url}
\setlength{\emergencystretch}{3em}
\title{'''+escape(TITLE)+r'''}
\author{}
\date{}
\begin{document}
\maketitle
'''
    bib=r'\begin{thebibliography}{9}'+'\n'
    for source in references():
        bib+=r'\bibitem{'+source['id']+'} '+escape(reference_label(source))+r' \url{'+source['urls'][0]+'}.\n'
    bib+=r'\end{thebibliography}'+'\n'+r'\end{document}'+'\n'
    return preamble+'\n'.join(out)+'\n'+bib.replace('\\n','\n')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--figures-only',type=Path)
    args=parser.parse_args(); data=figure_data()
    if args.figures_only:
        directory=args.figures_only.resolve()
        if directory==OUT or OUT in directory.parents:
            raise ValueError('Use a separate figure output directory')
        plots(data,directory); print('Regenerated saved-result figure:',directory); return
    if (OUT/'evidence-seal.json').exists():
        raise ValueError('Preserve sealed finalization; use verifier or --figures-only')
    OUT.mkdir(parents=True,exist_ok=True)
    manuscript=PAPER/'deadline_resolution_extension.md'; text=manuscript.read_text()
    if '![Three separate prospective comparisons]' not in text:
        marker='combined into a controlled application effect or a common accuracy interval.\n'
        assert marker in text
        figure='\n![Three separate prospective comparisons](../analysis/runtime_io_deadline_extension_finalization/20261010/figures/prospective_comparisons.png)\n\n**Figure 1.** '+CAPTION+'\n'
        text=text.replace(marker,marker+figure)
    text=text.split('\n## References')[0].rstrip()+'\n\n## References\n\n'+'\n\n'.join(
        f"{i}. {reference_label(s)} [Primary source]({s['urls'][0]})." for i,s in enumerate(references(),1))+'\n'
    manuscript.write_text(text)
    (PAPER/'deadline_resolution_extension.tex').write_text(latex(text,data))
    (OUT/'figure_data.json').write_text(json.dumps(data,indent=2)+'\n')
    (OUT/'sources.json').write_bytes((REVIEW/'sources.json').read_bytes())
    plots(data,OUT/'figures')
    print('Built saved-result figure and standalone LaTeX; no data collection or model fitting.')


if __name__=='__main__': main()
