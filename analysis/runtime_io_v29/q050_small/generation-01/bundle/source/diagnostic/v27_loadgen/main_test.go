package main

import (
	"sync"
	"testing"
	"time"
)

func TestTraceRecorderFreezesConcurrentCallbacks(t *testing.T) {
	trace := newRequestTrace()
	var workers sync.WaitGroup
	for i := 0; i < 32; i++ {
		workers.Add(1)
		go func(offset int64) {
			defer workers.Done()
			trace.record("write", offset)
		}(int64(i))
	}
	workers.Wait()
	trace.record("conn", 1)
	trace.record("first", 40)
	var result RequestResult
	trace.closeAndCopy(&result)
	if result.WroteRequestCount != 32 || result.WroteRequestOffsetNs != 31 ||
		result.FirstByteOffsetNs != 40 || result.TraceIssue != "multiple_request_writes" {
		t.Fatal(result)
	}
	trace.record("write", 50) // A callback after completion cannot mutate the saved result.
	if result.WroteRequestCount != 32 || result.WroteRequestOffsetNs != 31 { t.Fatal(result) }
}

func TestTraceRecorderClassifiesOutOfOrderCallbacks(t *testing.T) {
	trace := newRequestTrace()
	trace.record("conn", 1)
	trace.record("first", 4)
	trace.record("write", 5)
	var result RequestResult
	trace.closeAndCopy(&result)
	if result.TraceIssue != "write_callback_after_first_byte" || result.WroteRequestOffsetNs != -1 {
		t.Fatal(result)
	}
}

func TestPercentilesSmallAndTail(t *testing.T) {
	if got := computeSummary(nil); got.Count != 0 {
		t.Fatal(got)
	}
	values := make([]int64, 100)
	for i := range values {
		values[i] = int64(100-i) * 1000000
	}
	got := computeSummary(values)
	if got.P50Ms != 50 || got.P95Ms != 95 || got.P99Ms != 99 || got.MaxMs != 100 {
		t.Fatalf("incorrect percentiles: %+v", got)
	}
}

func TestArrivalScheduleMatchesPhaseBoundaries(t *testing.T) {
	for index, want := range map[uint64]time.Duration{0: 0, 150: 5 * time.Second, 500: 10 * time.Second, 650: 15 * time.Second, 1000: 20 * time.Second} {
		got := arrivalOffset(index, "bursty", 50, 30, 70, 10*time.Second, 5*time.Second)
		if got != want {
			t.Fatalf("arrival %d: got %v want %v", index, got, want)
		}
	}
	for i := uint64(1); i < 1000; i++ {
		if arrivalOffset(i, "bursty", 50, 30, 70, 10*time.Second, 5*time.Second) <= arrivalOffset(i-1, "bursty", 50, 30, 70, 10*time.Second, 5*time.Second) {
			t.Fatal("non-increasing arrivals")
		}
	}
	if arrivalOffset(60, "steady", 60, 0, 0, 10*time.Second, 5*time.Second) != time.Second {
		t.Fatal("steady schedule drift")
	}
}

func TestTimingMissingAndMalformedAreDistinct(t *testing.T) {
    missing := RequestResult{}
    readTiming(nil, &missing)
    if missing.ServerTimingPresent || missing.ServerTimingError != "" { t.Fatal(missing) }
    malformed := RequestResult{}
    readTiming(map[string][]string{"X-Queue-Wait-Ns": {"oops"}}, &malformed)
    if malformed.ServerTimingPresent || malformed.ServerTimingError == "" { t.Fatal(malformed) }
    valid := RequestResult{}
    readTiming(map[string][]string{"X-Queue-Wait-Ns": {"0"}, "X-Processing-Ns": {"100"},
        "X-Queue-Depth": {"2"}, "X-Pre-Admission-Ns": {"3"}, "X-Post-Work-Wait-Ns": {"4"}}, &valid)
    if !valid.ServerTimingPresent || valid.QueueWaitNs != 0 || valid.ProcessingNs != 100 ||
        valid.QueueDepth != 2 || valid.PreAdmissionNs != 3 || valid.PostWorkWaitNs != 4 { t.Fatal(valid) }
}

func TestV27ExactUnequalCycleIntegerOracleAndIdenticalHighOffers(t *testing.T) {
 for _, low := range []int64{15, 30} {
  count := uint64(0)
  for cycle := int64(0); cycle < 4; cycle++ {
   for j := int64(0); j < 10*low; j++ {
    want := cycle*15000000000 + (2*j*1000000000+low)/(2*low)
    got := arrivalOffset(count, "bursty", 1, float64(low), 169.8, 15*time.Second, 10*time.Second)
    if int64(got) != want { t.Fatalf("low %d index %d got %d want %d", low,count,got,want) }; count++
   }
   for j := int64(0); j < 849; j++ {
    want := cycle*15000000000 + 10000000000 + (2*j*5000000000+849)/(2*849)
    got := arrivalOffset(count, "bursty", 1, float64(low), 169.8, 15*time.Second, 10*time.Second)
    if int64(got) != want { t.Fatalf("high %d index %d got %d want %d", low,count,got,want) }; count++
   }
  }
  if got := arrivalOffset(count, "bursty", 1, float64(low), 169.8, 15*time.Second, 10*time.Second); got != 60*time.Second { t.Fatal(got) }
 }
}
