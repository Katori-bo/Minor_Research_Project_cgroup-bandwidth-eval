package main

import (
    "context"
    "crypto/sha256"
    "encoding/hex"
    "encoding/json"
    "flag"
    "fmt"
    "io"
    "net/http"
    "os"
    "runtime"
    "strconv"
    "sync"
    "time"
)

type job struct {
    id uint64
    iterations int
    admitted time.Time
    depth int
    context context.Context
    reply chan result
}

type result struct {
    queueNS, processingNS int64
    finished time.Time
    depth int
    digest [32]byte
}

type event struct {
    ID uint64 `json:"id"`
    AdmissionNS int64 `json:"admission_ns"`
    WorkerStartNS int64 `json:"worker_start_ns"`
    CompletionNS int64 `json:"completion_ns"`
    QueueWaitNS int64 `json:"queue_wait_ns"`
    ProcessingNS int64 `json:"processing_ns"`
    DepthAtAdmission int `json:"depth_at_admission"`
    ClientGoneAtCompletion bool `json:"client_gone_at_completion"`
}

type handlerEvent struct {
    ID uint64 `json:"id"`
    EntryNS int64 `json:"entry_ns"`
    AdmissionNS int64 `json:"admission_ns"`
    ResumeNS int64 `json:"resume_ns"`
    PreAdmissionNS int64 `json:"pre_admission_ns"`
    PostWorkWaitNS int64 `json:"post_work_wait_ns"`
    WriteStartNS int64 `json:"write_start_ns"`
    WriteEndNS int64 `json:"write_end_ns"`
    HandlerExitNS int64 `json:"handler_exit_ns"`
    WriteCalls int `json:"write_calls"`
    WriteBytes int `json:"write_bytes"`
    WriteError string `json:"write_error"`
}

// Wrap only the io.Writer used by fmt.Fprintf; retain the original HTTP response
// and formatting behavior. These boundaries time ResponseWriter.Write itself.
type timedWriter struct {
    writer io.Writer
    origin time.Time
    timing *handlerEvent
}

func (w *timedWriter) Write(p []byte) (int, error) {
    start := time.Since(w.origin).Nanoseconds()
    n, err := w.writer.Write(p)
    end := time.Since(w.origin).Nanoseconds()
    if w.timing.WriteCalls == 0 { w.timing.WriteStartNS = start }
    w.timing.WriteCalls++
    w.timing.WriteEndNS = end
    w.timing.WriteBytes += n
    if err != nil && w.timing.WriteError == "" { w.timing.WriteError = err.Error() }
    return n, err
}

type service struct {
    queue chan job
    workers int
    instrument bool
    origin time.Time
    mu sync.Mutex
    events []event
    handlerEvents []handlerEvent
    admitted, rejected, completed, abandoned, active, maxDepth int
}

func newService(workers, capacity int, instrument bool) *service {
    return &service{queue: make(chan job, capacity), workers: workers,
        instrument: instrument, origin: time.Now()}
}

func work(n int) [32]byte {
    var state [32]byte
    for i := range state { state[i] = byte(i) }
    for i := 0; i < n; i++ { state = sha256.Sum256(state[:]) }
    return state
}

func (s *service) worker() {
    for j := range s.queue {
        var start, finish time.Time
        if s.instrument { start = time.Now() }
        digest := work(j.iterations)
        if s.instrument { finish = time.Now() }
        gone := j.context.Err() != nil
        answer := result{depth: j.depth, digest: digest}
        if s.instrument {
            answer.queueNS = start.Sub(j.admitted).Nanoseconds()
            answer.processingNS = finish.Sub(start).Nanoseconds()
            answer.finished = finish
        }
        // Completion becomes visible only after the corresponding event is saved.
        s.mu.Lock()
        if s.instrument {
            s.events = append(s.events, event{j.id,
                j.admitted.Sub(s.origin).Nanoseconds(), start.Sub(s.origin).Nanoseconds(),
                finish.Sub(s.origin).Nanoseconds(), answer.queueNS, answer.processingNS,
                j.depth, gone})
        }
        s.completed++
        if gone { s.abandoned++ }
        s.mu.Unlock()
        j.reply <- answer // Buffered: timed-out clients never strand a worker.
    }
}

func (s *service) workHandler(w http.ResponseWriter, r *http.Request) {
    var handlerEntry time.Time
    if s.instrument { handlerEntry = time.Now() }
    var timing *handlerEvent
    n := 44000
    if x, err := strconv.Atoi(r.URL.Query().Get("iterations")); err == nil && x > 0 { n = x }
    id, err := strconv.ParseUint(r.URL.Query().Get("id"), 10, 64)
    if err != nil { http.Error(w, "request id required", http.StatusBadRequest); return }
    s.mu.Lock()
    s.active++
    s.mu.Unlock()
    defer func() {
        s.mu.Lock()
        if timing != nil { s.handlerEvents = append(s.handlerEvents, *timing) }
        s.active--
        // Timestamp after lock acquisition and event storage. Snapshot/reset
        // cannot observe a drained handler before its exit marker is published.
        // Unlock and the actual function return still follow this marker.
        if timing != nil {
            s.handlerEvents[len(s.handlerEvents)-1].HandlerExitNS = time.Since(s.origin).Nanoseconds()
        }
        s.mu.Unlock()
    }()
    j := job{id: id, iterations: n, context: r.Context(), reply: make(chan result, 1)}
    s.mu.Lock()
    j.depth = len(s.queue) // Admission-time sample, not a continuous occupancy trace.
    if s.instrument { j.admitted = time.Now() }
    accepted := false
    select {
    case s.queue <- j:
        s.admitted++
        if j.depth > s.maxDepth { s.maxDepth = j.depth }
        accepted = true
    default:
        s.rejected++
        if len(s.queue) > s.maxDepth { s.maxDepth = len(s.queue) }
    }
    s.mu.Unlock()
    if !accepted { http.Error(w, "queue full", http.StatusServiceUnavailable); return }
    select {
    case answer := <-j.reply:
        if s.instrument {
            resumed := time.Now()
            pre := j.admitted.Sub(handlerEntry).Nanoseconds()
            post := resumed.Sub(answer.finished).Nanoseconds()
            timing = &handlerEvent{ID: id, EntryNS: handlerEntry.Sub(s.origin).Nanoseconds(),
                AdmissionNS: j.admitted.Sub(s.origin).Nanoseconds(),
                ResumeNS: resumed.Sub(s.origin).Nanoseconds(), PreAdmissionNS: pre,
                PostWorkWaitNS: post}
            w.Header().Set("X-Queue-Wait-Ns", strconv.FormatInt(answer.queueNS, 10))
            w.Header().Set("X-Processing-Ns", strconv.FormatInt(answer.processingNS, 10))
            w.Header().Set("X-Queue-Depth", strconv.Itoa(answer.depth))
            w.Header().Set("X-Pre-Admission-Ns", strconv.FormatInt(pre, 10))
            w.Header().Set("X-Post-Work-Wait-Ns", strconv.FormatInt(post, 10))
        }
        var output io.Writer = w
        if timing != nil { output = &timedWriter{writer: w, origin: s.origin, timing: timing} }
        fmt.Fprintf(output, "OK: iter=%d digest=%s\n", n, hex.EncodeToString(answer.digest[:8]))
    case <-r.Context().Done():
        // Keep the admitted job in the queue and retain its eventual completion.
    }
}

func (s *service) snapshot(includeEvents bool) map[string]any {
    s.mu.Lock()
    defer s.mu.Unlock()
    snapshot := map[string]any{
        "admitted": s.admitted, "rejected": s.rejected, "completed": s.completed,
        "client_gone_at_completion": s.abandoned, "active_handlers": s.active,
        "queue_len": len(s.queue), "queue_cap": cap(s.queue),
        "queue_max": s.maxDepth, "workers": s.workers,
        "gomaxprocs": runtime.GOMAXPROCS(0), "go_version": runtime.Version(),
        "instrument": s.instrument,
    }
    if includeEvents { snapshot["events"] = append([]event{}, s.events...) }
    if includeEvents { snapshot["handler_events"] = append([]handlerEvent{}, s.handlerEvents...) }
    return snapshot
}

func (s *service) metrics(w http.ResponseWriter, r *http.Request) {
    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(s.snapshot(true))
}

func (s *service) health(w http.ResponseWriter, r *http.Request) {
    data := s.snapshot(false)
    data["gomaxprocs_env"] = os.Getenv("GOMAXPROCS")
    data["godebug"] = os.Getenv("GODEBUG")
    data["num_cpu"] = runtime.NumCPU()
    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(data)
}

func (s *service) reset(w http.ResponseWriter, r *http.Request) {
    if r.Method != http.MethodPost { http.Error(w, "POST required", 405); return }
    s.mu.Lock()
    defer s.mu.Unlock()
    if s.admitted != s.completed || s.active != 0 || len(s.queue) != 0 {
        http.Error(w, "jobs or handlers in flight", 409); return
    }
    s.events = nil
    s.handlerEvents = nil
    s.admitted, s.rejected, s.completed, s.abandoned, s.maxDepth = 0, 0, 0, 0, 0
    s.origin = time.Now()
    w.WriteHeader(http.StatusNoContent)
}

func positiveEnv(key string, fallback int) int {
    if value := os.Getenv(key); value != "" {
        n, err := strconv.Atoi(value)
        if err != nil || n < 1 { panic("invalid " + key) }
        return n
    }
    return fallback
}

func main() {
    port := flag.Int("port", 8080, "HTTP port")
    flag.Parse()
    if os.Getenv("GOMAXPROCS") != "" { runtime.GOMAXPROCS(positiveEnv("GOMAXPROCS", 2)) }
    s := newService(positiveEnv("WORKERS", 1), positiveEnv("QUEUE_SIZE", 128), os.Getenv("INSTRUMENT") != "0")
    for i := 0; i < s.workers; i++ { go s.worker() }
    http.HandleFunc("/work", s.workHandler)
    http.HandleFunc("/metrics", s.metrics)
    http.HandleFunc("/health", s.health)
    http.HandleFunc("/reset", s.reset)
    if err := http.ListenAndServe(fmt.Sprintf(":%d", *port), nil); err != nil { panic(err) }
}
