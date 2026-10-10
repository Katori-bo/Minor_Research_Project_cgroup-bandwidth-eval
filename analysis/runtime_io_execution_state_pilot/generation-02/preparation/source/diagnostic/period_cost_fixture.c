#define _GNU_SOURCE
#include <sched.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

/* Known fixed work on both service CPUs. No code enters the Go executable. */
static uint64_t work(int cpu, unsigned n) {
    cpu_set_t set; CPU_ZERO(&set); CPU_SET(cpu, &set);
    if (sched_setaffinity(0, sizeof(set), &set)) _exit(10);
    volatile uint64_t x = 1;
    for (unsigned i = 0; i < n; ++i) x = x * 1664525 + 1013904223;
    return x;
}
int main(int argc, char **argv) {
    if (argc != 2 || (strcmp(argv[1], "compute") && strcmp(argv[1], "sleep") && strcmp(argv[1], "selftest"))) return 2;
    puts("READY"); fflush(stdout);
    if (getchar() != 'G') return 3;
    unsigned n = !strcmp(argv[1], "selftest") ? 1024 : 134217728;
    pid_t child = fork();
    if (child < 0) return 4;
    if (!child) { uint64_t x = work(4, n); printf("CHILD %llu\n", (unsigned long long)x); fflush(stdout); _exit(0); }
    uint64_t x = work(2, n);
    int status;
    if (waitpid(child, &status, 0) != child || !WIFEXITED(status) || WEXITSTATUS(status)) return 5;
    if (!strcmp(argv[1], "sleep")) {
        struct timespec t = {1, 0};
        while (nanosleep(&t, &t)) {}
    }
    printf("DONE %llu\n", (unsigned long long)x); fflush(stdout);
    /* Remain alive until the counters are disabled and CPU stats are read. */
    return getchar() == 'Q' ? 0 : 6;
}
