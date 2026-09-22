package main

import (
 "net/http/httptest"
 "testing"
)

func TestQueueOverflow(t *testing.T) {
 jobQueue = make(chan Job, 1)
 jobQueue <- Job{}
 r := httptest.NewRequest("GET", "/work?iterations=1", nil)
 w := httptest.NewRecorder()
 workHandler(w,r)
 if w.Code != 503 { t.Fatalf("status=%d", w.Code) }
}

func TestWorkDeterministicAndDependentOnIterations(t *testing.T) {
 if cpuWork(10) != cpuWork(10) { t.Fatal("non deterministic") }
 if cpuWork(10) == cpuWork(11) { t.Fatal("iterations ignored") }
}
