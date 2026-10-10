package main

// Included only in the isolated completion-boundary qualification build.
// Slots are allocated before warmup, addressed by offered request ID, and read
// under service.mu. No buffer wrap or silent overwrite is allowed.
import "time"

const completionCapacity = 32768

type completionBoundary struct {
	ID uint64 `json:"id"`
	RecordStartNS int64 `json:"record_start_ns"`
	RecordLockNS int64 `json:"record_lock_ns"`
	RecordEndNS int64 `json:"record_end_ns"`
	PublishStartNS int64 `json:"publish_start_ns"`
	PublishEndNS int64 `json:"publish_end_ns"`
}

type completionSlot struct {
	seen, workerReady, handlerReady, entryReady bool
	worker event
	handler handlerEvent
	entry entryEvent
	boundary completionBoundary
}

func (s *service) configureCompletion(mode string) {
	if mode != "locked" && mode != "bounded" { panic("invalid completion recorder") }
	s.recorderMode = mode
	s.completionSlots = make([]completionSlot, completionCapacity)
}

// Export only finalized worker records. Live metrics cannot expose an event
// before publication has been recorded and its completed counter committed.
func (s *service) completionSnapshot(snapshot map[string]any, includeEvents bool) {
	snapshot["completion_protocol"] = "publication-brackets-v1"
	snapshot["recorder_mode"] = s.recorderMode
	snapshot["record_capacity"] = len(s.completionSlots)
	snapshot["record_errors"] = s.recordErrors
	if !includeEvents { return }
	boundaries := []completionBoundary{}
	workers := []event{}
	handlers := []handlerEvent{}
	entries := []entryEvent{}
	for i := range s.completionSlots {
		slot := &s.completionSlots[i]
		if slot.workerReady {
			boundaries = append(boundaries, slot.boundary)
			if s.recorderMode == "bounded" { workers = append(workers, slot.worker) }
		}
		if slot.handlerReady { handlers = append(handlers, slot.handler) }
		if slot.entryReady { entries = append(entries, slot.entry) }
	}
	if s.recorderMode == "bounded" {
		snapshot["events"], snapshot["handler_events"], snapshot["entry_events"] = workers, handlers, entries
	} else {
		// The ordinary event append precedes publication; filter unfinished
		// events for the same completed/event invariant as the legacy service.
		for _, e := range s.events {
			if s.completionSlots[e.ID].workerReady { workers = append(workers, e) }
		}
		snapshot["events"] = workers
	}
	snapshot["completion_events"] = boundaries
}

func (s *service) completionRunJob(j job, finishRegion func()) {
	var start, finish time.Time
	if s.instrument { start = time.Now() }
	digest := work(j.iterations)
	if finishRegion != nil { finishRegion() }
	if s.instrument { finish = time.Now() }
	gone := j.context.Err() != nil
	answer := result{depth: j.depth, digest: digest}
	if s.instrument {
		answer.queueNS = start.Sub(j.admitted).Nanoseconds()
		answer.processingNS = finish.Sub(start).Nanoseconds()
		answer.finished = finish
	}
	b := completionBoundary{ID: j.id, RecordStartNS: time.Since(s.origin).Nanoseconds()}
	s.mu.Lock()
	b.RecordLockNS = time.Since(s.origin).Nanoseconds()
	if s.instrument {
		e := event{j.id, j.admitted.Sub(s.origin).Nanoseconds(), start.Sub(s.origin).Nanoseconds(),
			finish.Sub(s.origin).Nanoseconds(), answer.queueNS, answer.processingNS, j.depth, gone}
		if s.recorderMode == "bounded" { s.completionSlots[j.id].worker = e } else { s.events = append(s.events, e) }
	}
	s.mu.Unlock()
	b.RecordEndNS = time.Since(s.origin).Nanoseconds()
	b.PublishStartNS = time.Since(s.origin).Nanoseconds()
	j.reply <- answer // Preserve buffered publication; cancellation never blocks a worker.
	b.PublishEndNS = time.Since(s.origin).Nanoseconds()
	s.mu.Lock()
	if s.instrument {
		s.completionSlots[j.id].boundary = b
		s.completionSlots[j.id].workerReady = true
	}
	// Drain waits for publication evidence as well as main computation.
	s.completed++
	if gone { s.abandoned++ }
	s.mu.Unlock()
}
