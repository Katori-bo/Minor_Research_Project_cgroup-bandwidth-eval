package main

import (
	"context"
	"encoding/json"
	"fmt"
	"net"
	"net/http"
	"os"
	"runtime/trace"
	"sync"
	"sync/atomic"
	"syscall"
	"time"
)

const traceLimit = 64 << 20
const ioLimit = 30000
const tracePath = "/runtime.trace"

type connKey struct{}

type ioEvent struct {
	Kind         string `json:"kind"`
	Conn         uint64 `json:"conn"`
	Request      uint64 `json:"request"`
	RequestKnown bool   `json:"request_known"`
	StartNS      int64  `json:"start_ns"`
	EndNS        int64  `json:"end_ns"`
	Bytes        int    `json:"bytes"`
	Error        string `json:"error,omitempty"`
}

// A returned Write only says that net.Conn accepted bytes. It does not prove
// the peer received them. Reads may contain partial or multiple HTTP requests.
type trackedConn struct {
	net.Conn
	id      uint64
	request atomic.Pointer[uint64]
	diag    *diagnostic
}

var _ net.Conn = (*trackedConn)(nil)
var _ syscall.Conn = (*trackedConn)(nil)

func (c *trackedConn) SyscallConn() (syscall.RawConn, error) {
	return c.Conn.(syscall.Conn).SyscallConn() // Listener supplies TCPConn.
}

func (c *trackedConn) CloseRead() error  { return c.Conn.(*net.TCPConn).CloseRead() }
func (c *trackedConn) CloseWrite() error { return c.Conn.(*net.TCPConn).CloseWrite() }

func (c *trackedConn) Read(p []byte) (int, error) {
	if !c.diag.enabled() {
		return c.Conn.Read(p)
	}
	start := time.Since(c.diag.s.origin).Nanoseconds()
	n, err := c.Conn.Read(p)
	if !c.diag.enabled() {
		return n, err
	}
	c.diag.record(ioEvent{Kind: "read", Conn: c.id, StartNS: start,
		EndNS: time.Since(c.diag.s.origin).Nanoseconds(), Bytes: n, Error: errorText(err)})
	return n, err
}

func (c *trackedConn) Write(p []byte) (int, error) {
	if !c.diag.enabled() {
		return c.Conn.Write(p)
	}
	request := c.request.Load()
	start := time.Since(c.diag.s.origin).Nanoseconds()
	n, err := c.Conn.Write(p)
	if !c.diag.enabled() {
		return n, err
	}
	event := ioEvent{Kind: "write", Conn: c.id, StartNS: start,
		EndNS: time.Since(c.diag.s.origin).Nanoseconds(), Bytes: n, Error: errorText(err)}
	if request != nil {
		event.Request, event.RequestKnown = *request, true
	}
	c.diag.record(event)
	return n, err
}

func errorText(err error) string {
	if err == nil {
		return ""
	}
	return err.Error()
}

type trackedListener struct {
	net.Listener
	diag *diagnostic
}

func (l *trackedListener) Accept() (net.Conn, error) {
	conn, err := l.Listener.Accept()
	if err != nil {
		return nil, err
	}
	id := l.diag.nextConn.Add(1)
	l.diag.mark("accept", id, nil)
	return &trackedConn{Conn: conn, id: id, diag: l.diag}, nil
}

type cappedWriter struct {
	file       *os.File
	bytes      int64
	overflow   bool
	writeError string
	mu         sync.Mutex
}

func (w *cappedWriter) Write(p []byte) (int, error) {
	w.mu.Lock()
	defer w.mu.Unlock()
	if w.overflow || w.bytes+int64(len(p)) > traceLimit {
		w.overflow = true
		return len(p), nil // Bounded file; status explicitly marks incomplete.
	}
	n, err := w.file.Write(p)
	if err != nil {
		w.writeError = err.Error()
	}
	w.bytes += int64(n)
	return n, err
}

type diagnostic struct {
	s                     *service
	captureRuntime        bool
	recordCustom          bool
	mu                    sync.Mutex
	active                atomic.Bool
	nextConn              atomic.Uint64
	pendingResponses      atomic.Int64
	events                []ioEvent
	dropped               int
	startedNS, stoppedNS  int64
	writer                *cappedWriter
	startError, stopError string
	anchors               []clockAnchor
}

type clockAnchor struct {
	Label    string `json:"label"`
	BeforeNS int64  `json:"before_ns"`
	AfterNS  int64  `json:"after_ns"`
}

func newDiagnostic(s *service) *diagnostic {
	return &diagnostic{s: s, captureRuntime: true, recordCustom: true}
}
func (d *diagnostic) enabled() bool { return d.active.Load() && d.recordCustom }

func (d *diagnostic) connContext(ctx context.Context, conn net.Conn) context.Context {
	if tracked, ok := conn.(*trackedConn); ok {
		return context.WithValue(ctx, connKey{}, tracked)
	}
	return ctx
}

func (d *diagnostic) record(e ioEvent) {
	d.mu.Lock()
	if len(d.events) < ioLimit {
		d.events = append(d.events, e)
	} else {
		d.dropped++
	}
	d.mu.Unlock()
}

func (d *diagnostic) mark(kind string, conn uint64, request *uint64) {
	if !d.enabled() {
		return
	}
	ns := time.Since(d.s.origin).Nanoseconds()
	event := ioEvent{Kind: kind, Conn: conn, StartNS: ns, EndNS: ns}
	if request != nil {
		event.Request, event.RequestKnown = *request, true
	}
	d.record(event)
}

// Go 1.26.1 HTTP/1 calls Active after readRequest (including parse errors),
// Idle after finishRequest, and Closed after finalFlush. Active is a parsing
// boundary only when followed by a valid work handler, never a packet arrival.
func (d *diagnostic) connState(conn net.Conn, state http.ConnState) {
	c := conn.(*trackedConn)
	if !d.enabled() {
		return
	}
	d.mark("conn_"+state.String(), c.id, c.request.Load())
	trace.Logf(context.Background(), "connection", "conn=%d state=%s", c.id, state.String())
	if state == http.StateIdle || state == http.StateClosed {
		if c.request.Swap(nil) != nil {
			d.pendingResponses.Add(-1)
		}
	}
}

func (d *diagnostic) reset() {
	d.mu.Lock()
	defer d.mu.Unlock()
	if d.active.Load() {
		panic("cannot reset active trace")
	}
	d.events = nil
	d.dropped = 0
	d.startedNS, d.stoppedNS = 0, 0
	d.startError, d.stopError = "", ""
	d.anchors = nil
}

// The runtime event timestamp lies between these service-local reads. The
// analyzer uses this bracket to map clocks with an explicit error interval.
func (d *diagnostic) anchor(label string) {
	before := time.Since(d.s.origin).Nanoseconds()
	trace.Log(context.Background(), "clock", label)
	after := time.Since(d.s.origin).Nanoseconds()
	d.anchors = append(d.anchors, clockAnchor{label, before, after})
}

func (d *diagnostic) start(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "POST required", 405)
		return
	}
	d.mu.Lock()
	if d.active.Load() || d.startedNS != 0 {
		d.mu.Unlock()
		http.Error(w, "trace already started", 409)
		return
	}
	d.startedNS = time.Since(d.s.origin).Nanoseconds()
	if d.captureRuntime {
		file, err := os.Create(tracePath)
		if err != nil {
			d.startError = err.Error()
			d.mu.Unlock()
			http.Error(w, err.Error(), 500)
			return
		}
		d.writer = &cappedWriter{file: file}
		if err := trace.Start(d.writer); err != nil {
			d.startError = err.Error()
			file.Close()
			d.mu.Unlock()
			http.Error(w, err.Error(), 500)
			return
		}
	}
	d.active.Store(true)
	d.anchor("start")
	d.mu.Unlock()
	w.WriteHeader(http.StatusNoContent)
}

func (d *diagnostic) stop(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "POST required", 405)
		return
	}
	d.mu.Lock()
	if !d.active.Load() {
		d.mu.Unlock()
		http.Error(w, "trace not active", 409)
		return
	}
	if d.pendingResponses.Load() != 0 {
		d.mu.Unlock()
		http.Error(w, "responses still flushing", 409)
		return
	}
	d.anchor("stop")
	d.active.Store(false)
	if d.captureRuntime {
		trace.Stop()
		if err := d.writer.file.Sync(); err != nil {
			d.stopError = err.Error()
		}
		if err := d.writer.file.Close(); err != nil {
			d.stopError = err.Error()
		}
	}
	d.stoppedNS = time.Since(d.s.origin).Nanoseconds()
	d.mu.Unlock()
	w.WriteHeader(http.StatusNoContent)
}

func (d *diagnostic) status(w http.ResponseWriter, r *http.Request) {
	d.mu.Lock()
	defer d.mu.Unlock()
	bytes := int64(0)
	overflow := false
	writeError := ""
	if d.writer != nil {
		d.writer.mu.Lock()
		bytes, overflow = d.writer.bytes, d.writer.overflow
		writeError = d.writer.writeError
		d.writer.mu.Unlock()
	}
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]any{
		"runtime_capture": d.captureRuntime, "custom_recording": d.recordCustom,
		"enabled": true, "active": d.active.Load(), "started_ns": d.startedNS,
		"stopped_ns": d.stoppedNS, "runtime_trace_path": tracePath,
		"runtime_trace_bytes": bytes, "runtime_trace_limit_bytes": traceLimit,
		"runtime_trace_overflow": overflow, "io_events": append([]ioEvent{}, d.events...),
		"io_event_limit": ioLimit, "io_events_dropped": d.dropped,
		"start_error": d.startError, "stop_error": d.stopError,
		"trace_write_error": writeError,
		"clock_anchors":     append([]clockAnchor{}, d.anchors...),
		"pending_responses": d.pendingResponses.Load(),
		"complete":          d.startedNS > 0 && d.stoppedNS >= d.startedNS && (!d.captureRuntime || bytes > 0) && !overflow && d.dropped == 0 && d.startError == "" && d.stopError == "" && writeError == "" && d.pendingResponses.Load() == 0,
		"association":       fmt.Sprintf("HTTP/1 sequential handler ID on connection; read byte framing unknown"),
	})
}
