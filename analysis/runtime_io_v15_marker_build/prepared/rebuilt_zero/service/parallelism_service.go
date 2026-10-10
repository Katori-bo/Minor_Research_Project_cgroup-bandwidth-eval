package main

// Included only in the isolated stock parallelism build.
import (
    "encoding/json"
    "net/http"
    "time"
)

type entryEvent struct {
    ID uint64 `json:"id"`
    EntryNS int64 `json:"entry_ns"`
    ExitNS int64 `json:"exit_ns"`
    Admitted bool `json:"admitted"`
}

func (s *service) clock(w http.ResponseWriter, r *http.Request) {
    s.mu.Lock()
    stamp := time.Since(s.origin).Nanoseconds()
    generation := s.generation
    s.mu.Unlock()
    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(struct {
        ServerNS int64 `json:"server_ns"`
        Generation uint64 `json:"generation"`
    }{stamp, generation})
}
