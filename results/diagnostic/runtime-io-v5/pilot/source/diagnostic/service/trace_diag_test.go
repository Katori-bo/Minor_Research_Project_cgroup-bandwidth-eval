package main

import (
	"encoding/json"
	"errors"
	"io"
	"net"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strconv"
	"testing"
	"time"
)

// An optional export is a deterministic functional fixture, not pilot data.
// It exercises a real client timeout, queue rejection, ID zero, connection
// reuse and final flushing under the pinned runtime.
func TestTraceOutcomeFixture(t *testing.T) {
	s := newService(1, 1, true)
	s.diag = newDiagnostic(s)
	listener, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	mux := http.NewServeMux()
	mux.HandleFunc("/work", s.workHandler)
	mux.HandleFunc("/health", s.health)
	mux.HandleFunc("/trace/start", s.diag.start)
	mux.HandleFunc("/trace/stop", s.diag.stop)
	server := &http.Server{Handler: mux, ConnContext: s.diag.connContext, ConnState: s.diag.connState}
	done := make(chan struct{})
	go func() { server.Serve(&trackedListener{Listener: listener, diag: s.diag}); close(done) }()
	defer func() { server.Close(); <-done; close(s.queue) }()
	transport := &http.Transport{MaxConnsPerHost: 1}
	defer transport.CloseIdleConnections()
	client := &http.Client{Transport: transport, Timeout: time.Second}
	base := "http://" + listener.Addr().String()
	post, err := client.Post(base+"/trace/start", "", nil)
	if err != nil {
		t.Fatal(err)
	}
	post.Body.Close()
	if post.StatusCode != 204 {
		t.Fatal(post.StatusCode)
	}
	var requests []map[string]any
	request := func(id int, timeout time.Duration) {
		client.Timeout = timeout
		begin := time.Now()
		response, err := client.Get(base + "/work?iterations=100&id=" + strconv.Itoa(id))
		status := 0
		if response != nil {
			status = response.StatusCode
			_, bodyErr := io.Copy(io.Discard, response.Body)
			response.Body.Close()
			if err == nil {
				err = bodyErr
			}
		}
		timedOut := false
		var ne net.Error
		if errors.As(err, &ne) {
			timedOut = ne.Timeout()
		}
		requests = append(requests, map[string]any{"ID": id, "StatusCode": status, "Error": errorText(err),
			"TimedOut": timedOut, "EndToEndLatencyNs": time.Since(begin).Nanoseconds()})
	}
	request(2, 100*time.Millisecond) // No worker yet: admitted, then client timeout.
	await(t, func() bool { return s.snapshot(false)["active_handlers"].(int) == 0 })
	request(1, time.Second) // Queue remains full: a real 503.
	if requests[0]["TimedOut"] != true || requests[1]["StatusCode"] != 503 {
		t.Fatal(requests)
	}
	go s.worker()
	await(t, func() bool { return s.snapshot(false)["completed"].(int) == 1 })
	request(0, time.Second)
	// Reuse for a control route must not attribute its write to request zero.
	health, err := client.Get(base + "/health")
	if err != nil {
		t.Fatal(err)
	}
	io.Copy(io.Discard, health.Body)
	health.Body.Close()
	request(4, time.Second)
	if requests[2]["StatusCode"] != 200 || requests[3]["StatusCode"] != 200 {
		t.Fatal(requests)
	}
	await(t, func() bool { return s.diag.pendingResponses.Load() == 0 })
	post, err = client.Post(base+"/trace/stop", "", nil)
	if err != nil {
		t.Fatal(err)
	}
	post.Body.Close()
	if post.StatusCode != 204 {
		t.Fatal(post.StatusCode)
	}
	snapshot := httptest.NewRecorder()
	s.diag.status(snapshot, httptest.NewRequest("GET", "/trace/status", nil))
	var status map[string]any
	if err = json.Unmarshal(snapshot.Body.Bytes(), &status); err != nil {
		t.Fatal(err)
	}
	if status["complete"] != true {
		t.Fatal(status)
	}
	d := s.diag
	d.mu.Lock()
	writeCount := map[uint64]int{}
	for _, e := range d.events {
		if e.Kind == "write" && e.RequestKnown {
			writeCount[e.Request]++
		}
	}
	d.mu.Unlock()
	if writeCount[0] != 1 || writeCount[4] != 1 {
		t.Fatal("stale request association", writeCount)
	}
	if directory := os.Getenv("TRACE_TEST_OUTPUT"); directory != "" {
		if err = os.MkdirAll(directory, 0755); err != nil {
			t.Fatal(err)
		}
		data, err := os.ReadFile(tracePath)
		if err != nil {
			t.Fatal(err)
		}
		if err = os.WriteFile(filepath.Join(directory, "runtime.trace"), data, 0644); err != nil {
			t.Fatal(err)
		}
		for name, value := range map[string]any{"trace_status.json": status, "server_metrics.json": s.snapshot(true),
			"loadgen.json": map[string]any{"requests": requests}} {
			data, err = json.MarshalIndent(value, "", "  ")
			if err != nil {
				t.Fatal(err)
			}
			if err = os.WriteFile(filepath.Join(directory, name), data, 0644); err != nil {
				t.Fatal(err)
			}
		}
	}
}

type writeErrorConn struct{ net.Conn }

func (writeErrorConn) Write(p []byte) (int, error) {
	return 0, errors.New("injected socket write error")
}

func TestTraceWriteErrorAndDisabledMode(t *testing.T) {
	s := newService(1, 1, true)
	d := newDiagnostic(s)
	id := uint64(0)
	c := &trackedConn{Conn: writeErrorConn{}, id: 1, diag: d}
	c.request.Store(&id)
	d.active.Store(true)
	_, err := c.Write([]byte("body"))
	if err == nil || len(d.events) != 1 || !d.events[0].RequestKnown || d.events[0].Request != 0 || d.events[0].Error == "" {
		t.Fatal("socket error lost", d.events)
	}
	d.active.Store(false)
	c.Write([]byte("body"))
	if len(d.events) != 1 {
		t.Fatal("disabled instrumentation recorded an event")
	}
}

func TestTraceStopRejectsUndrainedResponse(t *testing.T) {
	d := newDiagnostic(newService(1, 1, true))
	d.active.Store(true)
	d.pendingResponses.Store(1)
	w := httptest.NewRecorder()
	d.stop(w, httptest.NewRequest("POST", "/trace/stop", nil))
	if w.Code != 409 || !d.active.Load() {
		t.Fatal("stopped before final flush", w.Code)
	}
}
