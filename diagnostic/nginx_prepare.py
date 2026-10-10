#!/usr/bin/env python3
"""Build unchanged NGINX and seal full-path preparation; no scientific run."""
import argparse
import ctypes
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import tarfile
import tempfile

import nginx_common as n


CONFIG = '''daemon off;
master_process on;
worker_processes 1;
pid /tmp/nginx.pid;
error_log stderr notice;
events { worker_connections 128; use epoll; multi_accept off; accept_mutex off; }
http {
    access_log off;
    sendfile off;
    aio off;
    keepalive_timeout 0;
    client_header_timeout 10s;
    client_body_timeout 10s;
    send_timeout 10s;
    server {
        listen 8080;
        location = /health { stub_status; gzip off; }
        location = /compress {
            alias /input/corpus.ndjson;
            default_type application/x-ndjson;
            gzip on;
            gzip_comp_level 6;
            gzip_min_length 20;
            gzip_types application/x-ndjson;
            add_header X-Request-ID $http_x_request_id always;
        }
        location / { deny all; }
    }
}
'''


def build():
    n.prior.verify(False)
    n.require(n.sha(n.SOFTWARE / 'nginx-1.30.5.tar.gz') == n.SOURCE_SHA, 'Archive differs')
    signature = subprocess.run(['gpgv', '--keyring', str(n.SOFTWARE / 'gnupg/pubring.kbx'),
        '--status-fd', '1', str(n.SOFTWARE / 'nginx-1.30.5.tar.gz.asc'),
        str(n.SOFTWARE / 'nginx-1.30.5.tar.gz')], capture_output=True, text=True, timeout=15)
    n.require(signature.returncode == 0 and '[GNUPG:] VALIDSIG ' + n.SIGNER + ' ' in signature.stdout,
              'NGINX signature invalid')
    (n.SOFTWARE / 'signature-verified.log').write_text(signature.stdout + signature.stderr)
    n.exclusive_save(n.BASE / 'protocol.json', n.PROTOCOL)
    shutil.copy2(n.prior.selection.BASE / 'input/corpus.ndjson', n.BASE / 'input/corpus.ndjson')
    pristine = {}
    with tarfile.open(n.SOFTWARE / 'nginx-1.30.5.tar.gz') as archive:
        for member in archive.getmembers():
            if member.isfile():
                name = str(Path(member.name).relative_to('nginx-1.30.5'))
                n.require(n.sha(n.SOURCE / name) == n.prior.hashlib.sha256(archive.extractfile(member).read()).hexdigest(),
                          'Extracted upstream file differs')
                pristine[name] = n.sha(n.SOURCE / name)
    os.sched_setaffinity(0, {0, 1})
    commands = []
    env = dict(os.environ, LANG='C', LC_ALL='C', TZ='UTC')
    flags = ['--prefix=/application', '--conf-path=/application/nginx.conf',
        '--pid-path=/tmp/nginx.pid', '--lock-path=/tmp/nginx.lock', '--error-log-path=stderr',
        '--http-log-path=/tmp/access.log', '--http-client-body-temp-path=/tmp/client_body',
        '--http-proxy-temp-path=/tmp/proxy', '--http-fastcgi-temp-path=/tmp/fastcgi',
        '--http-uwsgi-temp-path=/tmp/uwsgi', '--http-scgi-temp-path=/tmp/scgi',
        '--without-http_rewrite_module', '--without-http_auth_basic_module',
        '--without-http-cache', '--with-http_stub_status_module']
    with (n.SOFTWARE / 'build.log').open('x') as log:
        for argv in (['./configure', *flags], ['make', '-j2']):
            commands.append(argv)
            subprocess.run(argv, cwd=n.SOURCE, env=env, check=True, stdout=log, stderr=subprocess.STDOUT, timeout=180)
        shutil.copy2(n.SOURCE / 'objs/nginx', n.SOFTWARE / 'nginx')
        argv = ['gcc', '-O2', '-static', str(n.ROOT / 'diagnostic/nginx_start_gate.c'), '-o', str(n.SOFTWARE / 'gate')]
        commands.append(argv); subprocess.run(argv, check=True, stdout=log, stderr=subprocess.STDOUT, timeout=60)
        go = n.ROOT / 'analysis/runtime_io_imgproxy_feasibility/generation-01/software/toolchain/go/bin/go'
        goenv = dict(env, GOTOOLCHAIN='local', GOENV='off', CGO_ENABLED='0', GOPROXY='off',
                     GOSUMDB='off', GOCACHE='/tmp/nginx-build-cache', GOMAXPROCS='2')
        subprocess.run([str(go), 'fmt', '.'], cwd=n.ROOT / 'diagnostic/nginx_client', env=goenv,
                       check=True, stdout=log, stderr=subprocess.STDOUT, timeout=30)
        for operation in ('build', 'vet'):
            argv = [str(go), operation]
            if operation == 'build': argv += ['-trimpath', '-o', str(n.SOFTWARE / 'client')]
            argv += ['.']; commands.append(argv)
            subprocess.run(argv, cwd=n.ROOT / 'diagnostic/nginx_client', env=goenv,
                           check=True, stdout=log, stderr=subprocess.STDOUT, timeout=120)
    for name, digest in pristine.items(): n.require(n.sha(n.SOURCE / name) == digest, 'Build changed upstream source')
    (n.SOFTWARE / 'compiler.txt').write_text(subprocess.check_output(['gcc', '--version'], text=True))
    version = subprocess.run([str(n.SOFTWARE / 'nginx'), '-V'], capture_output=True, text=True, check=True).stderr
    (n.SOFTWARE / 'version.txt').write_text(version)
    finish(commands, flags, pristine, version)


def finish(commands=None, flags=None, pristine=None, version=None):
    # Packaging may finish an already compiled build; no services or workloads
    # are rerun. NGINX -V does not report its dynamic zlib version.
    n.require(not (n.BASE / 'bundle-seal.json').exists(), 'Sealed NGINX build cannot be changed')
    if version is None:
        version = (n.SOFTWARE / 'version.txt').read_text()
        flags = shlex.split(version.split('configure arguments: ', 1)[1].strip())
        pristine = {}
        with tarfile.open(n.SOFTWARE / 'nginx-1.30.5.tar.gz') as archive:
            for member in archive.getmembers():
                if member.isfile():
                    name = str(Path(member.name).relative_to('nginx-1.30.5'))
                    digest = n.prior.hashlib.sha256(archive.extractfile(member).read()).hexdigest()
                    n.require(n.sha(n.SOURCE / name) == digest, 'Pristine source differs during packaging')
                    pristine[name] = digest
        commands = [['./configure', *flags], ['make', '-j2']]
    library = ctypes.CDLL('/usr/lib/libz.so.1')
    library.zlibVersion.restype = ctypes.c_char_p
    zlib_version = library.zlibVersion().decode('ascii')
    n.require('nginx/1.30.5' in version and zlib_version == '1.3.2', 'Built version/runtime zlib differs')
    modules = (n.SOURCE / 'objs/ngx_modules.c').read_text()
    n.require('ngx_http_gzip_filter_module' in modules and 'ngx_http_stub_status_module' in modules and
              'ngx_http_gzip_static_module' not in modules, 'Dynamic gzip/stub module set differs')
    dynamic = subprocess.check_output(['readelf', '-d', str(n.SOFTWARE / 'nginx')], text=True)
    needed = re.findall(r'\(NEEDED\).*?\[(.*?)\]', dynamic)
    n.require(set(needed) == {'libz.so.1', 'libc.so.6'}, 'Unexpected NGINX dynamic closure: ' + str(needed))
    runtime = n.SOFTWARE / 'runtime'; runtime.mkdir(exist_ok=True)
    for folder in ('application', 'input', 'usr/lib', 'lib64'): (runtime / folder).mkdir(parents=True, exist_ok=True)
    shutil.copy2(n.SOFTWARE / 'nginx', runtime / 'server')
    shutil.copy2(n.SOFTWARE / 'gate', runtime / 'gate')
    shutil.copy2(n.BASE / 'input/corpus.ndjson', runtime / 'input/corpus.ndjson')
    (runtime / 'application/nginx.conf').write_text(CONFIG)
    syntax_check()
    for destination, origin in [('usr/lib/libz.so.1', '/usr/lib/libz.so.1'),
        ('usr/lib/libc.so.6', '/usr/lib/libc.so.6'), ('lib64/ld-linux-x86-64.so.2', '/usr/lib64/ld-linux-x86-64.so.2')]:
        shutil.copy2(Path(origin).resolve(), runtime / destination)
    tarpath = n.SOFTWARE / 'runtime.tar'
    with tarfile.open(tarpath, 'x') as tar:
        for child in sorted(runtime.iterdir()): tar.add(child, arcname=child.name)
    n.exclusive_save(n.SOFTWARE / 'manifest.json', dict(commands=commands, configure_flags=flags,
        nginx_sha256=n.sha(n.SOFTWARE / 'nginx'), client_sha256=n.sha(n.SOFTWARE / 'client'),
        gate_sha256=n.sha(n.SOFTWARE / 'gate'), runtime_tar_sha256=n.sha(tarpath),
        runtime_files_sha256={str(p.relative_to(runtime)): n.sha(p) for p in runtime.rglob('*') if p.is_file()},
        pristine_source_sha256=pristine, dynamic_dependencies=needed,
        signature_fingerprint=n.SIGNER, source_archive_sha256=n.SOURCE_SHA, runtime_zlib_version=zlib_version,
        scientific_collection=False))
    print('Unchanged signed NGINX, stock dynamic compression runtime and full-body client built.')


def syntax_check():
    # Same directive/module set; only host-visible diagnostic paths change.
    with tempfile.TemporaryDirectory(prefix='research-nginx-syntax-') as name:
        directory = Path(name)
        config = (n.SOFTWARE / 'runtime/application/nginx.conf').read_text()
        config = config.replace('pid /tmp/nginx.pid;', f'pid {directory}/nginx.pid;')
        paths = '\n'.join(f'{kind}_temp_path {directory}/{kind};' for kind in
                          ('client_body', 'proxy', 'fastcgi', 'uwsgi', 'scgi'))
        config = config.replace('http {', 'http {\n' + paths)
        (directory / 'nginx.conf').write_text(config)
        p = subprocess.run([str(n.SOFTWARE / 'nginx'), '-t', '-p', str(directory) + '/',
            '-c', str(directory / 'nginx.conf'), '-e', 'stderr'], capture_output=True, text=True, timeout=15)
        n.save(n.SOFTWARE / 'configuration-check.json', dict(returncode=p.returncode, stdout=p.stdout, stderr=p.stderr,
            config_sha256=n.sha(n.SOFTWARE / 'runtime/application/nginx.conf'), diagnostic_config=config,
            service_started=False))
        n.require(p.returncode == 0, 'Stock NGINX configuration invalid: ' + p.stderr)


def package():
    n.inputs()
    result = subprocess.check_output(['docker', 'import', '--change', 'ENTRYPOINT ["/gate", "--server"]',
        str(n.SOFTWARE / 'runtime.tar'), 'research-nginx-feasibility:generation-02'], text=True, timeout=60).strip()
    n.require(result.startswith('sha256:'), 'NGINX immutable image missing')
    n.exclusive_save(n.SOFTWARE / 'image.json', dict(id=result))
    print('Stock NGINX immutable image packaged.')


def seal():
    n.inputs()
    import nginx_qualify as q
    summary = n.read(n.BASE / 'functional/summary.json')
    n.require(summary['functional_pass'], 'NGINX preparation incomplete')
    q.identity(n.BASE / 'functional/case')
    n.require(q.analyze(n.BASE / 'functional/case', 25, False) == summary['result'], 'NGINX preparation replay differs')
    log = (n.BASE / 'tests.log').read_text()
    n.require(log.rstrip().endswith('OK'), 'NGINX failure tests missing')
    paths = [n.ROOT / name for name in n.FILES]
    paths += [n.BASE / 'protocol.json', n.BASE / 'tests.log', n.BASE / 'source-review.json',
              n.prior.BASE / 'bundle-seal.json']
    paths += [p for parent in (n.SOFTWARE, n.BASE / 'input', n.BASE / 'functional')
              for p in parent.rglob('*') if p.is_file()]
    n.exclusive_save(n.BASE / 'bundle-seal.json', dict(protocol=n.PROTOCOL,
        baseline=n.prior.helpers.common.baseline(), files_sha256={str(p.relative_to(n.ROOT)): n.sha(p) for p in sorted(paths)}))
    print('Stock NGINX source/runtime/measurement contract and full-path preparation sealed.')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('phase', choices=('build', 'finish', 'package', 'seal', 'verify'))
    args = p.parse_args()
    if args.phase == 'verify': n.verify()
    else: globals()[args.phase]()
