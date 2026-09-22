package main

import (
 "testing"
)

func TestPercentilesSmallAndTail(t *testing.T) {
 if got := computeSummary(nil); got.Count != 0 { t.Fatal(got) }
 values := make([]int64, 100)
 for i := range values { values[i] = int64(100-i)*1000000 }
 got := computeSummary(values)
 if got.P50Ms != 50 || got.P95Ms != 95 || got.P99Ms != 99 || got.MaxMs != 100 {
  t.Fatalf("incorrect percentiles: %+v", got)
 }
}
