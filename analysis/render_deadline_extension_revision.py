"""Render the corrected manuscript into the existing standalone editor source.

Reuse the historical renderer read-only, preserving native inline mathematics.
Never invoke the historical finalizer or overwrite its sealed package.
"""
import argparse
import re
from pathlib import Path
import finalize_deadline_extension as original

ROOT = Path(__file__).resolve().parents[1]
BASE_LATEX = original.latex
BASE_INLINE = original.inline


def inline_math(value):
    tokens = []
    def save(match):
        tokens.append(match[0])
        return f'MATHPLACEHOLDER{len(tokens)-1}END'
    value = re.sub(r'\$[^$\n]+\$', save, value)
    value = BASE_INLINE(value)
    for i, token in enumerate(tokens):
        value = value.replace(f'MATHPLACEHOLDER{i}END', token)
    return value


def render(text, data):
    # These are in-memory overrides, not changes to historical software/files.
    saved_inline, saved_caption = original.inline, original.CAPTION
    try:
        original.inline = inline_math
        original.CAPTION = re.search(r'\*\*Figure 1\.\*\* ([^\n]+)', text)[1]
        result = BASE_LATEX(text, data)
    finally:
        original.inline, original.CAPTION = saved_inline, saved_caption
    result = result.replace(r'{Paired}', r'{Queue-adj.}')
    result = result.replace('capacity-calibration paper [7]',
                            r'capacity-calibration paper \cite{capacityprecursor}')
    precursor = (r'\bibitem{capacityprecursor} '
                 'Capacity Calibration and Deadline Forecasts Under a Fractional CPU Quota. '
                 'Retained precursor manuscript, 2026; authors and public artifact location unset. '
                 r'Local artifact: \path{paper/capacity_calibration_empirical.md}.' + '\n')
    return result.replace(r'\end{thebibliography}', precursor + r'\end{thebibliography}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    path = ROOT/'paper/deadline_resolution_extension.tex'
    text = (ROOT/'paper/deadline_resolution_extension.md').read_text()
    rendered = render(text, original.figure_data())
    if args.check:
        if path.read_text() != rendered:
            raise ValueError('Live LaTeX differs from revised Markdown rendering')
        print('Corrected Markdown/LaTeX derivation verifies.')
    else:
        path.write_text(rendered)
        print('Updated the existing LaTeX source in place.')


if __name__ == '__main__':
    main()
