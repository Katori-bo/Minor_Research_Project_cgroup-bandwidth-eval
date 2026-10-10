#!/usr/bin/env python3
"""Download, checksum and restore the archived portion of the research snapshot."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def check_original_files(manifest):
    missing, changed = [], []
    for name, expected in manifest['original_files'].items():
        path = ROOT / name
        if not path.exists() and not path.is_symlink():
            missing.append(name)
        elif 'symlink' in expected:
            if not path.is_symlink() or str(path.readlink()) != expected['symlink']:
                changed.append(name)
        elif path.is_symlink() or path.stat().st_size != expected['size'] or sha256(path) != expected['sha256']:
            changed.append(name)
    if missing or changed:
        for name in missing[:10]: print('Missing:', name)
        for name in changed[:10]: print('Changed:', name)
        raise SystemExit(f'Inventory mismatch: {len(missing)} missing, {len(changed)} changed.')
    print(f'Verified all {len(manifest["original_files"])} original file identities.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify', action='store_true', help='Only verify the restored file inventory; no network access.')
    parser.add_argument('--download-only', action='store_true', help='Download and verify assets without extracting.')
    parser.add_argument('--assets-dir', type=Path, default=ROOT / 'publication/downloads')
    args = parser.parse_args()
    manifest = json.loads((ROOT / 'publication/snapshot-manifest.json').read_text())
    if args.verify:
        check_original_files(manifest)
        return
    if not args.download_only and (not shutil.which('tar') or not shutil.which('zstd')):
        raise SystemExit('Restoration requires tar and zstd. Install them before downloading.')
    args.assets_dir.mkdir(parents=True, exist_ok=True)
    base = f'https://github.com/{manifest["repository"]}/releases/download/{manifest["release_tag"]}/'
    for asset in manifest['assets']:
        path = args.assets_dir / asset['name']
        if path.exists() and path.stat().st_size == asset['size'] and sha256(path) == asset['sha256']:
            print('Already verified:', path.name, flush=True)
            continue
        if path.exists():
            raise SystemExit(f'Existing asset has the wrong identity: {path}. Move it aside before retrying.')
        temporary = path.with_name(path.name + '.partial')
        print(f'Downloading {path.name} ({asset["size"] / 1024**2:.1f} MiB)', flush=True)
        with urllib.request.urlopen(base + asset['name'], timeout=120) as response, temporary.open('wb') as dest:
            shutil.copyfileobj(response, dest, length=1024 * 1024)
        if temporary.stat().st_size != asset['size'] or sha256(temporary) != asset['sha256']:
            raise SystemExit('Downloaded checksum differs: ' + path.name)
        temporary.rename(path)
        print('SHA256 verified:', path.name, flush=True)
    if args.download_only:
        return
    for group, names in manifest['archive_files'].items():
        existing = [name for name in names if (ROOT / name).exists() or (ROOT / name).is_symlink()]
        if len(existing) == len(names):
            print('Group already present:', group, flush=True)
            continue
        if existing:
            raise SystemExit(f'{group} is partially present. Restore into a fresh clone to avoid overwriting existing records.')
        print('Restoring:', group, flush=True)
        process = subprocess.Popen(['tar', '--zstd', '--extract', '--preserve-permissions', '--keep-old-files', '--file=-', '--directory=' + str(ROOT)], stdin=subprocess.PIPE)
        try:
            for asset in manifest['assets']:
                if asset['group'] == group:
                    with (args.assets_dir / asset['name']).open('rb') as source:
                        shutil.copyfileobj(source, process.stdin, length=1024 * 1024)
        finally:
            process.stdin.close()
        if process.wait() != 0:
            raise SystemExit('Extraction failed: ' + group)
    check_original_files(manifest)


if __name__ == '__main__':
    main()
