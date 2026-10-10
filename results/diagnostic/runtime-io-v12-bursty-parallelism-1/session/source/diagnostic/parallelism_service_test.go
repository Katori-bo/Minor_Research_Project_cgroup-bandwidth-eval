package main

import (
    "context"
    "encoding/json"
    "net/http/httptest"
    "testing"
)

func TestParallelismEntryRetainsRejectionAndCancellation(t *testing.T) {
    for _, reject := range []bool{true, false} {
        s := newService(1, 1, true)
        if reject { s.queue <- job{id:99} }
        request := httptest.NewRequest("GET", "/work?id=0&iterations=1", nil)
        ctx, cancel := context.WithCancel(request.Context()); cancel()
        request = request.WithContext(ctx)
        response := httptest.NewRecorder()
        s.workHandler(response, request)
        if len(s.entries) != 1 || s.entries[0].ID != 0 ||
            s.entries[0].Admitted == reject || s.entries[0].EntryNS < 0 ||
            s.entries[0].ExitNS < s.entries[0].EntryNS || s.active != 0 {
            t.Fatalf("entry was lost or invalid: %+v", s.entries)
        }
        if len(s.handlerEvents) != 0 { t.Fatal("changed successful-response cohort") }
    }
}

func TestParallelismClockGenerationAndReset(t *testing.T) {
    s := newService(1, 1, true)
    for generation := uint64(0); generation < 2; generation++ {
        response := httptest.NewRecorder()
        s.clock(response, httptest.NewRequest("GET", "/clock", nil))
        var value struct { ServerNS int64 `json:"server_ns"`; Generation uint64 `json:"generation"` }
        if err := json.Unmarshal(response.Body.Bytes(), &value); err != nil ||
            value.ServerNS < 0 || value.Generation != generation { t.Fatal("bad clock", value, err) }
        s.reset(httptest.NewRecorder(), httptest.NewRequest("POST", "/reset", nil))
        if len(s.entries) != 0 { t.Fatal("entry reset failed") }
    }
}
