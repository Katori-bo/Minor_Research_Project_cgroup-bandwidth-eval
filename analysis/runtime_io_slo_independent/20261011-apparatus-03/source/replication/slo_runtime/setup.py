#!/usr/bin/env python3
"""External package check/image setup. No service or measurement is started."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/p) for p in ('runtime','diagnostic','scripts','analysis','slo')]
import common as c


def setup(root):
    package=c.verify_package(root);host=package['host']['id'];started=time.monotonic_ns()
    state=Path(root)/'runs'/host/'setup'
    c.require(not state.exists(),'preserve setup attempt; no automatic resume/overwrite')
    state.mkdir(parents=True)
    try:
        check=c.check_host(root,require_images=False)
        go=c.read(Path(root)/'assets/retained_identity.json')
        subprocess.run(['docker','image','load','--input',str(Path(root)/'assets/service-image.tar')],check=True,timeout=180)
        image=json.loads(c.command(['docker','image','inspect',go['image']]))[0]
        c.require(image['Id']==go['image'],'Go retained image identity changed')
        archive=Path(root)/'assets/nginx/runtime.tar'
        manifest=c.read(Path(root)/'assets/nginx/manifest.json')
        c.require(c.sha(archive)==manifest['runtime_tar_sha256'],'NGINX runtime archive changed')
        # Import the exact sealed filesystem. Docker creates a fresh image
        # metadata identity; original immutable image ID is retained provenance.
        nginx=c.command(['docker','import','--change','ENTRYPOINT ["/gate", "--server"]',str(archive)],timeout=180)
        software=state/'nginx';software.mkdir()
        for name in ('client','manifest.json'):shutil.copy2(Path(root)/'assets/nginx'/name,software/name)
        c.write(software/'image.json',dict(id=nginx,original_image_id=package['original_nginx_image'],
            runtime_tar_sha256=c.sha(archive),fresh_import_metadata=True))
        value=dict(package_seal_sha256=c.sha(Path(root)/'runtime_seal.json'),go_image=go['image'],
            nginx_image=nginx,host_check=check,created_ns=time.monotonic_ns(),
            setup_elapsed_sec=(time.monotonic_ns()-started)/1e9,setup_is_offline_engineering_cost=False,
            setup_is_external_image_preparation=True,no_traffic_started=True)
        c.write(state/'setup.json',value)
        c.verify_setup(root,state)
    except BaseException as exc:
        c.write(state/'failure.json',dict(error=str(exc),elapsed_sec=(time.monotonic_ns()-started)/1e9));raise


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['verify-package','check','setup'])
    args=p.parse_args()
    if args.command=='verify-package':c.verify_package(ROOT);print('Portable package verifies; runtime qualification and allocation confirmation remain pending.')
    elif args.command=='check':print(json.dumps(c.check_host(ROOT),indent=2))
    else:setup(ROOT)
