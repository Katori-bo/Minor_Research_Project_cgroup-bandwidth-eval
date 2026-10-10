package main

import (
	"sync/atomic"
	"time"
)

var defaultAblationMode = "passive"

const ablationCapacity = 16384 // Per worker, never wrapped or silently overwritten.

type ablationBoundary struct {
	ID uint64 `json:"id"`
	RecordStartNS int64 `json:"record_start_ns"`
	RecordLockNS int64 `json:"record_lock_ns"`
	RecordEndNS int64 `json:"record_end_ns"`
	PublishStartNS int64 `json:"publish_start_ns"`
	PublishEndNS int64 `json:"publish_end_ns"`
}

// Each worker owns one buffer. Published prefixes are immutable until a drained
// reset; atomic count publication makes simultaneous metrics reads race safe.
type ablationBuffer struct {
	values []ablationBoundary
	count atomic.Uint64
}

type ablationRecorder struct {
	mode string
	buffers []ablationBuffer
	nextWorker atomic.Uint64
	dropped atomic.Uint64
}

func (s *service) configureAblation(mode string) {
	if mode!="clocks" && mode!="passive" && mode!="mutex_early" && mode!="mutex_late" { panic("invalid ablation mode") }
	a:=&ablationRecorder{mode:mode}
	if mode!="clocks" {
		a.buffers=make([]ablationBuffer,s.workers)
		for i:=range a.buffers { a.buffers[i].values=make([]ablationBoundary,ablationCapacity) }
	}
	s.ablation=a
}

func (s *service) ablationWorker() {
	a:=s.ablation
	var buffer *ablationBuffer
	if a.mode!="clocks" {
		index:=a.nextWorker.Add(1)-1
		if index>=uint64(len(a.buffers)) { panic("too many observer workers") }
		buffer=&a.buffers[index]
	}
	for j:=range s.queue { s.ablationRunJob(j,buffer) }
}

func (a *ablationRecorder) store(buffer *ablationBuffer,b ablationBoundary) {
	index:=buffer.count.Load()
	if index>=uint64(len(buffer.values)) { a.dropped.Add(1);return }
	buffer.values[index]=b
	buffer.count.Store(index+1)
}

func (s *service) ablationRunJob(j job,buffer *ablationBuffer) {
	a:=s.ablation
	origin:=s.origin // Clocks-only never reads a potentially reset origin after send.
	var start,finish time.Time
	if s.instrument { start=time.Now() }
	digest:=work(j.iterations)
	if s.instrument { finish=time.Now() }
	gone:=j.context.Err()!=nil
	answer:=result{depth:j.depth,digest:digest}
	if s.instrument {
		answer.queueNS=start.Sub(j.admitted).Nanoseconds()
		answer.processingNS=finish.Sub(start).Nanoseconds()
		answer.finished=finish
	}
	b:=ablationBoundary{ID:j.id,RecordStartNS:time.Since(origin).Nanoseconds()}
	s.mu.Lock()
	b.RecordLockNS=time.Since(origin).Nanoseconds()
	if s.instrument {
		s.events=append(s.events,event{j.id,j.admitted.Sub(origin).Nanoseconds(),start.Sub(origin).Nanoseconds(),
			finish.Sub(origin).Nanoseconds(),answer.queueNS,answer.processingNS,j.depth,gone})
	}
	// All but mutex_late retain legacy event -> counters -> unlock -> send order.
	if a.mode!="mutex_late" { s.completed++;if gone { s.abandoned++ } }
	s.mu.Unlock()
	b.RecordEndNS=time.Since(origin).Nanoseconds()
	b.PublishStartNS=time.Since(origin).Nanoseconds()
	j.reply<-answer // Original buffered handoff, including abandoned clients.
	b.PublishEndNS=time.Since(origin).Nanoseconds()
	if a.mode=="clocks" {
		// Consume stamps to retain the five calls without persistent recording.
		if b.RecordStartNS>b.RecordLockNS || b.RecordLockNS>b.RecordEndNS || b.RecordEndNS>b.PublishStartNS || b.PublishStartNS>b.PublishEndNS { panic("clock ordering") }
		return
	}
	if a.mode=="passive" { a.store(buffer,b);return }
	s.mu.Lock()
	a.store(buffer,b)
	if a.mode=="mutex_late" { s.completed++;if gone { s.abandoned++ } }
	s.mu.Unlock()
}

// Called while service.mu is held. Live reads inspect only atomically published
// immutable prefixes; final export/reset additionally require observer drain.
func (s *service) ablationPending() int {
	if s.ablation.mode=="clocks" { return 0 }
	recorded:=s.ablation.dropped.Load()
	for i:=range s.ablation.buffers { recorded+=s.ablation.buffers[i].count.Load() }
	pending:=s.completed-int(recorded)
	if pending<0 { return 0 }
	return pending
}

func (s *service) ablationSnapshot(snapshot map[string]any,includeEvents bool) {
	a:=s.ablation
	snapshot["ablation_protocol"]="worker-buffer-ablation-v1"
	snapshot["ablation_mode"]=a.mode
	snapshot["observer_pending_records"]=s.ablationPending()
	snapshot["observer_dropped_records"]=a.dropped.Load()
	snapshot["observer_capacity_per_worker"]=ablationCapacity
	if !includeEvents || a.mode=="clocks" { return }
	boundaries:=[]ablationBoundary{}
	ready:=make(map[uint64]bool)
	for i:=range a.buffers {
		buffer:=&a.buffers[i]
		for _,b:=range buffer.values[:buffer.count.Load()] { boundaries=append(boundaries,b);ready[b.ID]=true }
	}
	snapshot["completion_events"]=boundaries
	if a.mode=="mutex_late" {
		workers:=[]event{}
		for _,e:=range s.events { if ready[e.ID] { workers=append(workers,e) } }
		snapshot["events"]=workers // Preserve completed/event conservation in live reads.
	}
}

func (s *service) resetAblation() {
	for i:=range s.ablation.buffers { s.ablation.buffers[i].count.Store(0) }
	s.ablation.dropped.Store(0)
}
