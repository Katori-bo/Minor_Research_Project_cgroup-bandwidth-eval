package main

import (
    "context"
    "errors"
    "io"
    "net/http"
    "net/http/httptest"
    "strconv"
    "sync"
    "testing"
    "time"
)

func await(t *testing.T, condition func() bool) {
    t.Helper()
    deadline := time.Now().Add(3 * time.Second)
    for !condition() {
        if time.Now().After(deadline) { t.Fatal("condition did not become true") }
        time.Sleep(time.Millisecond)
    }
}

func TestTimedOutQueuedWorkCompletesAndResetWaits(t *testing.T) {
    s := newService(1, 1, true)
    ctx, cancel := context.WithCancel(context.Background())
    request := httptest.NewRequest("GET", "/work?iterations=100&id=7", nil).WithContext(ctx)
    done := make(chan struct{})
    go func() { s.workHandler(httptest.NewRecorder(), request); close(done) }()
    await(t, func() bool { return s.snapshot(false)["admitted"].(int) == 1 })
    cancel()
    <-done
    denied := httptest.NewRecorder()
    s.reset(denied, httptest.NewRequest("POST", "/reset", nil))
    if denied.Code != 409 { t.Fatal("reset lost unfinished work") }
    overflow := httptest.NewRecorder()
    s.workHandler(overflow, httptest.NewRequest("GET", "/work?iterations=100&id=8", nil))
    if overflow.Code != 503 { t.Fatal("full queue not rejected") }
    go s.worker()
    await(t, func() bool { return s.snapshot(false)["completed"].(int) == 1 })
    close(s.queue)
    snapshot := s.snapshot(true)
    events := snapshot["events"].([]event)
    if len(events) != 1 || !events[0].ClientGoneAtCompletion || snapshot["client_gone_at_completion"].(int) != 1 {
        t.Fatal("timed-out work was lost", snapshot)
    }
    e := events[0]
    if e.ID != 7 || e.QueueWaitNS <= 0 || e.ProcessingNS <= 0 || e.WorkerStartNS-e.AdmissionNS != e.QueueWaitNS || e.CompletionNS-e.WorkerStartNS != e.ProcessingNS {
        t.Fatal("inconsistent component timing", e)
    }
    reset := httptest.NewRecorder()
    s.reset(reset, httptest.NewRequest("POST", "/reset", nil))
    if reset.Code != 204 || s.snapshot(false)["completed"].(int) != 0 { t.Fatal("drained reset failed") }
}

func TestSnapshotsDoNotPublishCompletionBeforeEvents(t *testing.T) {
    s := newService(4, 128, true)
    for i := 0; i < 4; i++ { go s.worker() }
    done := make(chan struct{})
    go func() {
        for i := 0; i < 100; i++ {
            s.workHandler(httptest.NewRecorder(), httptest.NewRequest("GET", "/work?iterations=100&id="+strconv.Itoa(i), nil))
        }
        close(done)
    }()
    for {
        snapshot := s.snapshot(true)
        if snapshot["completed"].(int) != len(snapshot["events"].([]event)) { t.Fatal("incomplete event snapshot") }
        select { case <-done:
            if len(s.snapshot(true)["handler_events"].([]handlerEvent)) != 100 { t.Fatal("handler events missing after drain") }
            close(s.queue); return
        default: }
    }
}

func TestTimingHeadersMatchAndOffMeansOff(t *testing.T) {
    for _, enabled := range []bool{true, false} {
        s := newService(1, 1, enabled)
        go s.worker()
        response := httptest.NewRecorder()
        s.workHandler(response, httptest.NewRequest("GET", "/work?iterations=100&id=0", nil))
        close(s.queue)
        if response.Code != 200 { t.Fatal(response.Code) }
        if enabled {
            e := s.snapshot(true)["events"].([]event)[0]
            if response.Header().Get("X-Queue-Wait-Ns") != strconv.FormatInt(e.QueueWaitNS, 10) || response.Header().Get("X-Processing-Ns") != strconv.FormatInt(e.ProcessingNS, 10) { t.Fatal("timing headers differ") }
            h := s.snapshot(true)["handler_events"].([]handlerEvent)[0]
            if h.AdmissionNS-h.EntryNS != h.PreAdmissionNS || h.ResumeNS-e.CompletionNS != h.PostWorkWaitNS ||
                response.Header().Get("X-Pre-Admission-Ns") != strconv.FormatInt(h.PreAdmissionNS, 10) ||
                response.Header().Get("X-Post-Work-Wait-Ns") != strconv.FormatInt(h.PostWorkWaitNS, 10) { t.Fatal("diagnostic timing mismatch") }
            if h.ResumeNS > h.WriteStartNS || h.WriteStartNS > h.WriteEndNS || h.WriteEndNS > h.HandlerExitNS ||
                h.WriteBytes != response.Body.Len() || h.WriteError != "" {
                t.Fatal("response-write timing mismatch", h)
            }
        } else if response.Header().Get("X-Queue-Wait-Ns") != "" || len(s.events) != 0 {
            t.Fatal("instrumentation off still records timing")
        } else if len(s.handlerEvents) != 0 {
            t.Fatal("instrumentation off recorded handler timing")
        }
    }
}

func TestWorkMatchesOriginalSHAWork(t *testing.T) {
    if work(10) == work(11) || work(10) != work(10) { t.Fatal("work ignored iterations or is non-deterministic") }
}

type lockAfterWrite struct {
    *httptest.ResponseRecorder
    mu *sync.Mutex
    held chan struct{}
}

func (w *lockAfterWrite) Write(p []byte) (int, error) {
    n, err := w.ResponseRecorder.Write(p)
    w.mu.Lock()
    close(w.held)
    return n, err
}

func TestExitMarkerIncludesFinalLockWait(t *testing.T) {
    s := newService(1, 1, true)
    go s.worker()
    writer := &lockAfterWrite{httptest.NewRecorder(), &s.mu, make(chan struct{})}
    done := make(chan struct{})
    go func() {
        s.workHandler(writer, httptest.NewRequest("GET", "/work?iterations=100&id=7", nil))
        close(done)
    }()
    select {
    case <-writer.held:
    case <-time.After(3 * time.Second): t.Fatal("handler never wrote")
    }
    // Allow the handler to reach its final mutex while the test owns the lock.
    time.Sleep(20 * time.Millisecond)
    releaseNS := time.Since(s.origin).Nanoseconds()
    s.mu.Unlock()
    select {
    case <-done:
    case <-time.After(3 * time.Second): t.Fatal("handler did not return")
    }
    snapshot := s.snapshot(true)
    h := snapshot["handler_events"].([]handlerEvent)[0]
    if h.HandlerExitNS < releaseNS || h.HandlerExitNS < h.WriteEndNS || snapshot["active_handlers"].(int) != 0 {
        t.Fatal("exit marker missed final lock wait or was not published before drain", h)
    }
    close(s.queue)
}

type failedWriter struct { *httptest.ResponseRecorder }

func (w failedWriter) Write(p []byte) (int, error) { return 0, errors.New("test write failure") }

func TestWriteFailureIsRetained(t *testing.T) {
    s := newService(1, 1, true)
    go s.worker()
    s.workHandler(failedWriter{httptest.NewRecorder()}, httptest.NewRequest("GET", "/work?iterations=100&id=5", nil))
    h := s.snapshot(true)["handler_events"].([]handlerEvent)[0]
    if h.WriteCalls != 1 || h.WriteBytes != 0 || h.WriteError != "test write failure" || h.HandlerExitNS < h.WriteEndNS {
        t.Fatal("write failure lost or exit not recorded", h)
    }
    close(s.queue)
}

func TestRealHTTPResponseUnchangedAndEventsDrained(t *testing.T) {
    var previous string
    for _, enabled := range []bool{false, true} {
        s := newService(1, 1, enabled)
        go s.worker()
        server := httptest.NewServer(http.HandlerFunc(s.workHandler))
        response, err := http.Get(server.URL + "/work?iterations=100&id=1")
        if err != nil { t.Fatal(err) }
        body, err := io.ReadAll(response.Body)
        response.Body.Close()
        if err != nil || response.StatusCode != 200 { t.Fatal("invalid response", err) }
        await(t, func() bool { return s.snapshot(false)["active_handlers"].(int) == 0 })
        if enabled {
            if previous != string(body) { t.Fatal("instrumentation changed response body") }
            events := s.snapshot(true)["handler_events"].([]handlerEvent)
            if len(events) != 1 || events[0].WriteCalls != 1 || events[0].WriteBytes != len(body) {
                t.Fatal("drained HTTP response has incomplete write evidence", events)
            }
        }
        previous = string(body)
        server.Close()
        close(s.queue)
    }
}
