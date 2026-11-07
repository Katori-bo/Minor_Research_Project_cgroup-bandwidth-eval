#!/usr/bin/env python3
"""Package complete or partial host02 evidence without starting any workload."""
import datetime
import hashlib
import json
from pathlib import Path
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'diagnostic'))
import v31_common as c


def main():
    c.verify_package()
    attempts = ROOT / 'runs/host02'
    if not attempts.exists():
        raise ValueError('No host02 setup or attempted evidence exists yet')
    for path in attempts.rglob('*owner.json'):
        owner = c.read(path).get('owner')
        if owner and c.same_process(owner):
            raise ValueError('Collection/preparation owner is still running; wait for cleanup before export')
    # Preserve original absolute paths for any later explicit relocation adapter.
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    export = ROOT.parent / ('v31-host02-return-' + stamp)
    export.mkdir(exist_ok=False)
    inventory = {str(p.relative_to(ROOT)): c.digest(p) for p in sorted(ROOT.rglob('*'))
                 if p.is_file() and '__pycache__' not in p.parts}
    if any(p.is_symlink() for p in ROOT.rglob('*')):
        raise ValueError('Symlinks in return evidence require review')
    (export / 'inventory.json').write_text(json.dumps(dict(original_package_root=str(ROOT),
        files_sha256=inventory, complete_or_partial=True), indent=2) + '\n')
    archive = export / 'v31-host02-evidence.tar.gz'
    with tarfile.open(archive, 'w:gz') as out:
        for name in inventory:
            out.add(ROOT / name, arcname=ROOT.name + '/' + name, recursive=False)
    if any(c.digest(ROOT / name) != expected for name, expected in inventory.items()):
        raise ValueError('Evidence changed during export; preserve this directory and review activity')
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    (export / 'v31-host02-evidence.tar.gz.sha256').write_text(digest + '  ' + archive.name + '\n')
    print('Send the entire directory: ' + str(export))
    print('No additional collection started. Partial/interrupted results are retained.')


if __name__ == '__main__':
    main()
