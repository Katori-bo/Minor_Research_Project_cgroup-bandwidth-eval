package main

import (
	"testing"
	"time"
)

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
		got := arrivalOffset(index, "bursty", 50, 30, 70, 10*time.Second)
		if got != want {
			t.Fatalf("arrival %d: got %v want %v", index, got, want)
		}
	}
	for i := uint64(1); i < 1000; i++ {
		if arrivalOffset(i, "bursty", 50, 30, 70, 10*time.Second) <= arrivalOffset(i-1, "bursty", 50, 30, 70, 10*time.Second) {
			t.Fatal("non-increasing arrivals")
		}
	}
	if arrivalOffset(60, "steady", 60, 0, 0, 10*time.Second) != time.Second {
		t.Fatal("steady schedule drift")
	}
}
