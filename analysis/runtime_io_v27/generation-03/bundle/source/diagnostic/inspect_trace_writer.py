#!/usr/bin/env python3
"""Inspect saved trace-writer syscall states without editing sealed attempts."""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile
import run
import trace_analysis


def summarize(lines):
    pending, goroutines, spans = {}, set(), []
    entries = 0

    def consume(block):
        nonlocal entries
        if not block:
            return
        header = trace_analysis.HEADER.match(block[0])
        if not header or header[2] != 'StateTransition':
            return
        transition = trace_analysis.TRANSITION.search(header[4])
        if not transition:
            return
        goroutine, old, new, _ = transition.groups()
        stamp = int(header[3])
        if goroutine in pending:
            if old != 'Syscall' or stamp < pending[goroutine]:
                raise ValueError('broken trace writer syscall interval')
            spans.append(stamp - pending.pop(goroutine))
        if new == 'Syscall' and any('main.(*cappedWriter).Write' in line for line in block):
            entries += 1
            pending[goroutine] = stamp
            goroutines.add(goroutine)

    block = []
    for line in lines:
        if trace_analysis.HEADER.match(line):
            consume(block)
            block = []
        block.append(line)
    consume(block)
    return dict(writer_syscall_entries=entries, writer_goroutines=sorted(goroutines),
                completed_syscall_spans=len(spans), missing_syscall_exit_count=len(pending),
                summed_writer_syscall_ms=sum(spans)/1e6,
                max_writer_syscall_ms=max(spans, default=0)/1e6)


def inspect(attempt):
    command = ['docker', 'run', '--rm', '-v', f'{attempt}:/trace:ro',
               'golang:1.26.1-alpine', 'go', 'tool', 'trace', '-d=parsed', '/trace/runtime.trace']
    with tempfile.TemporaryFile(mode='w+') as errors:
        proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=errors, text=True)
        try:
            result = summarize(proc.stdout)
            if proc.wait():
                errors.seek(0)
                raise RuntimeError(errors.read(2000))
        finally:
            proc.stdout.close()
            if proc.poll() is None:
                proc.kill()
                proc.wait()
    return dict(attempt=str(attempt), runtime_sha256=run.sha(attempt/'runtime.trace'),
                parser_image='golang:1.26.1-alpine', **result,
                limitations='Syscall state is elapsed Go state time, not CPU execution or proof of disk blocking. '
                            'Includes trace start/stop and drain. Unfinished spans are counted separately. '
                            'Counts and durations do not establish a causal scheduling effect.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('attempt', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    attempt, output = args.attempt.resolve(), args.output.resolve()
    if output.is_relative_to(attempt):
        parser.error('output must be outside the sealed attempt')
    result = inspect(attempt)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2)+'\n')
    print(output)
