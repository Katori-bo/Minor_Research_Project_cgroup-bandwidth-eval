#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <inttypes.h>
#include <sched.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

#define CAPACITY 6000
#define RAW_CAPACITY 4096
#define STEP_NS UINT64_C(20000000)
#define BOUND_NS UINT64_C(110000000000)
typedef struct {
    uint64_t scheduled, before, after, cpu_before, cpu_after;
    ssize_t length;
    int error;
    char raw[RAW_CAPACITY];
} record;
static volatile sig_atomic_t running = 1;
static void stop_capture(int signal_number) { (void)signal_number; running = 0; }
static uint64_t now(clockid_t id) {
    struct timespec t;
    if (clock_gettime(id, &t)) { perror("clock_gettime"); exit(2); }
    return (uint64_t)t.tv_sec * UINT64_C(1000000000) + (uint64_t)t.tv_nsec;
}
static void quote(FILE *out, const char *value, size_t length) {
    fputc('"', out);
    for (size_t i=0; i<length; ++i) {
        unsigned char ch=(unsigned char)value[i];
        if (ch=='"' || ch=='\\') { fputc('\\', out); fputc(ch, out); }
        else if (ch<32 || ch>126) fprintf(out,"\\u%04x",ch);
        else fputc(ch,out);
    }
    fputc('"',out);
}
int main(int argc, char **argv) {
    if (argc!=5 || strcmp(argv[1],"--path") || strcmp(argv[3],"--output")) {
        fprintf(stderr,"Usage: counter --path CPU_STAT --output RAW_JSON\n"); return 2;
    }
    struct sigaction sa={0}; sa.sa_handler=stop_capture;
    sigemptyset(&sa.sa_mask);
    if (sigaction(SIGINT,&sa,NULL) || sigaction(SIGTERM,&sa,NULL)) return 2;
    cpu_set_t affinity;
    if (sched_getaffinity(0,sizeof(affinity),&affinity)) return 2;
    /* Preallocate and fault in storage before the timed lifetime. */
    record *records=calloc(CAPACITY,sizeof(*records));
    if (!records) return 2;
    volatile unsigned char *storage=(volatile unsigned char *)records;
    for (size_t i=0;i<CAPACITY*sizeof(*records);i+=4096) storage[i]=0;
    int output_fd=open(argv[4],O_WRONLY|O_CREAT|O_EXCL|O_CLOEXEC,0600);
    if (output_fd<0) { perror("output"); free(records); return 2; }
    int input_fd=open(argv[2],O_RDONLY|O_CLOEXEC);
    int failure=input_fd<0 ? errno : 0;
    uint64_t cpu_start=now(CLOCK_THREAD_CPUTIME_ID);
    uint64_t started=now(CLOCK_MONOTONIC), scheduled=started, skipped=0;
    size_t count=0;
    while (!failure && running && now(CLOCK_MONOTONIC)<started+BOUND_NS) {
        if (count==CAPACITY) { failure=EOVERFLOW; break; }
        record *r=&records[count++]; r->scheduled=scheduled;
        r->before=now(CLOCK_MONOTONIC);
        r->cpu_before=now(CLOCK_THREAD_CPUTIME_ID);
        if (lseek(input_fd,0,SEEK_SET)<0) r->error=errno;
        else {
            r->length=read(input_fd,r->raw,RAW_CAPACITY);
            if (r->length<0) { r->error=errno; r->length=0; }
            else if (r->length==0) r->error=ENODATA;
            else if (r->length==RAW_CAPACITY) r->error=EOVERFLOW;
        }
        r->cpu_after=now(CLOCK_THREAD_CPUTIME_ID);
        r->after=now(CLOCK_MONOTONIC);
        if (r->error) { failure=r->error; break; }
        /* Single control handshake, outside acquisition; no periodic output. */
        if (count==1 && write(STDOUT_FILENO,"READY\n",6)!=6) {
            failure=EIO; break;
        }
        scheduled+=STEP_NS;
        uint64_t wall=now(CLOCK_MONOTONIC);
        while (scheduled<=wall) { scheduled+=STEP_NS; ++skipped; }
        uint64_t target=scheduled<started+BOUND_NS ? scheduled : started+BOUND_NS;
        struct timespec wake={(time_t)(target/UINT64_C(1000000000)),
                              (long)(target%UINT64_C(1000000000))};
        int error;
        do { error=clock_nanosleep(CLOCK_MONOTONIC,TIMER_ABSTIME,&wake,NULL); }
        while (error==EINTR && running);
        if (error && error!=EINTR) { failure=error; break; }
    }
    uint64_t finished=now(CLOCK_MONOTONIC),cpu_end=now(CLOCK_THREAD_CPUTIME_ID);
    if (input_fd>=0) close(input_fd);
    /* No decoding, dynamic record allocation, or serialization in acquisition. */
    FILE *out=fdopen(output_fd,"w");
    if (!out) { close(output_fd); free(records); return 2; }
    fprintf(out,"{\"schema\":3,\"sampler_revision\":\"v24r3-native\",\"path\":");
    quote(out,argv[2],strlen(argv[2]));
    fprintf(out,",\"interval_sec\":0.02,\"duration_bound_sec\":110,"
        "\"record_capacity\":6000,\"raw_capacity\":4096,"
        "\"cadence\":\"absolute_skip_missed\",\"skipped_deadlines\":%" PRIu64
        ",\"started_ns\":%" PRIu64 ",\"finished_ns\":%" PRIu64
        ",\"thread_cpu_started_ns\":%" PRIu64 ",\"thread_cpu_finished_ns\":%" PRIu64
        ",\"own_cpu_ns\":%" PRIu64 ",\"pid\":%ld,\"uid\":%ld,\"affinity\":[",
        skipped,started,finished,cpu_start,cpu_end,cpu_end-cpu_start,(long)getpid(),(long)getuid());
    int comma=0;
    for (int i=0;i<CPU_SETSIZE;++i) if (CPU_ISSET(i,&affinity)) {
        fprintf(out,"%s%d",comma?",":"",i); comma=1;
    }
    fprintf(out,"],\"failure\":");
    if (failure) quote(out,strerror(failure),strlen(strerror(failure))); else fputs("null",out);
    fputs(",\"samples\":[",out);
    for (size_t i=0;i<count;++i) {
        record *r=&records[i];
        fprintf(out,"%s{\"scheduled_ns\":%" PRIu64 ",\"before_ns\":%" PRIu64
            ",\"after_ns\":%" PRIu64 ",\"thread_cpu_before_ns\":%" PRIu64
            ",\"thread_cpu_after_ns\":%" PRIu64 ",\"read_errno\":%d,\"raw\":",
            i?",":"",r->scheduled,r->before,r->after,r->cpu_before,r->cpu_after,r->error);
        quote(out,r->raw,(size_t)r->length); fputc('}',out);
    }
    fputs("]}\n",out);
    int write_error=ferror(out);
    if (fclose(out)) write_error=1;
    free(records);
    return failure || write_error ? 1 : 0;
}
