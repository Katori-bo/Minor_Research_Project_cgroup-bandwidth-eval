"""Deterministically render the standalone unified manuscript without dependencies."""
from pathlib import Path
import argparse
import re

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'paper/unified_manuscript.md'
TARGET = SOURCE.with_suffix('.tex')


def escape(value):
    substitutions = {'\\': r'\textbackslash{}', '&': r'\&', '%': r'\%', '$': r'\$',
                     '#': r'\#', '_': r'\_', '{': r'\{', '}': r'\}',
                     '~': r'\textasciitilde{}', '^': r'\textasciicircum{}'}
    return ''.join(substitutions.get(c, c) for c in value).replace('≤', r'$\leq$')


def inline(value):
    pattern = r'(`[^`]+`|\*\*[^*]+\*\*|\[[^\]]+\]\([^)]+\))'
    pieces = []
    for part in re.split(pattern, value):
        if part.startswith('`'):
            pieces.append(r'\texttt{' + escape(part[1:-1]) + '}')
        elif part.startswith('**'):
            pieces.append(r'\textbf{' + escape(part[2:-2]) + '}')
        elif re.fullmatch(r'\[[^\]]+\]\([^)]+\)', part):
            label, url = re.match(r'\[([^\]]+)\]\(([^)]+)\)', part).groups()
            if url.startswith('https://'):
                pieces.append(r'\href{' + url + '}{' + escape(label) + '}')
            else:
                pieces.append(escape(label))
        else:
            pieces.append(escape(part))
    return ''.join(pieces)


def table(lines):
    rows = [[part.strip() for part in line.strip('|').split('|')] for line in lines]
    rows = [r for r in rows if not all(re.fullmatch(r'[-: ]+', cell) for cell in r)]
    n = len(rows[0])
    if n == 3:
        widths = [.23, .30, .39]
    elif n == 4:
        widths = [.31, .19, .20, .22]
    else:
        widths = [.36] + [.56/(n-1)]*(n-1)
    columns = ''.join(r'>{\raggedright\arraybackslash}p{' + f'{w:.4f}' + r'\linewidth}' for w in widths)
    def row(cells):
        return ' & '.join(inline(c) for c in cells) + r' \\'
    header = row(rows[0])
    return '\n'.join([r'\begingroup\small\setlength{\tabcolsep}{3pt}\renewcommand{\arraystretch}{1.12}',
                      r'\begin{longtable}{' + columns + '}', r'\toprule', header,
                      r'\midrule\endfirsthead', r'\toprule', header,
                      r'\midrule\endhead', *[row(r) for r in rows[1:]],
                      r'\bottomrule\end{longtable}\endgroup'])


def render(text):
    lines = text.splitlines()
    title = lines.pop(0).removeprefix('# ')
    output = [r'\documentclass[11pt,a4paper]{article}',
              r'\usepackage[margin=22mm]{geometry}', r'\usepackage[T1]{fontenc}',
              r'\usepackage[utf8]{inputenc}', r'\usepackage{lmodern,microtype,amsmath,booktabs,longtable,array}',
              r'\usepackage[hidelinks,breaklinks]{hyperref}', r'\usepackage{url}',
              r'\setlength{\emergencystretch}{3em}', r'\setlength{\parskip}{0.25em}',
              r'\title{' + escape(title) + '}', r'\author{}', r'\date{}',
              r'\begin{document}\maketitle']
    i = 0
    abstract = False
    references = False
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        if line == '## Abstract':
            output.append(r'\begin{abstract}')
            abstract = True
        elif line.startswith('## '):
            if abstract:
                output.append(r'\end{abstract}')
                abstract = False
            if line == '## References':
                output.append(r'\begin{thebibliography}{99}')
                references = True
            else:
                output.append(r'\section{' + escape(re.sub(r'^## \d+\. ', '', line)) + '}')
        elif line.startswith('### '):
            output.append(r'\subsection{' + escape(re.sub(r'^### \d+\.\d+ ', '', line)) + '}')
        elif line.startswith('|'):
            block = []
            while i < len(lines) and lines[i].startswith('|'):
                block.append(lines[i]); i += 1
            output.append(table(block)); continue
        elif references:
            number, body = re.match(r'(\d+)\. (.*)', line).groups()
            output.append(r'\bibitem{ref' + number + '} ' + inline(body))
        else:
            block = [line]
            while i+1 < len(lines) and lines[i+1].strip() and not lines[i+1].startswith(('#', '|')):
                i += 1; block.append(lines[i])
            output.append(inline(' '.join(block)))
        i += 1
    if references:
        output.append(r'\end{thebibliography}')
    output.append(r'\end{document}')
    return '\n\n'.join(output) + '\n'


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    result = render(SOURCE.read_text())
    if args.check:
        if TARGET.read_text() != result:
            raise ValueError('Unified Markdown/LaTeX derivation differs')
        print('Unified standalone source matches Markdown.')
    else:
        TARGET.write_text(result)
        print(TARGET)
