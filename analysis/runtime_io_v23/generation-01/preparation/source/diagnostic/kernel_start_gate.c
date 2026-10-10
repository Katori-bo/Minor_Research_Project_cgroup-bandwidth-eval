#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <sched.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

/* Single-thread startup barrier. No code survives exec into the retained server. */
static int64_t ns(clockid_t clock) {
    struct timespec t;
    if (clock_gettime(clock, &t)) _exit(90);
    return (int64_t)t.tv_sec * 1000000000LL + t.tv_nsec;
}
static void event(const char *name, int cpu) {
    printf("{\"event\":\"%s\",\"pid\":%d,\"cpu\":%d,\"monotonic_ns\":%lld,\"cpu_ns\":%lld}\n",
           name, getpid(), cpu, (long long)ns(CLOCK_MONOTONIC),
           (long long)ns(CLOCK_PROCESS_CPUTIME_ID));
    fflush(stdout);
}
int main(int argc, char **argv) {
    if (argc != 2 || (strcmp(argv[1], "--server") && strcmp(argv[1], "--fixture"))) return 2;
    event("ready", sched_getcpu());
    if (!strcmp(argv[1], "--server")) {
        /* Namespace PID 1 ignores a self-issued SIGSTOP. A FIFO is a real
           blocking barrier in both host and container PID namespaces. */
        int fd = open("/qualification/start.fifo", O_RDONLY);
        char token = 0;
        if (fd < 0 || read(fd, &token, 1) != 1 || token != 'G') return 3;
        close(fd);
        execl("/server", "/server", (char *)NULL);
        perror("exec /server");
        return 4;
    }
    if (raise(SIGSTOP)) return 3;
    pid_t children[2];
    for (int i = 0; i < 2; ++i) {
        children[i] = fork();
        if (children[i] < 0) return 5;
        if (!children[i]) {
            int cpu = i ? 4 : 2;
            cpu_set_t set; CPU_ZERO(&set); CPU_SET(cpu, &set);
            if (sched_setaffinity(0, sizeof(set), &set)) _exit(6);
            event("child_start", cpu);
            int64_t until = ns(CLOCK_MONOTONIC) + 1800000000LL;
            volatile uint64_t value = 1;
            while (ns(CLOCK_MONOTONIC) < until)
                for (int n = 0; n < 4096; ++n) value = value * 1664525 + 1013904223;
            event("child_end", cpu);
            _exit(0);
        }
    }
    for (int i = 0; i < 2; ++i) {
        int status;
        if (waitpid(children[i], &status, 0) != children[i] ||
            !WIFEXITED(status) || WEXITSTATUS(status)) return 7;
    }
    struct timespec delay = {0, 300000000};
    while (nanosleep(&delay, &delay) && errno == EINTR) {}
    event("done", sched_getcpu());
    return 0;
}
