# Stock NGINX compression: fresh feasibility contract

Date: 2026-10-09. Engineering qualification only; scientific calibration and
held-out prediction are unstarted. The imgproxy and gzip attempts remain failed
under their original rules. No queue threshold is changed in those studies.

Active preparation generation: 02. Generation 01 stopped before any HTTP workload
because its minimal build disabled the rewrite module while its default location
used that module's return directive. An offline configuration check reproduces
the invalid directive. The complete abort, owned cleanup and original source
snapshots are preserved in generation-01. Generation 02 denies the unused default
location with the available access module, requires a syntax/module check before
startup, and captures owned container state/logs before cleanup. Its dedicated
startup barrier passes -e stderr to the unchanged NGINX executable. Application
binary, zlib, input, compression level, resource limits and traffic stay identical.
This repairs apparatus before any performance experiment, not a replacement
scientific trial. Evidence is analysis/runtime_io_nginx_feasibility/generation-02/.

## Selection and changed scientific question

Pin official stable NGINX 1.30.5, source archive SHA256
6c20565aa2325cb82216ae804f4a4ff1875179014759a381c42ddc8e11c4906d.
Verify its detached release signature against the official maintainer key with
fingerprint D6786CE303D9A9022998DC6CC8464D549AF75C0A. Build source unchanged,
using installed zlib 1.3.2 and pinned actual compiler/runtime hashes. Install
only in this evidence tree and package an isolated scratch runtime; do not edit
host NGINX or system configuration. No service timing or model advantage selects
the version, file size, compression level or traffic rate.

Operation: built-in dynamic gzip compression, level 6, of the exact previously
declared 1 MiB NDJSON corpus (input SHA256
befb815ea245bd525f5e686b3507deab15819b7a43b5751a17d6e19396ae5625).
The HTTP application and compression path are upstream NGINX, with configuration
only. No custom HTTP service, response cache, precompressed file, proxy, Lua/njs
workload, service timing patch, TLS, thread pool or asynchronous file I/O.
Warm input page cache is allowed; dynamic compression still runs per response.

NGINX's single event-loop worker can have several unfinished requests. Gzip and
write filters can yield NGX_AGAIN. Therefore a single worker does not prove
whole-request FIFO serialization and supplies no equivalent of our enqueue-to-
worker-acquisition interval. Do not assign this absent measurement zero or assert
the old 100 us/99% scientific domain. No periodic-plus-residual or paired-worker
comparison can be imported unchanged.

The later possible question is whether a freshly calibrated *complete response*
CDF predicts deadline outcomes at previously unused steady rates in this stock
application. All dispatch, server/event-loop waiting, compression, output and
network time stay in the response. This is a newly scoped response-CDF transfer
study, not exact V31 paired-stage/comparator replication. It requires a separate
sealed scientific design after this engineering check, including fresh capacity,
calibration, deadlines, forecasts, uncertainty, and overload controls. No existing
CDF, service-time decomposition, forecast or capacity is imported.

## Bounded apparatus

One foreground master and one worker, actual single-thread state and stable
PID/start-tick identities; both on logical CPU 2. Whole-service cgroup includes
both processes: quota 25 ms/100 ms, burst 0, memory 512 MiB, pids 128. Client and
supervisor use CPUs 0,1. Read-only runtime; ephemeral writable /tmp only. Fresh
owned container/namespace per trial, immutable image/executable checks, startup
FIFO barrier, uncapped ancestors, unshifted time namespace and procfs guards.
Owner-death/120-second service watchdog removes only the nonce-owned immutable
container and its namespace, and stops only the owned client process group.

Use an independent bounded Go client with integer open-loop spacing 200,000,000
ns (5 requests/s), 32 maximum in flight and 10-second timeout. Send HTTP GET with
Accept-Encoding:gzip and unique X-Request-ID. Disable automatic decompression.
Read the full encoded body before the completion timestamp; then validate gzip
checksum, capped decompression and decoded input hash. Keep encoded hash/size and
both decoded/hash/error records. Cap encoded and decoded bodies at 2 MiB each;
at most 1,000 offers per client invocation. Missing/dropped offers remain present.

The stock stub_status endpoint confirms drain: Reading=0, Writing=1 (the control
request itself), Waiting=0. Its request-count increment must equal the measured
offer count plus the retained post-measurement control requests. CPU counters
begin after the pre-measurement status and end after this common drain check.
This includes common control/connection-close service work. No HTTP polling runs
during workload collection; runtime guards use procfs. Access logging is off.
There is no added service recorder to compare against a reference binary. This
does not prove the client/control apparatus has zero interference.

## Preparation and external suitability checks

Before external launch, allow exactly one real preparation service, without
replacement: two direct compression/decoded-output checks, 25 warmup and 25
diagnostic offers at 5 requests/s. Exercise the actual pre/post process scans,
counter windows, stub-status conservation, full-body client validation, raw
classification, cleanup and offline replay. Preparation with Codex open records
domain exits as diagnostics and does not qualify performance. Technical identity,
body, client, counter or cleanup errors stop preparation. Preparation total cap
300 seconds, including 120 seconds cleanup reserve; active service 120 seconds.

After sources/runtime/input/preparation are sealed, run exactly three fresh
stock cohorts, with 10 seconds settling, 25 warmup and 200 measurement offers per
cohort, at the fixed 5 requests/s. No retries, resume, replacements or rate/size
searches. Total cap 600 seconds including 120 cleanup reserve; each service 120
seconds maximum. Expected normal path about three minutes, not a power study.
Require all complete matching decoded bodies, gzip Content-Encoding and echoed
IDs, dispatch p99 <=2 ms/max <=10 ms, zero measurement throttled periods, stable
source/image/config/process/thread/resource identities, exact request accounting
and verified cleanup. Export/save raw records and counters before classification;
seal all attempted evidence on success or failure. Preserve warmup/startup
throttling separately. Report response-window overlaps descriptively; they are
not server queue measurements or substitutes for the old 100 us criterion.

Success means only stock_full_response_measurement_qualified. No observer-cost
claim, low-queue guarantee, CDF accuracy, comparator advantage, application-transfer
confirmation, independent host/team replication or novelty follows. Scientific
collection stays disabled pending its separately justified prospective design.

Primary sources: https://nginx.org/en/download.html;
https://nginx.org/en/pgp_keys.html;
https://nginx.org/en/docs/http/ngx_http_gzip_module.html;
https://nginx.org/en/docs/http/ngx_http_stub_status_module.html;
https://nginx.org/en/docs/dev/development_guide.html.
