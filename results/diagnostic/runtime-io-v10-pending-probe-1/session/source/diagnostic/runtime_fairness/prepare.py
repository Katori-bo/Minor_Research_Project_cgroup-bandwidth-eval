#!/usr/bin/env python3
"""Prepare an isolated, unqualified Go 1.26.1 scheduler candidate.

No installed toolchain, service source, sealed session or build seal is changed.
"""
import argparse
import difflib
import hashlib
import json
from pathlib import Path

EXPECTED = {
    'proc.go': 'b0ea864c1dd251cd9146644863ae9126ca57761dff05862dc80ab0799925fec6',
    'export_test.go': '2d1c20d71fea179ee4a673c567d06c53fe93307310479d7f5e20604ef4f06b2a',
    'proc_test.go': '8afb6d8304993fcc9301314a02c5d0bf18459005f95f1ebcdd6e44e579e21a61',
}
IMAGE = 'sha256:2389ebfa5b7f43eeafbd6be0c3700cc46690ef842ad962f6c5bd6be49ed82039'


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError('expected exactly one source anchor: '+old[:80])
    return text.replace(old, new, 1)


def patch_proc(text):
    text = replace_once(text,
        'func findRunnable() (gp *g, inheritTime, tryWakeP bool) {',
        'func findRunnable(preemptRequested bool) (gp *g, inheritTime, tryWakeP bool) {')
    text = replace_once(text,
        '\tif pp.schedtick%61 == 0 && !sched.runq.empty() {',
        '\t// Research candidate: honor a pending preemption at the next ordinary\n'
        '\t// work selection, even when the previous G parked before preemption.\n'
        '\tforceFair := preemptRequested\n'
        '\tpreemptRequested = false\n'
        '\tif (forceFair || pp.schedtick%61 == 0) && !sched.runq.empty() {')
    text = replace_once(text,
        '\t// local runq\n\tif gp, inheritTime := runqget(pp); gp != nil {',
        '\t// On a fairness turn, prefer older local work over runnext.\n'
        '\tif gp, inheritTime := runqgetPolicy(pp, !forceFair); gp != nil {')
    text = replace_once(text,
        'top:\n\tpp := mp.p.ptr()\n\tpp.preempt = false',
        'top:\n\tpp := mp.p.ptr()\n\tpreemptRequested := pp.preempt\n\tpp.preempt = false')
    text = replace_once(text,
        '\tgp, inheritTime, tryWakeP := findRunnable() // blocks until work is available',
        '\tgp, inheritTime, tryWakeP := findRunnable(preemptRequested) // blocks until work is available')
    text = replace_once(text,
        'func runqget(pp *p) (gp *g, inheritTime bool) {\n',
        'func runqget(pp *p) (gp *g, inheritTime bool) {\n'
        '\treturn runqgetPolicy(pp, true)\n}\n\n'
        '// runqgetPolicy preserves normal runnext priority unless a fairness turn\n'
        '// requests older local work first. A fairness turn starts a new time slice.\n'
        'func runqgetPolicy(pp *p, preferNext bool) (gp *g, inheritTime bool) {\n')
    text = replace_once(text,
        '\tif next != 0 && pp.runnext.cas(next, 0) {\n\t\treturn next.ptr(), true\n\t}',
        '\tif preferNext && next != 0 && pp.runnext.cas(next, 0) {\n\t\treturn next.ptr(), true\n\t}')
    text = replace_once(text,
        '\t\tif t == h {\n\t\t\treturn nil, false\n\t\t}\n\t\tgp := pp.runq[h%uint32(len(pp.runq))].ptr()',
        '\t\tif t == h {\n'
        '\t\t\t// Keep the sole runnext runnable when no older local work exists.\n'
        '\t\t\tif !preferNext && next != 0 && pp.runnext.cas(next, 0) {\n'
        '\t\t\t\treturn next.ptr(), false\n\t\t\t}\n'
        '\t\t\treturn nil, false\n\t\t}\n\t\tgp := pp.runq[h%uint32(len(pp.runq))].ptr()')
    return text


EXPORT_TEST = r'''
// RunResearchFairQueueTest verifies queue conservation and ordering for the
// experimental pending-preemption policy. It is not a latency benchmark.
func RunResearchFairQueueTest() {
	for _, preferNext := range []bool{true, false} {
		for _, wrapped := range []bool{false, true} {
			pp := new(p)
			gs := make([]g, 3)
			Escape(gs)
			if wrapped {
				pp.runqhead = uint32(len(pp.runq)) - 1
				pp.runqtail = pp.runqhead
			}
			runqput(pp, &gs[0], false)
			runqput(pp, &gs[1], false)
			runqput(pp, &gs[2], true)
			order := []int{0, 1, 2}
			if preferNext {
				order = []int{2, 0, 1}
			}
			for _, index := range order {
				gp, inherit := runqgetPolicy(pp, preferNext)
				if gp != &gs[index] || inherit != (preferNext && index == 2) {
					throw("research fairness queue order/time slice mismatch")
				}
			}
			if gp, _ := runqgetPolicy(pp, preferNext); gp != nil || !runqempty(pp) {
				throw("research fairness queue lost or duplicated work")
			}
		}
		pp := new(p)
		gp := new(g)
		Escape(gp)
		runqput(pp, gp, true)
		got, inherit := runqgetPolicy(pp, preferNext)
		if got != gp || inherit != preferNext || !runqempty(pp) {
			throw("research fairness stranded sole runnext")
		}
	}
}
'''
PROC_TEST = '''
// A functional queue-policy check, not a performance measurement.
func TestResearchPendingPreemptFairQueue(t *testing.T) {
\truntime.RunResearchFairQueueTest()
}
'''


def prepare(source, output):
    if output.exists():
        raise ValueError('use a fresh output directory')
    if output.is_relative_to(source):
        raise ValueError('output must be outside pinned source')
    original = {}
    for name, expected in EXPECTED.items():
        data = (source/name).read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise ValueError('pinned Go 1.26.1 source mismatch: '+name)
        original[name] = data.decode()
    changed = dict(original)
    changed['proc.go'] = patch_proc(original['proc.go'])
    changed['export_test.go'] += EXPORT_TEST
    changed['proc_test.go'] += PROC_TEST
    output.mkdir(parents=True)
    diff = ''
    for name, text in changed.items():
        (output/name).write_text(text)
        diff += ''.join(difflib.unified_diff(original[name].splitlines(True),text.splitlines(True),
                                           fromfile='a/src/runtime/'+name,tofile='b/src/runtime/'+name))
    (output/'runtime_fairness.patch').write_text(diff)
    hashes = {name:hashlib.sha256((output/name).read_bytes()).hexdigest() for name in changed}
    (output/'manifest.json').write_text(json.dumps(dict(
        candidate='pending-preemption-fairness-v1',status='experimental_unqualified',
        compiler_image_id=IMAGE,original_sha256=EXPECTED,patched_sha256=hashes,
        generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        performance_run=False,eligible_for_full=False,
        limitations='Saved traces do not record pending preemption flags or queue positions; '
                    'this candidate tests a source-supported causal hypothesis.'),indent=2)+'\n')
    print(output/'runtime_fairness.patch')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    args = parser.parse_args()
    prepare(args.source.resolve(),args.output.resolve())
