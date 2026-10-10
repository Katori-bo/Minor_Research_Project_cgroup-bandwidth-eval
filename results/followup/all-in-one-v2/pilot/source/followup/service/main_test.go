package main

import (
    "context"
    "net/http/httptest"
    "strconv"
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
        select { case <-done: close(s.queue); return; default: }
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
        } else if response.Header().Get("X-Queue-Wait-Ns") != "" || len(s.events) != 0 {
            t.Fatal("instrumentation off still records timing")
        }
    }
}

func TestWorkMatchesOriginalSHAWork(t *testing.T) {
    if work(10) == work(11) || work(10) != work(10) { t.Fatal("work ignored iterations or is non-deterministic") }
}
