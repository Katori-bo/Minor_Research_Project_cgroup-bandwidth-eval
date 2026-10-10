#define _GNU_SOURCE
#include <arpa/inet.h>
#include <errno.h>
#include <fcntl.h>
#include <inttypes.h>
#include <poll.h>
#include <pthread.h>
#include <sched.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/syscall.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

#ifndef OBSERVED
#define OBSERVED 0
#endif
#define CAP 1024
#define QUEUE 128
#define BODY_CAP (2 * 1024 * 1024)
#define JSON_CAP (1024 * 1024)
typedef struct { int fd; char id[65]; int64_t enqueued; } Job;
typedef struct {
    char id[65]; int pid, pidfd_ok, affinity_ok, cgroup_ok, threads_ok;
    unsigned long long ticks;
    int exec_ok, reaped, exit_code, success; size_t bytes;
} Audit;
typedef struct {
    char id[65]; int64_t enqueued, acquired, spawn_before, spawn_after;
    int64_t drained, reaped, response_before, response_after, released;
    int success;
} Event;
static Job queue[QUEUE];
static Audit audits[CAP];
#if OBSERVED
static Event events[CAP];
#endif
static unsigned head, tail, queued, completed, overflow, started;
static int active_pid;
static pthread_mutex_t mu = PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t available = PTHREAD_COND_INITIALIZER;
static unsigned char body[BODY_CAP];
static char exported[JSON_CAP];

static int64_t now_ns(void) {
    struct timespec t;
    if (clock_gettime(CLOCK_MONOTONIC, &t)) _exit(90);
    return (int64_t)t.tv_sec * 1000000000LL + t.tv_nsec;
}
#if OBSERVED
#define STAMP(e, field) ((e)->field = now_ns())
#else
#define STAMP(e, field) ((void)(e))
#endif
static int send_all(int fd, const void *data, size_t len) {
    const unsigned char *p = data;
    while (len) {
        ssize_t n = send(fd, p, len, MSG_NOSIGNAL);
        if (n < 0 && errno == EINTR) continue;
        if (n <= 0) return -1;
        p += n; len -= (size_t)n;
    }
    return 0;
}
static int response(int fd, int status, const char *type, const char *id,
                    const void *data, size_t size, int64_t q, int64_t p, int timings) {
    char headers[1024], extra[256] = "", identity[128] = "";
    if (id) snprintf(identity, sizeof(identity), "X-Request-ID: %s\r\n", id);
    if (timings) snprintf(extra, sizeof(extra),
        "X-Qualification-Queue-Ns: %" PRId64 "\r\nX-Qualification-Process-Ns: %" PRId64 "\r\n", q, p);
    int n = snprintf(headers, sizeof(headers),
        "HTTP/1.1 %d %s\r\nContent-Type: %s\r\nContent-Length: %zu\r\nConnection: close\r\n%s%s\r\n",
        status, status == 200 ? "OK" : "Error", type, size, identity, extra);
    if (n < 0 || (size_t)n >= sizeof(headers) || send_all(fd, headers, (size_t)n)) return -1;
    return send_all(fd, data, size);
}
static int read_file(const char *path, char *out, size_t cap) {
    int fd = open(path, O_RDONLY | O_CLOEXEC);
    if (fd < 0) return -1;
    ssize_t n = read(fd, out, cap - 1);
    close(fd);
    if (n < 0 || (size_t)n == cap - 1) return -1;
    out[n] = 0; return 0;
}
static int child_identity(pid_t pid, Audit *a) {
    char path[128], text[4096], own[4096];
    snprintf(path, sizeof(path), "/proc/%d/stat", pid);
    if (read_file(path, text, sizeof(text))) return -1;
    char *cursor = strrchr(text, ')'), *save = NULL;
    if (!cursor) return -1;
    char *token = strtok_r(cursor + 2, " ", &save);
    for (int field = 3; field < 22 && token; ++field) token = strtok_r(NULL, " ", &save);
    if (!token) return -1;
    a->ticks = strtoull(token, NULL, 10);
    cpu_set_t set;
    CPU_ZERO(&set);
    a->affinity_ok = !sched_getaffinity(pid, sizeof(set), &set) && CPU_COUNT(&set) == 1 && CPU_ISSET(2, &set);
    snprintf(path, sizeof(path), "/proc/%d/cgroup", pid);
    a->cgroup_ok = !read_file(path, text, sizeof(text)) &&
                  !read_file("/proc/self/cgroup", own, sizeof(own)) && !strcmp(text, own);
    snprintf(path, sizeof(path), "/proc/%d/status", pid);
    a->threads_ok = !read_file(path, text, sizeof(text)) && strstr(text, "\nThreads:\t1\n") != NULL;
    return a->ticks && a->affinity_ok && a->cgroup_ok && a->threads_ok ? 0 : -1;
}
static int compress_job(Audit *a, Event *e) {
    int output[2], gate[2], proof[2];
    if (pipe2(output, O_CLOEXEC)) return -1;
    if (pipe2(gate, O_CLOEXEC)) { close(output[0]); close(output[1]); return -1; }
    if (pipe2(proof, O_CLOEXEC)) {
        close(output[0]); close(output[1]); close(gate[0]); close(gate[1]); return -1;
    }
    int64_t deadline = now_ns() + 10000000000LL;
    STAMP(e, spawn_before);
    pid_t pid = fork();
    if (pid == 0) {
        /* After a threaded fork, only async-signal-safe operations until exec. */
        close(output[0]); close(gate[1]); close(proof[0]);
        char token = 0;
        if (read(gate[0], &token, 1) != 1 || token != 'G' || dup2(output[1], STDOUT_FILENO) < 0) _exit(125);
        close(gate[0]); close(output[1]);
        char *argv[] = {"/application/gzip", "-n", "-6", "-c", "--", "/input/corpus.ndjson", NULL};
        char *env[] = {"LANG=C", "LC_ALL=C", "TZ=UTC", NULL};
        execve(argv[0], argv, env);
        int error = errno;
        (void)write(proof[1], &error, sizeof(error));
        _exit(126);
    }
    STAMP(e, spawn_after);
    close(output[1]); close(gate[0]); close(proof[1]);
    if (pid < 0) { close(output[0]); close(gate[1]); close(proof[0]); return -1; }
    a->pid = pid;
    int pidfd = (int)syscall(SYS_pidfd_open, pid, 0);
    a->pidfd_ok = pidfd >= 0;
    pthread_mutex_lock(&mu); active_pid = pid; pthread_mutex_unlock(&mu);
    int ok = pidfd >= 0 && !child_identity(pid, a);
    if (ok && write(gate[1], "G", 1) != 1) ok = 0;
    close(gate[1]);
    fcntl(output[0], F_SETFL, O_NONBLOCK);
    fcntl(proof[0], F_SETFL, O_NONBLOCK);
    size_t used = 0;
    int eof = 0;
    while (ok && !eof) {
        int64_t remaining = deadline - now_ns();
        if (remaining <= 0) { ok = 0; break; }
        struct pollfd poller = {.fd = output[0], .events = POLLIN | POLLHUP};
        int ready = poll(&poller, 1, (int)((remaining + 999999) / 1000000));
        if (ready < 0 && errno == EINTR) continue;
        if (ready <= 0) { ok = 0; break; }
        unsigned char excess;
        ssize_t n = used < BODY_CAP ? read(output[0], body + used, BODY_CAP - used) : read(output[0], &excess, 1);
        if (n < 0 && (errno == EAGAIN || errno == EINTR)) continue;
        if (n < 0 || (n > 0 && used == BODY_CAP)) { ok = 0; break; }
        if (n == 0) eof = 1;
        else used += (size_t)n;
    }
    STAMP(e, drained);
    close(output[0]);
    if (!ok) {
        if (pidfd >= 0) (void)syscall(SYS_pidfd_send_signal, pidfd, SIGKILL, NULL, 0);
        else (void)kill(pid, SIGKILL); /* Unreaped known child: its PID cannot be reused. */
    }
    int status = 0;
    /* Keep the wait bounded even if stdout closed before process exit. */
    pid_t waited;
    for (;;) {
        waited = waitpid(pid, &status, WNOHANG);
        if (waited == pid || (waited < 0 && errno != EINTR)) break;
        if (now_ns() >= deadline) {
            ok = 0;
            if (pidfd >= 0) (void)syscall(SYS_pidfd_send_signal, pidfd, SIGKILL, NULL, 0);
            else (void)kill(pid, SIGKILL);
        }
        if (now_ns() >= deadline + 1000000000LL) break;
        if (pidfd >= 0) {
            struct pollfd exited = {.fd = pidfd, .events = POLLIN};
            int64_t left = deadline + (ok ? 0 : 1000000000LL) - now_ns();
            (void)poll(&exited, 1, left > 0 ? (int)((left + 999999) / 1000000) : 1);
        } else {
            struct timespec pause = {0, 1000000}; nanosleep(&pause, NULL);
        }
    }
    a->reaped = waited == pid;
    a->exit_code = a->reaped && WIFEXITED(status) ? WEXITSTATUS(status) : -1;
    int error;
    a->exec_ok = read(proof[0], &error, sizeof(error)) == 0;
    close(proof[0]);
    if (pidfd >= 0) close(pidfd);
    pthread_mutex_lock(&mu); active_pid = 0; pthread_mutex_unlock(&mu);
    STAMP(e, reaped);
    a->bytes = used;
    return ok && eof && used && a->reaped && a->exit_code == 0 && a->exec_ok ? 0 : -1;
}
static void *worker(void *unused) {
    (void)unused;
    for (;;) {
        pthread_mutex_lock(&mu);
        while (!queued) pthread_cond_wait(&available, &mu);
        Job job = queue[head]; head = (head + 1) % QUEUE; --queued; ++started;
        pthread_mutex_unlock(&mu);
        Event event = {0}; Audit audit = {.exit_code = -1};
        strcpy(event.id, job.id); strcpy(audit.id, job.id);
        event.enqueued = job.enqueued;
        STAMP(&event, acquired);
        int success = compress_job(&audit, &event) == 0;
        STAMP(&event, response_before);
        const char error[] = "native compression failed\n";
        int sent = response(job.fd, success ? 200 : 500, success ? "application/gzip" : "text/plain",
            job.id, success ? (const void *)body : (const void *)error,
            success ? audit.bytes : sizeof(error) - 1,
            event.acquired - event.enqueued, event.reaped - event.acquired, OBSERVED);
        STAMP(&event, response_after);
        close(job.fd);
        audit.success = success && !sent;
        event.success = audit.success;
        STAMP(&event, released);
        pthread_mutex_lock(&mu);
        if (completed < CAP) {
            audits[completed] = audit;
#if OBSERVED
            events[completed] = event;
#endif
        } else ++overflow;
        ++completed;
        pthread_mutex_unlock(&mu);
        if (!audit.reaped) _exit(92); /* Independent outer watchdog retains owned cleanup. */
    }
    return NULL;
}
static void controls(int fd, int event_export) {
    pthread_mutex_lock(&mu);
    FILE *out = fmemopen(exported, sizeof(exported), "w");
    if (!out) _exit(93);
    fprintf(out, "{\"Schema\":\"gzip-service-v1\",\"Observed\":%s,\"Capacity\":1024,\"Overflow\":%u,"
        "\"Started\":%u,\"Completed\":%u,\"Queued\":%u,\"ActivePID\":%d,\"ParentPID\":%d,\"Records\":[",
        OBSERVED ? "true" : "false", overflow, started, completed, queued, active_pid, getpid());
    unsigned count = completed < CAP ? completed : CAP;
    for (unsigned i = 0; i < count; ++i) {
        if (i) fputc(',', out);
        if (!event_export) {
            Audit *a = &audits[i];
            fprintf(out, "{\"ID\":\"%s\",\"PID\":%d,\"StartTicks\":%llu,\"PIDFD\":%s,"
                "\"AffinityCPU2\":%s,\"CgroupSame\":%s,\"SingleThreadAtGate\":%s,"
                "\"ExecSucceeded\":%s,\"Reaped\":%s,\"ExitCode\":%d,\"BodyBytes\":%zu,\"Success\":%s}",
                a->id, a->pid, a->ticks, a->pidfd_ok ? "true" : "false", a->affinity_ok ? "true" : "false",
                a->cgroup_ok ? "true" : "false", a->threads_ok ? "true" : "false",
                a->exec_ok ? "true" : "false", a->reaped ? "true" : "false", a->exit_code,
                a->bytes, a->success ? "true" : "false");
        } else {
#if OBSERVED
            Event *e = &events[i];
            fprintf(out, "{\"ID\":\"%s\",\"EnqueuedNs\":%" PRId64 ",\"AcquiredNs\":%" PRId64
                ",\"SpawnBeforeNs\":%" PRId64 ",\"SpawnAfterNs\":%" PRId64 ",\"DrainedNs\":%" PRId64
                ",\"ReapedNs\":%" PRId64 ",\"ResponseBeforeNs\":%" PRId64 ",\"ResponseAfterNs\":%" PRId64
                ",\"ReleasedNs\":%" PRId64 ",\"Success\":%s}", e->id, e->enqueued, e->acquired,
                e->spawn_before, e->spawn_after, e->drained, e->reaped,
                e->response_before, e->response_after, e->released, e->success ? "true" : "false");
#else
            _exit(94);
#endif
        }
    }
    fputs("]}", out);
    long size = ftell(out);
    int error = ferror(out);
    fclose(out);
    pthread_mutex_unlock(&mu);
    if (error || size < 0 || (size_t)size >= sizeof(exported)) _exit(95);
    (void)response(fd, 200, "application/json", NULL, exported, (size_t)size, 0, 0, 0);
    close(fd);
}
int main(void) {
    signal(SIGPIPE, SIG_IGN);
    cpu_set_t set; CPU_ZERO(&set);
    if (sched_getaffinity(0, sizeof(set), &set) || CPU_COUNT(&set) != 1 || !CPU_ISSET(2, &set)) return 2;
    int listener = socket(AF_INET, SOCK_STREAM | SOCK_CLOEXEC, 0), yes = 1;
    if (listener < 0) return 3;
    setsockopt(listener, SOL_SOCKET, SO_REUSEADDR, &yes, sizeof(yes));
    struct sockaddr_in address = {.sin_family = AF_INET, .sin_port = htons(8080), .sin_addr.s_addr = INADDR_ANY};
    if (bind(listener, (struct sockaddr *)&address, sizeof(address)) || listen(listener, 128)) return 4;
    pthread_t thread;
    if (pthread_create(&thread, NULL, worker, NULL)) return 5;
    for (;;) {
        int fd = accept4(listener, NULL, NULL, SOCK_CLOEXEC);
        if (fd < 0 && errno == EINTR) continue;
        if (fd < 0) return 6;
        struct timeval timeout = {3, 0};
        setsockopt(fd, SOL_SOCKET, SO_RCVTIMEO, &timeout, sizeof(timeout));
        setsockopt(fd, SOL_SOCKET, SO_SNDTIMEO, &timeout, sizeof(timeout));
        char request[4097]; size_t used = 0; int valid = 1;
        while (used < sizeof(request) - 1) {
            ssize_t n = recv(fd, request + used, sizeof(request) - 1 - used, 0);
            if (n < 0 && errno == EINTR) continue;
            if (n <= 0) { valid = 0; break; }
            used += (size_t)n; request[used] = 0;
            if (strstr(request, "\r\n\r\n")) break;
        }
        request[used] = 0;
        if (!valid || !strstr(request, "\r\n\r\n")) {
            (void)response(fd, 400, "text/plain", NULL, "bad request", 11, 0, 0, 0); close(fd); continue;
        }
        if (!strncmp(request, "GET /health HTTP/1.1\r\n", 22) ||
            !strncmp(request, "GET /qualification/audit HTTP/1.1\r\n", 35)) { controls(fd, 0); continue; }
#if OBSERVED
        if (!strncmp(request, "GET /qualification/events HTTP/1.1\r\n", 36)) { controls(fd, 1); continue; }
#endif
        char *id_header = strcasestr(request, "\r\nX-Request-ID: ");
        Job job = {.fd = fd};
        if (strncmp(request, "GET /compress HTTP/1.1\r\n", 24) || !id_header) valid = 0;
        /* Fixed GET-only interface; no client-selected payload or command. */
        if (strcasestr(request, "\r\nContent-Length:") || strcasestr(request, "\r\nTransfer-Encoding:")) valid = 0;
        if (valid) {
            char *p = id_header + 16, *end = strstr(p, "\r\n");
            size_t len = end ? (size_t)(end - p) : 0;
            if (!len || len > 64 || strcasestr(end, "\r\nX-Request-ID:")) valid = 0;
            for (size_t i = 0; valid && i < len; ++i)
                if (!((p[i] >= 'a' && p[i] <= 'z') || (p[i] >= 'A' && p[i] <= 'Z') ||
                      (p[i] >= '0' && p[i] <= '9') || p[i] == '-' || p[i] == '_')) valid = 0;
            if (valid) { memcpy(job.id, p, len); job.id[len] = 0; }
        }
        if (!valid) { (void)response(fd, 400, "text/plain", NULL, "bad request", 11, 0, 0, 0); close(fd); continue; }
        pthread_mutex_lock(&mu);
        if (queued == QUEUE) {
            pthread_mutex_unlock(&mu);
            (void)response(fd, 503, "text/plain", job.id, "queue full", 10, 0, 0, 0); close(fd); continue;
        }
#if OBSERVED
        job.enqueued = now_ns();
#endif
        queue[tail] = job; tail = (tail + 1) % QUEUE; ++queued;
        pthread_cond_signal(&available); pthread_mutex_unlock(&mu);
    }
}
