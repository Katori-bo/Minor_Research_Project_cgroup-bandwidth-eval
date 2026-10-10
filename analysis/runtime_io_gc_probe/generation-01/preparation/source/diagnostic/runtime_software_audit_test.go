package main

// Added only to an isolated copy of the retained service, never its sealed source.
import (
    "context"
    "encoding/hex"
    "net/http/httptest"
    "runtime"
    "strconv"
    "strings"
    "sync"
    "testing"
)

func TestAuditIndependentDigestVectors(t *testing.T) {
    // Reference digests are generated independently with Python hashlib during
    // preparation and embedded in audit_vectors_test.go.
    for n, expected := range auditDigestVectors {
        got := work(n)
        if hex.EncodeToString(got[:]) != expected { t.Fatalf("wrong digest for %d iterations", n) }
    }
}

func TestAuditConcurrentRequestsSnapshotsAndDrainedResets(t *testing.T) {
    original := runtime.GOMAXPROCS(0)
    defer runtime.GOMAXPROCS(original)
    for _, procs := range []int{1, 2} {
        runtime.GOMAXPROCS(procs)
        for _, yielding := range []bool{false, true} {
            s := newService(1, 16, true)
            s.workerYield = yielding
            workerDone := make(chan struct{})
            go func() { s.worker(); close(workerDone) }()
            for round := 0; round < 3; round++ {
                stop, observerDone := make(chan struct{}), make(chan struct{})
                go func() {
                    defer close(observerDone)
                    for {
                        select { case <-stop: return; default: }
                        s.snapshot(true)
                        s.clock(httptest.NewRecorder(), httptest.NewRequest("GET", "/clock", nil))
                        runtime.Gosched()
                    }
                }()
                var group sync.WaitGroup
                statuses := make([]int, 64)
                bodies := make([]string, 64)
                for i := range statuses {
                    group.Add(1)
                    go func(i int) {
                        defer group.Done()
                        r := httptest.NewRequest("GET", "/work?iterations=10&id="+strconv.Itoa(i), nil)
                        ctx, cancel := context.WithCancel(r.Context())
                        defer cancel()
                        if i%4 == 0 { cancel() }
                        w := httptest.NewRecorder()
                        s.workHandler(w, r.WithContext(ctx))
                        statuses[i], bodies[i] = w.Code, w.Body.String()
                    }(i)
                }
                group.Wait()
                await(t, func() bool {
                    v := s.snapshot(false)
                    return v["active_handlers"].(int) == 0 && v["queue_len"].(int) == 0 && v["completed"] == v["admitted"]
                })
                close(stop); <-observerDone
                v := s.snapshot(true)
                if v["admitted"].(int)+v["rejected"].(int) != len(statuses) { t.Fatal("lost offer") }
                if v["completed"].(int) != len(v["events"].([]event)) || len(v["entry_events"].([]entryEvent)) != len(statuses) { t.Fatal("lost records") }
                seen := map[uint64]bool{}
                for _, e := range v["events"].([]event) {
                    if seen[e.ID] || e.CompletionNS < e.WorkerStartNS || e.WorkerStartNS < e.AdmissionNS { t.Fatal("duplicate work or invalid times") }
                    seen[e.ID] = true
                }
                expected := "digest="+auditDigestVectors[10][:16]
                for i, status := range statuses {
                    if status != 200 && status != 503 { t.Fatal("unexpected response", status) }
                    if i%4 != 0 && status == 200 && !strings.Contains(bodies[i], expected) { t.Fatal("wrong successful response", bodies[i]) }
                }
                w := httptest.NewRecorder()
                s.reset(w, httptest.NewRequest("POST", "/reset", nil))
                if w.Code != 204 || s.snapshot(false)["completed"].(int) != 0 { t.Fatal("drained reset failed") }
            }
            close(s.queue); <-workerDone
        }
    }
}
