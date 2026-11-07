#!/usr/bin/env python3
"""Render the integrated manuscript, retaining the historical renderers unchanged."""
import argparse
import re
from pathlib import Path
import render_deadline_extension_revision as previous

ROOT = Path(__file__).resolve().parents[1]
EXTRA_REFERENCES = [
    ('tales', 'Jialin Li; Naveen Kr. Sharma; Dan R. K. Ports; Steven D. Gribble. Tales of the Tail: Hardware, OS, and Application-level Sources of Tail Latency. SoCC 2014.', 'https://syslab.cs.washington.edu/papers/latency-socc14.pdf'),
    ('retail', 'Shuang Chen; Angela Jin; Christina Delimitrou; Jose F. Martinez. ReTail: Opting for Learning Simplicity to Enable QoS-Aware Power Management in the Cloud. HPCA 2022.', 'https://people.csail.mit.edu/delimitrou/papers/2022.hpca.retail.pdf'),
    ('mpora', 'Abigail Eisenklam et al. Uncertainty-Aware Resource Allocation for Multi-Path Programs with In-Kernel Predictions. ECRTS 2026. DOI: 10.4230/LIPIcs.ECRTS.2026.17.', 'https://drops.dagstuhl.de/storage/00lipics/lipics-vol375-ecrts2026/html/LIPIcs.ECRTS.2026.17/LIPIcs.ECRTS.2026.17.html'),
    ('amdpstate', 'Linux kernel documentation. amd-pstate CPU Performance Scaling Driver. Live documentation accessed 2026-10-10.', 'https://docs.kernel.org/admin-guide/pm/amd-pstate.html')]


def render(text):
    result = previous.render(text, previous.original.figure_data())
    result = result.replace(previous.original.escape(previous.original.TITLE),
        previous.original.escape(text.splitlines()[0].removeprefix('# ')), 1)
    result = result.replace(r'\begin{thebibliography}{9}', r'\begin{thebibliography}{99}')
    extra = []
    for number, (key, title, url) in enumerate(EXTRA_REFERENCES, 8):
        result = result.replace(f' [{number}]', r' \cite{' + key + '}')
        extra.append(r'\bibitem{' + key + '} ' + previous.original.escape(title) + r' \url{' + url + '}.')
    return result.replace(r'\end{thebibliography}', '\n'.join(extra) + '\n' + r'\end{thebibliography}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    source = render((ROOT / 'paper/deadline_resolution_extension.md').read_text())
    target = ROOT / 'paper/deadline_resolution_extension.tex'
    if args.check:
        if target.read_text() != source:
            raise ValueError('Integrated Markdown/LaTeX derivation differs')
        print('Integrated Markdown/LaTeX derivation verifies.')
    else:
        target.write_text(source)
        print('Integrated the existing standalone LaTeX source.')


if __name__ == '__main__': main()
