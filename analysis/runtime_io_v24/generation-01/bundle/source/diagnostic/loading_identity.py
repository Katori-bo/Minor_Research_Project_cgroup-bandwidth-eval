"""Same startup qualification in all arms; executable identity, not request tracing."""
import json
from pathlib import Path
import run


def identity(path):
    s = path.stat()
    return dict(sha256=run.sha(path), device=s.st_dev, inode=s.st_ino, size=s.st_size,
                mode=s.st_mode, uid=s.st_uid, gid=s.st_gid)


def mount_arguments(assets, mode):
    if mode not in ('packaged', 'shared'):
        raise ValueError('unknown loading mode')
    args = ['--mount', f'type=bind,src={assets},dst=/qualification,readonly']
    if mode == 'shared':
        args += ['--mount', f'type=bind,src={assets / "shared.server"},dst=/server,readonly']
    return args


def validate(evidence, mode, assets, server_sha, probe_sha):
    if mode not in ('packaged', 'shared'):
        raise ValueError('unknown loading mode')
    expected = {'/qualification': str(assets)}
    if mode == 'shared': expected['/server'] = str(assets / 'shared.server')
    mounts = evidence['mounts']
    if len(mounts) != len(expected) or {m['Destination']: m['Source'] for m in mounts} != expected or any(
            m['Type'] != 'bind' or m['RW'] or m['Propagation'] != 'rprivate' for m in mounts):
        raise ValueError('actual mount configuration differs')
    probe = evidence['probe']
    if probe['target_executable']['sha256'] != server_sha or probe['probe_executable']['sha256'] != probe_sha:
        raise ValueError('actual process executable hash differs')
    if probe['probe_executable'] != evidence['host_probe_identity']:
        raise ValueError('probe is not the frozen host file')
    if evidence['host_shared_identity']['sha256'] != server_sha:
        raise ValueError('shared file hash differs')
    if mode == 'shared' and probe['target_executable'] != evidence['host_shared_identity']:
        raise ValueError('running server is not the exact common file')
    if evidence['loading_mode'] != mode or evidence['image_id'] != evidence['expected_image_id']:
        raise ValueError('loading mode or image differs')


def collect(container, assets, mode, expected_image, server_sha, probe_sha):
    inspect = json.loads(run.capture(['docker', 'inspect', container]))[0]
    probe = json.loads(run.capture(['docker', 'exec', container, '/qualification/probe']))
    value = dict(loading_mode=mode, image_id=inspect['Image'], expected_image_id=expected_image,
        mounts=inspect['Mounts'], probe=probe, host_shared_identity=identity(assets / 'shared.server'),
        host_probe_identity=identity(assets / 'probe'), collection='startup_before_warmup',
        limitation='Startup executable provenance only; no runnable-readiness or request-level kernel observation.')
    validate(value, mode, assets, server_sha, probe_sha)
    return value
