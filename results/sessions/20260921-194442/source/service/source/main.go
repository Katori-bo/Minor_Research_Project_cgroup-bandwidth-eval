package main

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"flag"
	"fmt"
	"log"
	"net/http"
	"os"
	"runtime"
	"strconv"
	"sync/atomic"
)

type Job struct {
	Iterations int
	RespChan   chan JobResult
}

type JobResult struct {
	Status int
	Body   []byte
}

var (
	queueCapacity    int
	workerCount      int
	defaultIterCount int
	jobQueue         chan Job
	totalCompleted   uint64
	queueFullDrops   uint64
)

func cpuWork(iterations int) [32]byte {
	// Seed 32 bytes
	var state [32]byte
	for i := 0; i < 32; i++ {
		state[i] = byte(i)
	}

	// Repeated SHA-256 computation
	for i := 0; i < iterations; i++ {
		state = sha256.Sum256(state[:])
	}
	return state
}

func worker(id int) {
	for job := range jobQueue {
		digest := cpuWork(job.Iterations)
		atomic.AddUint64(&totalCompleted, 1)

		resp := JobResult{
			Status: http.StatusOK,
			Body:   []byte(fmt.Sprintf("OK: iter=%d digest=%s\n", job.Iterations, hex.EncodeToString(digest[:8]))),
		}
		job.RespChan <- resp
	}
}

func workHandler(w http.ResponseWriter, r *http.Request) {
	iter := defaultIterCount
	if q := r.URL.Query().Get("iterations"); q != "" {
		if val, err := strconv.Atoi(q); err == nil && val > 0 {
			iter = val
		}
	}

	respChan := make(chan JobResult, 1)
	job := Job{
		Iterations: iter,
		RespChan:   respChan,
	}

	select {
	case jobQueue <- job:
		res := <-respChan
		w.Header().Set("Content-Type", "text/plain")
		w.WriteHeader(res.Status)
		w.Write(res.Body)
	default:
		atomic.AddUint64(&queueFullDrops, 1)
		w.Header().Set("Retry-After", "1")
		w.WriteHeader(http.StatusServiceUnavailable)
		w.Write([]byte("503 Service Unavailable: Queue Full\n"))
	}
}

func healthHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(map[string]interface{}{
		"status":           "ok",
		"workers":          workerCount,
		"gomaxprocs":       runtime.GOMAXPROCS(0),
		"queue_cap":        queueCapacity,
		"queue_len":        len(jobQueue),
		"total_completed":  atomic.LoadUint64(&totalCompleted),
		"queue_full_drops": atomic.LoadUint64(&queueFullDrops),
	})
}

func main() {
	port := flag.Int("port", 8080, "HTTP server port")
	workers := flag.Int("workers", 1, "Number of worker goroutines")
	queueSize := flag.Int("queue-size", 128, "Bounded job queue capacity")
	defaultIter := flag.Int("default-iterations", 50000, "Default SHA256 iterations")
	flag.Parse()

	// Check environment variable overrides
	if envWorkers := os.Getenv("WORKERS"); envWorkers != "" {
		if val, err := strconv.Atoi(envWorkers); err == nil && val > 0 {
			*workers = val
		}
	}
	if envIter := os.Getenv("DEFAULT_ITERATIONS"); envIter != "" {
		if val, err := strconv.Atoi(envIter); err == nil && val > 0 {
			*defaultIter = val
		}
	}
	if envQueue := os.Getenv("QUEUE_SIZE"); envQueue != "" {
		if val, err := strconv.Atoi(envQueue); err == nil && val > 0 {
			*queueSize = val
		}
	}

	// Fix GOMAXPROCS explicitly to 2 as specified
	runtime.GOMAXPROCS(2)

	workerCount = *workers
	queueCapacity = *queueSize
	defaultIterCount = *defaultIter
	jobQueue = make(chan Job, queueCapacity)

	for i := 0; i < workerCount; i++ {
		go worker(i)
	}

	log.Printf("Starting research-service on :%d (workers=%d, queue_size=%d, default_iter=%d, GOMAXPROCS=%d)",
		*port, workerCount, queueCapacity, defaultIterCount, runtime.GOMAXPROCS(0))

	http.HandleFunc("/work", workHandler)
	http.HandleFunc("/health", healthHandler)

	server := &http.Server{
		Addr: fmt.Sprintf(":%d", *port),
	}

	if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
		log.Fatalf("Server listen failed: %v", err)
	}
}

