"""Portable identities, package guards and host placement; no import-time I/O."""
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time


def require(condition, message):
    if not condition: raise ValueError(message)


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path): return json.loads(Path(path).read_bytes())


def write(path, value, exclusive=True):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x' if exclusive else 'w') as f:
        json.dump(value,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')
        f.flush();os.fsync(f.fileno())
    fd=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(fd)
    finally:os.close(fd)


def replace(path,value):
    path=Path(path);temporary=path.with_name(path.name+'.'+str(time.monotonic_ns())+'.tmp')
    write(temporary,value);os.replace(temporary,path)
    fd=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(fd)
    finally:os.close(fd)


def identity(pid):
    path=Path('/proc')/str(pid)
    fields=(path/'stat').read_text().rsplit(') ',1)[1].split()
    if fields[0] in ('Z','X'):raise ProcessLookupError(pid)
    return dict(pid=pid,start_ticks=int(fields[19]),uid=path.stat().st_uid,
                boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip())


def same(identity_record, inspect=identity):
    try:
        actual=inspect(identity_record['pid'])
        require('pid' in identity_record and 'start_ticks' in identity_record,'incomplete process ownership')
        return all((str(actual.get(k))==str(v) if k=='start_ticks' else actual.get(k)==v)
                   for k,v in identity_record.items() if k!='state')
    except (FileNotFoundError,ProcessLookupError):return False


def command(argv, timeout=30):
    p=subprocess.run(argv,capture_output=True,text=True,timeout=timeout)
    require(p.returncode==0,repr(argv)+': '+p.stderr[-2000:]);return p.stdout.strip()


def verify_package(root):
    root=Path(root);seal=read(root/'runtime_seal.json')['files_sha256']
    actual={str(p.relative_to(root)) for p in root.rglob('*') if p.is_file() and
            'runs' not in p.relative_to(root).parts and p!=root/'runtime_seal.json' and '__pycache__' not in p.parts}
    require(actual==set(seal),'runtime package file inventory changed')
    for name,h in seal.items():
        path=root/name
        require(not path.is_symlink() and sha(path)==h,'runtime package changed: '+name)
    return read(root/'runtime_package.json')


def placement(host, topology, allowed):
    required=set(host['go_service_cpus'])|set(host['control_cpus'])|set(host['nginx_service_cpus'])
    require(required<=set(allowed),'frozen service/control CPUs unavailable')
    key=lambda cpu:(topology[str(cpu)]['package'],topology[str(cpu)]['core'])
    service=[key(cpu) for cpu in host['go_service_cpus']]
    control=[key(cpu) for cpu in host['control_cpus']]
    require(len(set(service))==len(service) and not set(service)&set(control),
            'service cores overlap each other or control physical cores/SMT siblings')
    # Frozen AMD control CPUs 0,1 are the two siblings of physical core 0.
    # Intel's retained allocation uses two distinct control physical cores.
    if host['id']=='host02':
        require(len(set(control))==len(control),'Intel control physical cores overlap')
    require(set(host['nginx_service_cpus'])<=set(host['go_service_cpus']), 'NGINX placement differs')
    for cpu in required:
        require(cpu in expand_cpu_list(topology[str(cpu)]['siblings']), 'inconsistent sibling inventory')
    return topology


def expand_cpu_list(text):
    result=set()
    for part in text.split(','):
        lo,_,hi=part.partition('-');result.update(range(int(lo),int(hi or lo)+1))
    return result


def topology():
    result={}
    for p in sorted(Path('/sys/devices/system/cpu').glob('cpu[0-9]*')):
        if not (p/'topology').is_dir():continue
        d=p/'topology';result[p.name[3:]]=dict(core=(d/'core_id').read_text().strip(),
            package=(d/'physical_package_id').read_text().strip(),siblings=(d/'thread_siblings_list').read_text().strip())
    return result


def temperatures():
    values={}
    for hw in sorted(Path('/sys/class/hwmon').glob('hwmon*')):
        name=(hw/'name').read_text().strip() if (hw/'name').exists() else ''
        if name not in ('coretemp','k10temp'):continue
        for sensor in hw.glob('temp*_input'):
            label=sensor.with_name(sensor.name.replace('_input','_label'))
            values[name+':'+hw.name+':'+(label.read_text().strip() if label.exists() else sensor.stem)]=int(sensor.read_text())/1000
    require(values,'no readable retained CPU temperature sensors');return values


def baseline():
    return dict(kernel=platform.release(),boot_id=identity(os.getpid())['boot_id'],
                topology={k:v['siblings'] for k,v in topology().items()})


def check_host(root, require_images=True, control_pinned=False):
    package=verify_package(root);host=package['host']
    require(os.geteuid()!=0,'run the campaign as the normal user')
    require(platform.system()=='Linux' and platform.machine()=='x86_64','native Linux x86-64 required')
    marker={'host01':'AMD Ryzen 5 5600H','host02':'Intel(R) Core(TM) i5-10300H'}[host['id']]
    require(marker in Path('/proc/cpuinfo').read_text(),'CPU differs from frozen host allocation')
    allowed=os.sched_getaffinity(0)
    if control_pinned:
        require(allowed==set(host['control_cpus']),'control process affinity changed')
        # Full allowed affinity was checked in this worker before self-pinning;
        # service affinity is checked again by each retained startup/guard.
        placement(host,topology(),set(map(int,topology())))
    else:placement(host,topology(),allowed)
    temperatures()
    detected=subprocess.run(['systemd-detect-virt'],capture_output=True,text=True,timeout=10)
    require(detected.returncode==1 and detected.stdout.strip()=='none','native hardware requirement not established')
    for name in ('docker','taskset','systemd-inhibit','sudo','pgrep','bpftool'):
        import shutil
        require(shutil.which(name),'missing runtime prerequisite: '+name)
    command(['bpftool','version'])
    info=json.loads(command(['docker','info','--format','{{json .}}']))
    require(str(info.get('CgroupVersion'))=='2' and info.get('CgroupDriver')=='systemd' and
        not any('rootless' in x for x in info.get('SecurityOptions',[])), 'rootful Docker cgroup-v2/systemd required')
    context=json.loads(command(['docker','context','inspect']))[0]
    endpoint=os.environ.get('DOCKER_HOST') or context['Endpoints']['docker']['Host']
    require(endpoint.startswith('unix://'),'local Docker socket required')
    require({'cpu','cpuset'}<=set(Path('/sys/fs/cgroup/cgroup.controllers').read_text().split()),'cgroup controllers missing')
    require(Path('/sys/kernel/tracing').is_dir(),'tracefs unavailable for retained read-only inventory')
    require(__import__('shutil').disk_usage(root).free>=20*1024**3,'20 GiB free required')
    from environment_controls import power_settings
    power=power_settings(include_profile=True)
    require(power['external_power'] and any(v=='1' for v in power['external_power'].values()),'readable AC power required')
    require(power.get('desktop_profile') in (None,'balanced'),'recorded balanced power policy required; settings are not changed')
    if require_images:
        setup=Path(root)/'runs'/host['id']/'setup'
        verify_setup(root,setup)
    return dict(host=host['id'],baseline=baseline(),power=power,topology=topology(),allowed_cpus=sorted(allowed),
                temperatures_c=temperatures(),docker=info['ServerVersion'],collection_started=False)


def verify_setup(root, setup):
    require(not (Path(setup)/'failure.json').exists(),'setup attempt failed; preserve it without reuse')
    value=read(Path(setup)/'setup.json')
    require(value['package_seal_sha256']==sha(Path(root)/'runtime_seal.json'),'setup belongs to another package')
    for app,key in [('Go','go_image'),('NGINX','nginx_image')]:
        image=json.loads(command(['docker','image','inspect',value[key]]))[0]
        require(image['Id']==value[key] and image['Architecture']=='amd64' and image['Os']=='linux',app+' image/platform changed')
    return value
