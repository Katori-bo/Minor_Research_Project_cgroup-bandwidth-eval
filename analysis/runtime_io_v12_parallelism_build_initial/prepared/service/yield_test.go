package main

import (
	"context"
	"testing"
)

func TestWorkerYieldCompletesIdenticalWork(t *testing.T) {
	for _, enabled := range []bool{false, true} {
		s := newService(1, 4, true)
		s.workerYield = enabled
		done := make(chan struct{})
		go func() { s.worker(); close(done) }()
		for id := uint64(0); id < 3; id++ {
			reply := make(chan result, 1)
			s.queue <- job{id: id, iterations: 100, context: context.Background(), reply: reply}
			if answer := <-reply; answer.digest != work(100) {
				t.Fatal("yield changed work result")
			}
		}
		close(s.queue)
		<-done // Worker returned after every post-job yield, with no stranded reply.
		if s.snapshot(false)["completed"] != 3 || s.snapshot(false)["worker_yield"] != enabled {
			t.Fatal(s.snapshot(false))
		}
	}
}

func TestWorkerYieldEnvironmentIsExplicit(t *testing.T) {
	for _, value := range []string{"", "0", "1"} {
		t.Setenv("WORKER_YIELD", value)
		if booleanEnv("WORKER_YIELD", false) != (value == "1") {
			t.Fatal(value)
		}
	}
	t.Setenv("WORKER_YIELD", "true")
	defer func() {
		if recover() == nil {
			t.Fatal("ambiguous worker yield setting accepted")
		}
	}()
	booleanEnv("WORKER_YIELD", false)
}
