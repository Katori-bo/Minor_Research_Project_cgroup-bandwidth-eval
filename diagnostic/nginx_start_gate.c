#define _GNU_SOURCE
#include <fcntl.h>
#include <sched.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

/* Sole-thread barrier; no code survives exec into the unchanged application. */
int main(int argc, char **argv) {
    if (argc != 2 || strcmp(argv[1], "--server")) return 2;
    cpu_set_t set; CPU_ZERO(&set);
    if (sched_getaffinity(0, sizeof(set), &set) || CPU_COUNT(&set) != 1 || !CPU_ISSET(2, &set)) return 3;
    int fd = open("/qualification/start.fifo", O_RDONLY);
    char token = 0;
    if (fd < 0 || read(fd, &token, 1) != 1 || token != 'G') return 4;
    close(fd);
    /* Avoid opening the compile-time relative initial error-log path. */
    execl("/server", "/server", "-e", "stderr", (char *)NULL);
    perror("exec stock NGINX");
    return 5;
}
