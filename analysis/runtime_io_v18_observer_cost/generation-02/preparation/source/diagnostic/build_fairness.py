#!/usr/bin/env python3
"""Build and seal stock/patched images without replacing the v8 images."""
import json
from pathlib import Path
import shutil
import sys
import tempfile

import run
sys.path.insert(0,str(run.HERE/'runtime_fairness'))
import prepare

MANIFEST = run.HERE/'bin/fairness_build.json'
DECODER = run.HERE/'bin/fairness-go-trace'
SOURCE = run.ROOT/'analysis/runtime_io_v8_long_waits/go_source/runtime'
PREVIOUS_DECODER = run.ROOT/'analysis/runtime_io_v8_long_waits/go-trace'
DECODER_SHA = 'e5eb16fa367b755509001974e3bc2a80e2931b4f4efa04bf92bdddf31c86b77a'
TAGS = {'stock':'quota-diagnostic-stock:9','patched':'quota-diagnostic-fairness:9'}


def dependencies():
    return (run.build_sources()+[Path(__file__),run.HERE/'runtime_fairness/Dockerfile',
            run.HERE/'runtime_fairness/prepare.py']+[SOURCE/n for n in prepare.EXPECTED])


def verify_manifest():
    base = run.verify_build()
    value = run.read(MANIFEST)
    if value['sources'] != run.hashes(dependencies()) or value['base_build_sha256'] != run.sha(run.BUILD):
        raise RuntimeError('Fairness build sources changed; rebuild before a NEW session')
    if value['base_build'] != base or value['decoder_sha256'] != run.sha(DECODER):
        raise RuntimeError('Client/base build or pinned decoder changed')
    if value['compiler_image_id'] != prepare.IMAGE or run.image_id('golang:1.26.1-alpine') != prepare.IMAGE:
        raise RuntimeError('Pinned compiler image differs')
    for mode in ('stock','patched'):
        if run.image_id(value['images'][mode]) != value['images'][mode]:
            raise RuntimeError('Frozen runtime image unavailable: '+mode)
        labels=json.loads(run.capture(['docker','image','inspect','--format','{{json .Config.Labels}}',value['images'][mode]]))
        expected='stock' if mode=='stock' else 'pending-preemption-fairness-v1'
        if labels.get('research.runtime.variant') != expected:
            raise RuntimeError('Runtime image variant label mismatch')
    if value['images']['stock']==value['images']['patched']:
        raise RuntimeError('Stock and patched images must differ')
    return value


def build():
    base=run.verify_build()
    if run.image_id('golang:1.26.1-alpine')!=prepare.IMAGE:
        raise RuntimeError('Expected retained Go 1.26.1 compiler image')
    if run.sha(PREVIOUS_DECODER)!=DECODER_SHA:
        raise RuntimeError('Retained pinned trace decoder changed')
    with tempfile.TemporaryDirectory(prefix='quota-fairness-build-') as tmp:
        context=Path(tmp)
        prepare.prepare(SOURCE,context/'runtime')
        shutil.copytree(run.HERE/'service',context/'service',ignore=shutil.ignore_patterns('*.trace'))
        shutil.copy2(run.HERE/'runtime_fairness/Dockerfile',context/'Dockerfile')
        candidate=run.read(context/'runtime/manifest.json')
        for mode,tag in TAGS.items():
            print('BUILD:',mode,flush=True)
            run.sp.run(['docker','build','--network','none','--build-arg','COMPILER_IMAGE='+prepare.IMAGE,
                        '--target',mode,'-t',tag,str(context)],check=True)
    shutil.copy2(PREVIOUS_DECODER,DECODER)
    DECODER.chmod(0o755)
    run.put(MANIFEST,dict(schema=1,built_at=run.now(),compiler_image_id=prepare.IMAGE,
            images={mode:run.image_id(tag) for mode,tag in TAGS.items()},tags=TAGS,
            sources=run.hashes(dependencies()),base_build=base,base_build_sha256=run.sha(run.BUILD),
            decoder=str(DECODER),decoder_sha256=run.sha(DECODER),candidate=candidate,
            eligible_for_full=False))
    verify_manifest()
    print('FAIRNESS BUILD SEALED:',MANIFEST,flush=True)


if __name__=='__main__':
    build()
