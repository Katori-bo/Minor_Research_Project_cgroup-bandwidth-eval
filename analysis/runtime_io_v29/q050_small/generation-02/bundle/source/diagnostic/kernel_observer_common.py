"""Frozen V18 cost protocol and evidence utilities (standard library only)."""
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import shutil
import socket
import struct
import tempfile

ROOT = Path(__file__).resolve().parents[1]
PARENT = ROOT / 'analysis/runtime_io_v18_observer_cost'
BASE = ROOT / 'analysis/runtime_io_v16_repeatability_build'
BRIDGE_ASSETS = ROOT / 'analysis/runtime_io_v18_service_bridge_assets'
BRIDGE = ROOT / 'analysis/runtime_io_v18_service_bridge/20261004T142940Z-97399'
RAW_LIMIT = 1024**3
FREE_MIN = 20 * 1024**3
CAPTURE_SEC = 300
WATCHDOG_SEC = 360
WORKLOAD = dict(gomaxprocs=1, workers=4, queue=128, iterations=44000,
    cpus=[2, 4], quota_us=50000, period_us=100000, burst_us=0,
    warmup_sec=20, duration_sec=60, rate=113.21, burst_low=56.605,
    burst_high=169.815, burst_period_sec=10, concurrency=512, timeout_sec=5,
    memory=0, memory_swap=0, pids_limit=0)


def service_argv(image, qualification, name):
    # Preserve the historical omission of memory/PID overrides. Systemd/Docker
    # may still supply a finite default; preparation freezes its observed value.
    return ['docker','create','--name',name,'--cpuset-cpus','2,4',
            '--cpu-period','100000','--cpu-quota','50000',
            '--mount',f'type=bind,src={qualification},dst=/qualification,readonly',
            '--entrypoint','/qualification/gate','-e','GOMAXPROCS=1','-e','WORKERS=4',
            '-e','QUEUE_SIZE=128','-e','INSTRUMENT=1','-p','127.0.0.1::8080',image,'--server']


def validate_resources(limits, host, baseline):
    cpu={'cpu.max':'50000 100000','cpu.max.burst':'0','cpuset.cpus.effective':'2,4'}
    observed_host={k:host.get(k) for k in ('Memory','MemorySwap','PidsLimit')}
    if any(limits.get(k)!=v for k,v in cpu.items()): raise ValueError('CPU limits differ: '+json.dumps(limits))
    if baseline['host_config']['Memory']!=0 or baseline['host_config']['MemorySwap']!=0:
        raise ValueError('preparation imported extra memory limits')
    if limits!=baseline['limits'] or observed_host!=baseline['host_config']:
        raise ValueError('resource defaults differ from frozen preparation: '+json.dumps(dict(
            actual_limits=limits,expected_limits=baseline['limits'],actual_host=observed_host,expected_host=baseline['host_config'])))


def matrix():
    return [dict(pair=p, arm=a, order=2*(p-1)+i+1,
                 trial=f'p{p}_{a}', **WORKLOAD)
            for p in range(1, 7)
            for i, a in enumerate(('off', 'on') if p % 2 else ('on', 'off'))]


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024**2), b''): h.update(block)
    return h.hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name+'.', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as f:
            json.dump(value, f, indent=2, allow_nan=False); f.write('\n'); f.flush(); os.fsync(f.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary): os.unlink(temporary)


def files(directory, exclude=('seal.json',)):
    result = {}
    for p in sorted(Path(directory).rglob('*')):
        if p.is_symlink(): raise ValueError('symlink in evidence: '+str(p))
        if p.is_file() and str(p.relative_to(directory)) not in exclude:
            result[str(p.relative_to(directory))] = digest(p)
    return result


def seal(directory):
    save(Path(directory)/'seal.json', dict(files_sha256=files(directory)))


def verify_seal(directory, name='seal.json'):
    if read(Path(directory)/name)['files_sha256'] != files(directory, (name,)):
        raise ValueError('evidence seal mismatch: '+str(directory))


def source_hashes():
    paths = list((ROOT/'diagnostic').glob('*.py'))
    paths += list((ROOT/'diagnostic').glob('kernel*.bt'))
    paths += [ROOT/'diagnostic/kernel_start_gate.c', ROOT/'diagnostic/start_kernel_observer_cost.sh',
              ROOT/'docs/runtime_io_v18_observer_cost.md']
    paths += list((ROOT/'scripts').glob('*.py'))
    return {str(p.relative_to(ROOT)): digest(p) for p in sorted(paths)}


def owned_directory(value):
    path = Path(value).absolute()
    if path.parent != PARENT or path.is_symlink() or path.resolve() != path:
        raise ValueError('use a direct dedicated observer-cost directory')
    return path


def arrivals(seconds=60):
    offsets = []; i = 0
    while True:
        cycle = math.floor(i / (5*(56.605+169.815)))
        within = i - cycle*(5*(56.605+169.815))
        offset = cycle*10 + (within/56.605 if within < 5*56.605 else 5+(within-5*56.605)/169.815)
        stamp = math.floor(offset*1e9+.5)
        if stamp >= seconds*1e9: return offsets
        offsets.append(stamp); i += 1


def arrival_vector(client, seconds=60):
    requests = sorted(client['requests'], key=lambda q: q['ID'])
    if [q['ID'] for q in requests] != list(range(client['total_scheduled'])):
        raise ValueError('offered request identity/count mismatch')
    vector = [q['ScheduledOffsetNs'] for q in requests]
    if vector != arrivals(seconds): raise ValueError('relative arrival vector differs from frozen workload')
    return vector


def capacity(directory):
    if shutil.disk_usage(directory).free < FREE_MIN: raise ValueError('20 GiB free required')


def baseline():
    return dict(kernel=platform.release(), boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
                topology={str(c): Path(f'/sys/devices/system/cpu/cpu{c}/topology/thread_siblings_list').read_text().strip()
                          for c in (0, 1, 2, 4)})


def send(sock, value):
    data = json.dumps(value, allow_nan=False).encode()
    if len(data) > 65536: raise ValueError('IPC frame too large')
    sock.sendall(struct.pack('!I', len(data))+data)


def receive(sock):
    def exact(n):
        data = bytearray()
        while len(data) < n:
            block = sock.recv(n-len(data))
            if not block: raise EOFError('supervisor IPC disconnected')
            data.extend(block)
        return bytes(data)
    size = struct.unpack('!I', exact(4))[0]
    if not 0 < size <= 65536: raise ValueError('IPC frame size rejected')
    value = json.loads(exact(size))
    if not isinstance(value, dict): raise ValueError('IPC object required')
    return value


class Protocol:
    """No arguments, paths, process IDs, commands or arm overrides are accepted."""
    def __init__(self, count): self.count=count; self.index=0; self.state='idle'

    def accept(self, request):
        if set(request) != {'op'}: raise ValueError('IPC arguments rejected')
        op = request['op']
        allowed = {'idle': {'create', 'finish'}, 'gated': {'release', 'observe', 'end'},
                   'active': {'observe', 'end'}, 'finished': set()}[self.state]
        if op not in allowed: raise ValueError('out-of-order or unknown IPC operation')
        if op == 'create':
            if self.index >= self.count: raise ValueError('frozen trial matrix exhausted')
            self.state='gated'
        elif op == 'release': self.state='active'
        elif op == 'end': self.index+=1; self.state='idle'
        elif op == 'finish':
            if self.index != self.count: raise ValueError('unfinished frozen matrix')
            self.state='finished'
        return op
