package main

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"os"
	"runtime"
	"strconv"
	"syscall"
	"time"
	"unsafe"
)

// This function must match the retained service function byte for byte.
func work(n int) [32]byte {
	var state [32]byte
	for i := range state {
		state[i] = byte(i)
	}
	for i := 0; i < n; i++ {
		state = sha256.Sum256(state[:])
	}
	return state
}

func clockNS(id uintptr) int64 {
	var ts syscall.Timespec
	_, _, err := syscall.RawSyscall(syscall.SYS_CLOCK_GETTIME, id, uintptr(unsafe.Pointer(&ts)), 0)
	if err != 0 {
		panic(err)
	}
	return ts.Sec*1e9 + ts.Nsec
}

func emit(value interface{}) {
	if err := json.NewEncoder(os.Stdout).Encode(value); err != nil {
		panic(err)
	}
}

func awaitToken(name string) {
	f, err := os.Open("/qualification/" + name + ".fifo")
	if err != nil {
		panic(err)
	}
	var token [1]byte
	n, err := f.Read(token[:])
	f.Close()
	if n != 1 || err != nil || token[0] != 'G' {
		panic("invalid FIFO token")
	}
}

type sample struct {
	Event       string `json:"event"`
	Jobs        int64  `json:"jobs"`
	Digest      string `json:"digest"`
	StartNS     int64  `json:"start_monotonic_ns"`
	StopNS      int64  `json:"stop_monotonic_ns"`
	CPUStartNS  int64  `json:"cpu_start_ns"`
	CPUStopNS   int64  `json:"cpu_stop_ns"`
	Iterations  int    `json:"iterations"`
	DurationMS  int    `json:"duration_ms"`
	GoVersion   string `json:"go_version"`
	GOMAXPROCS  int    `json:"gomaxprocs"`
}

func compute(event string, durationMS int) sample {
	s := sample{Event: event, Iterations: 44000, DurationMS: durationMS,
		GoVersion: runtime.Version(), GOMAXPROCS: runtime.GOMAXPROCS(0)}
	// CPU includes all threads in this Go process. There is no per-job timer,
	// allocation, result channel, HTTP handling or profiling in this loop.
	s.CPUStartNS = clockNS(2) // CLOCK_PROCESS_CPUTIME_ID
	s.StartNS = clockNS(1)    // CLOCK_MONOTONIC, shared host clock namespace
	until := time.Now().Add(time.Duration(durationMS) * time.Millisecond)
	var digest [32]byte
	for time.Now().Before(until) {
		digest = work(44000)
		s.Jobs++
	}
	s.StopNS = clockNS(1)
	s.CPUStopNS = clockNS(2)
	s.Digest = hex.EncodeToString(digest[:])
	runtime.KeepAlive(digest)
	return s
}

func milliseconds(name string) int {
	n, err := strconv.Atoi(os.Getenv(name))
	if err != nil || n < 1 || n > 60000 {
		panic("invalid duration: " + name)
	}
	return n
}

func main() {
	if runtime.Version() != "go1.26.1" || runtime.GOMAXPROCS(0) != 1 {
		panic("unexpected Go version or GOMAXPROCS")
	}
	warm, measure := milliseconds("MINIMAL_WARMUP_MS"), milliseconds("MINIMAL_MEASURE_MS")
	emit(map[string]interface{}{"event": "started", "go_version": runtime.Version(), "gomaxprocs": 1})
	emit(compute("warmup_done", warm))
	awaitToken("measure")
	emit(compute("measurement_done", measure))
	// Remain alive, blocked and idle, so the controller can read final cgroup
	// counters and independently verify ownership before removing the container.
	awaitToken("exit")
	fmt.Println("{\"event\":\"exiting\"}")
}
