"""Fixed stock-NGINX screening contract and immutable preparation inputs."""
from pathlib import Path
import os
import gzip_qualify as prior

ROOT = prior.ROOT
BASE = ROOT / 'analysis/runtime_io_nginx_feasibility/generation-01'
SOFTWARE = BASE / 'software'
SOURCE = SOFTWARE / 'source/nginx-1.30.5'
PLAN = ROOT / 'docs/runtime_io_nginx_feasibility_plan_20261009.md'
SOURCE_SHA = '6c20565aa2325cb82216ae804f4a4ff1875179014759a381c42ddc8e11c4906d'
INPUT_SHA = 'befb815ea245bd525f5e686b3507deab15819b7a43b5751a17d6e19396ae5625'
SIGNER = 'D6786CE303D9A9022998DC6CC8464D549AF75C0A'
LIMITS = dict(prior.LIMITS)
PROTOCOL = dict(candidate='stock-nginx-1.30.5-dynamic-gzip-generation-01',
    version='1.30.5', source_sha256=SOURCE_SHA, input_sha256=INPUT_SHA,
    input_bytes=1048576, compression_level=6, application_user=f'{os.getuid()}:{os.getgid()}',
    limits=LIMITS, processes=2, threads_each=1, endpoint='/compress',
    rate=5, interval_ns=200000000, warmup_offers=25, measurement_offers=200,
    client_inflight_cap=32, encoded_body_cap=2097152, decoded_body_cap=2097152,
    preparation_services=1, preparation_measurement_offers=25, preparation_direct_checks=2,
    preparation_total_sec=300, pilot_services=3, total_sec=600, cleanup_reserve_sec=120,
    active_service_sec=120, settling_sec=10, dispatch_p99_ns=2000000, dispatch_max_ns=10000000,
    measurement_throttled_periods=0, retries=0, service_timing_patch=False,
    scientific_collection=False, ready_for_scientific_collection=False,
    queue_domain='Not measured/equivalent: do not assert the V31 FIFO queue domain.',
    intended_question='Fresh complete-response CDF transfer, including all waiting; new scientific design required.')
FILES = ('diagnostic/nginx_common.py', 'diagnostic/nginx_prepare.py',
    'diagnostic/nginx_qualify.py', 'diagnostic/test_nginx_qualification.py',
    'diagnostic/nginx_client/main.go', 'diagnostic/nginx_client/go.mod',
    'diagnostic/start_nginx_qualification.sh', 'docs/runtime_io_nginx_feasibility_plan_20261009.md')
sha, read, save, require = prior.sha, prior.read, prior.save, prior.require
exclusive_save = prior.selection.save


def source_hashes():
    return {name: sha(ROOT / name) for name in FILES}


def inputs():
    prior.verify(False)
    require(sha(SOFTWARE / 'nginx-1.30.5.tar.gz') == SOURCE_SHA, 'NGINX archive changed')
    require(sha(BASE / 'input/corpus.ndjson') == INPUT_SHA, 'NGINX input changed')
    manifest = read(SOFTWARE / 'manifest.json')
    for name, digest in manifest['pristine_source_sha256'].items():
        require(sha(SOURCE / name) == digest, 'Upstream source changed: ' + name)
    require(read(BASE / 'protocol.json') == PROTOCOL, 'NGINX protocol changed')


def verify(boot=True):
    inputs()
    sealed = read(BASE / 'bundle-seal.json')
    require(sealed['protocol'] == PROTOCOL, 'NGINX sealed protocol changed')
    if boot: require(sealed['baseline'] == prior.helpers.common.baseline(), 'NGINX host boot changed')
    for name, digest in sealed['files_sha256'].items():
        require(sha(ROOT / name) == digest, 'NGINX sealed input changed: ' + name)
