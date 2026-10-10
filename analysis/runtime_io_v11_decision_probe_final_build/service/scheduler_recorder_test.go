
package main
import (
    "reflect"
    "runtime"
    "testing"
)
func TestSchedulerRecorderLifecycle(t *testing.T) {
    for _, request := range []uint64{0, 42} {
        if !runtime.ResearchSchedulerStart() { t.Fatal("start refused") }
        runtime.ResearchSchedulerMark(4, request)
        runtime.Gosched()
        runtime.ResearchSchedulerStop()
        events, reserved, stopped := runtime.ResearchSchedulerSnapshot()
        if stopped <= 0 || reserved != uint64(len(events)) { t.Fatal("incomplete published capture") }
        marks := 0
        for i, e := range events {
            if e.Sequence != uint64(i+1) || e.Time > stopped { t.Fatal("invalid sequence/time") }
            if e.Kind == 4 { if e.Request != request { t.Fatal("stale capture marker") }; marks++ }
        }
        if runtime.ResearchSchedulerObservationEnabled() {
            if marks != 1 { t.Fatal("missing identity marker, including request zero") }
        } else if len(events) != 0 { t.Fatal("disabled recorder wrote events") }
        runtime.Gosched()
        again, next, stop := runtime.ResearchSchedulerSnapshot()
        if !reflect.DeepEqual(events, again) || reserved != next || stopped != stop { t.Fatal("stopped capture mutated") }
    }
}
func TestSchedulerRecorderOverflow(t *testing.T) {
    if !runtime.ResearchSchedulerStart() { t.Fatal("start refused") }
    for i := uint64(0); i <= 262144; i++ { runtime.ResearchSchedulerMark(4, i) }
    runtime.ResearchSchedulerStop()
    events, reserved, _ := runtime.ResearchSchedulerSnapshot()
    if runtime.ResearchSchedulerObservationEnabled() {
        if len(events) != 262144 || reserved <= 262144 { t.Fatal("overflow was not explicitly retained") }
    } else if reserved != 0 || len(events) != 0 { t.Fatal("disabled overflow recorder wrote events") }
}
