package main

import (
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"io"
	"math"
	"net"
	"net/http"
	"net/http/httptrace"
	"os"
	"sort"
	"strconv"
	"sync"
	"sync/atomic"
	"syscall"
	"time"
)

type RequestTask struct {
	ID                uint64
	ScheduledTime     time.Time
	ScheduledOffsetNs int64
}

type RequestResult struct {
	ID                uint64
	ScheduledOffsetNs int64
	StatusCode        int
	Error             string
	DispatchLagNs     int64
	ServiceLatencyNs  int64
	EndToEndLatencyNs int64
	QueueWaitNs int64
	ProcessingNs int64
	PreAdmissionNs int64
	PostWorkWaitNs int64
	GotConnOffsetNs int64
	WroteRequestOffsetNs int64
	FirstByteOffsetNs int64
	HeadersOffsetNs int64
	BodyDoneOffsetNs int64
	WroteRequestCount int
	TraceIssue string
	QueueDepth int
	ServerTimingPresent bool
	ServerTimingError string
	TimedOut bool
	CompletedOffsetNs int64
}

func readTiming(headers http.Header, result *RequestResult) {
	q, p, d := headers.Get("X-Queue-Wait-Ns"), headers.Get("X-Processing-Ns"), headers.Get("X-Queue-Depth")
	if q == "" && p == "" && d == "" { return }
	var err error
	if result.QueueWaitNs, err = strconv.ParseInt(q, 10, 64); err != nil || result.QueueWaitNs < 0 { result.ServerTimingError = "invalid queue time"; return }
	if result.ProcessingNs, err = strconv.ParseInt(p, 10, 64); err != nil || result.ProcessingNs <= 0 { result.ServerTimingError = "invalid processing time"; return }
	if result.QueueDepth, err = strconv.Atoi(d); err != nil || result.QueueDepth < 0 { result.ServerTimingError = "invalid depth"; return }
	pre, post := headers.Get("X-Pre-Admission-Ns"), headers.Get("X-Post-Work-Wait-Ns")
	if pre == "" || post == "" { result.ServerTimingError = "missing diagnostic server timing"; return }
	if result.PreAdmissionNs, err = strconv.ParseInt(pre, 10, 64); err != nil || result.PreAdmissionNs < 0 { result.ServerTimingError = "invalid pre-admission time"; return }
	if result.PostWorkWaitNs, err = strconv.ParseInt(post, 10, 64); err != nil || result.PostWorkWaitNs < 0 { result.ServerTimingError = "invalid post-work wait"; return }
	result.ServerTimingPresent = true
}

type LatencySummary struct {
	Count  int     `json:"count"`
	MeanMs float64 `json:"mean_ms"`
	P50Ms  float64 `json:"p50_ms"`
	P90Ms  float64 `json:"p90_ms"`
	P95Ms  float64 `json:"p95_ms"`
	P99Ms  float64 `json:"p99_ms"`
	P999Ms float64 `json:"p999_ms"`
	MaxMs  float64 `json:"max_ms"`
}

type RunReport struct {
	ClockAnchors []clockAnchor `json:"clock_anchors"`
	ClientTestStartNS int64 `json:"client_test_start_ns"`
	ElapsedIncludingDrainSec float64         `json:"elapsed_including_drain_sec"`
	SuccessfulThroughputRps  float64         `json:"successful_throughput_rps"`
	Requests                 []RequestResult `json:"requests"`
	ClientTraceEnabled       bool            `json:"client_trace_enabled"`
	ClientCPUUsec            int64           `json:"client_cpu_usec"`
	TargetURL                string          `json:"target_url"`
	Pattern                  string          `json:"pattern"`
	DurationSec              float64         `json:"duration_sec"`
	TargetRate               float64         `json:"target_rate"`
	BurstLowRate             float64         `json:"burst_low_rate,omitempty"`
	BurstHighRate            float64         `json:"burst_high_rate,omitempty"`
	BurstPeriodSec           float64         `json:"burst_period_sec,omitempty"`
	TotalScheduled           uint64          `json:"total_scheduled"`
	TotalDispatched          uint64          `json:"total_dispatched"`
	TotalCompleted           uint64          `json:"total_completed"`
	TotalSuccess             uint64          `json:"total_success"`
	Total503                 uint64          `json:"total_503"`
	TotalErrors              uint64          `json:"total_errors"`
	ClientDropped            uint64          `json:"client_dropped"`
	MissedArrivals           uint64          `json:"missed_arrivals"`
	AchievedThroughputRps    float64         `json:"achieved_throughput_rps"`
	DispatchLagSummary       LatencySummary  `json:"dispatch_lag_summary"`
	ServiceLatencySummary    LatencySummary  `json:"service_latency_summary"`
	EndToEndLatencySummary   LatencySummary  `json:"end_to_end_latency_summary"`
}

// HTTP trace callbacks may arrive concurrently or after the request returns.
// They only write this recorder; closeAndCopy freezes its values before the
// request result is sent to the collector.
type requestTrace struct {
	mu sync.Mutex
	closed bool
	gotConn, firstByte int64
	wrote []int64
}

func newRequestTrace() *requestTrace {
	return &requestTrace{gotConn: -1, firstByte: -1}
}

func (t *requestTrace) record(kind string, offset int64) {
	t.mu.Lock()
	defer t.mu.Unlock()
	if t.closed { return }
	switch kind {
	case "conn": if t.gotConn < 0 { t.gotConn = offset }
	case "write": t.wrote = append(t.wrote, offset)
	case "first": if t.firstByte < 0 { t.firstByte = offset }
	}
}

func (t *requestTrace) closeAndCopy(r *RequestResult) {
	t.mu.Lock()
	defer t.mu.Unlock()
	t.closed = true
	r.GotConnOffsetNs = t.gotConn
	r.FirstByteOffsetNs = t.firstByte
	r.WroteRequestCount = len(t.wrote)
	r.WroteRequestOffsetNs = -1
	for _, offset := range t.wrote {
		if t.firstByte >= 0 && offset <= t.firstByte && offset > r.WroteRequestOffsetNs {
			r.WroteRequestOffsetNs = offset
		}
	}
	if t.gotConn < 0 || t.firstByte < 0 || len(t.wrote) == 0 {
		r.TraceIssue = "missing_callback"
	} else if r.WroteRequestOffsetNs < 0 {
		r.TraceIssue = "write_callback_after_first_byte"
	} else if len(t.wrote) > 1 {
		r.TraceIssue = "multiple_request_writes"
	}
}

func processCPUUsec() int64 {
	var usage syscall.Rusage
	if err := syscall.Getrusage(syscall.RUSAGE_SELF, &usage); err != nil {
		return -1
	}
	return int64(usage.Utime.Sec+usage.Stime.Sec)*1_000_000 +
		int64(usage.Utime.Usec+usage.Stime.Usec)
}

func computeSummary(samples []int64) LatencySummary {
	n := len(samples)
	if n == 0 {
		return LatencySummary{}
	}
	sort.Slice(samples, func(i, j int) bool { return samples[i] < samples[j] })

	var sum int64
	for _, v := range samples {
		sum += v
	}
	mean := float64(sum) / float64(n) / 1e6

	pct := func(p float64) float64 {
		idx := int(math.Ceil(p*float64(n))) - 1
		if idx < 0 {
			idx = 0
		}
		if idx >= n {
			idx = n - 1
		}
		return float64(samples[idx]) / 1e6
	}

	return LatencySummary{
		Count:  n,
		MeanMs: mean,
		P50Ms:  pct(0.50),
		P90Ms:  pct(0.90),
		P95Ms:  pct(0.95),
		P99Ms:  pct(0.99),
		P999Ms: pct(0.999),
		MaxMs:  float64(samples[n-1]) / 1e6,
	}
}

// Invert the integrated arrival rate. This avoids accumulating rounded intervals
// or carrying the low-rate spacing across a low/high phase boundary.
func arrivalOffset(index uint64, pattern string, rate, low, high float64, period time.Duration) time.Duration {
	if pattern == "steady" {
		return time.Duration(math.Round(float64(index) / rate * 1e9))
	}
	half := period.Seconds() / 2
	perCycle := half * (low + high)
	cycle := math.Floor(float64(index) / perCycle)
	within := float64(index) - cycle*perCycle
	seconds := cycle * period.Seconds()
	if within < half*low {
		seconds += within / low
	} else {
		seconds += half + (within-half*low)/high
	}
	return time.Duration(math.Round(seconds * 1e9))
}

func main() {
	targetURL := flag.String("url", "http://127.0.0.1:8080/work", "Target URL")
	duration := flag.Duration("duration", 30*time.Second, "Workload duration")
	rate := flag.Float64("rate", 50.0, "Offered request rate (req/s) for steady pattern")
	pattern := flag.String("pattern", "steady", "Traffic pattern: 'steady' or 'bursty'")
	burstLow := flag.Float64("burst-low", 30.0, "Bursty low rate (req/s)")
	burstHigh := flag.Float64("burst-high", 70.0, "Bursty high rate (req/s)")
	burstPeriod := flag.Duration("burst-period", 10*time.Second, "Full burst cycle duration (e.g. 10s = 5s low + 5s high)")
	concurrency := flag.Int("concurrency", 128, "HTTP client worker concurrency pool")
	timeout := flag.Duration("timeout", 5*time.Second, "HTTP request timeout")
	outputFile := flag.String("output", "", "Path to write JSON results")
	traceClient := flag.Bool("trace-client", true, "Record client HTTP trace callbacks")
	flag.Parse()
	if *duration <= 0 || *timeout <= 0 || *rate <= 0 || *burstLow <= 0 || *burstHigh <= 0 || *burstPeriod <= 0 || *concurrency < 1 || (*pattern != "steady" && *pattern != "bursty") {
		fmt.Fprintln(os.Stderr, "Invalid duration, rate, concurrency or pattern")
		os.Exit(2)
	}
	if *pattern == "bursty" {
		*rate = (*burstLow + *burstHigh) / 2
	}

	transport := &http.Transport{
		Proxy: http.ProxyFromEnvironment,
		DialContext: (&net.Dialer{
			Timeout:   5 * time.Second,
			KeepAlive: 30 * time.Second,
		}).DialContext,
		MaxIdleConns:        *concurrency * 2,
		MaxIdleConnsPerHost: *concurrency * 2,
		IdleConnTimeout:     90 * time.Second,
		DisableKeepAlives:   false,
	}
	client := &http.Client{
		Transport: transport,
		Timeout:   *timeout,
	}

	taskChan := make(chan RequestTask, *concurrency*4)
	resultChan := make(chan RequestResult, 100000)

	var (
		clientDropped uint64
		workerWG      sync.WaitGroup
	)

	// Launch HTTP client worker pool
	for i := 0; i < *concurrency; i++ {
		workerWG.Add(1)
		go func() {
			defer workerWG.Done()
			for task := range taskChan {
				reqStart := time.Now()
				dispatchLag := reqStart.Sub(task.ScheduledTime).Nanoseconds()

				req, err := http.NewRequest("GET", *targetURL, nil)
				if err == nil {
					query := req.URL.Query()
					query.Set("id", strconv.FormatUint(task.ID, 10))
					req.URL.RawQuery = query.Encode()
				}
				var res RequestResult
				res.ID = task.ID
				res.ScheduledOffsetNs = task.ScheduledOffsetNs
				res.DispatchLagNs = dispatchLag
				res.GotConnOffsetNs, res.WroteRequestOffsetNs, res.FirstByteOffsetNs = -1, -1, -1

				if err != nil {
					res.Error = err.Error()
					res.ServiceLatencyNs = time.Since(reqStart).Nanoseconds()
					res.EndToEndLatencyNs = time.Since(task.ScheduledTime).Nanoseconds()
					res.CompletedOffsetNs = res.ScheduledOffsetNs + res.EndToEndLatencyNs
					resultChan <- res
					continue
				}

				var recorder *requestTrace
				if *traceClient {
					recorder = newRequestTrace()
					trace := &httptrace.ClientTrace{
						GotConn: func(httptrace.GotConnInfo) { recorder.record("conn", time.Since(reqStart).Nanoseconds()) },
						WroteRequest: func(httptrace.WroteRequestInfo) { recorder.record("write", time.Since(reqStart).Nanoseconds()) },
						GotFirstResponseByte: func() { recorder.record("first", time.Since(reqStart).Nanoseconds()) },
					}
					req = req.WithContext(httptrace.WithClientTrace(req.Context(), trace))
				} else {
					res.TraceIssue = "disabled"
				}
				resp, err := client.Do(req)
				res.HeadersOffsetNs = time.Since(reqStart).Nanoseconds()
				if err != nil {
					res.Error = err.Error()
					var timeoutErr net.Error
					res.TimedOut = errors.As(err, &timeoutErr) && timeoutErr.Timeout()
				} else {
					res.StatusCode = resp.StatusCode
					if resp.StatusCode == http.StatusOK {
						readTiming(resp.Header, &res)
					}
					_, bodyErr := io.Copy(io.Discard, resp.Body)
					resp.Body.Close()
					if bodyErr != nil {
						res.Error = bodyErr.Error()
						var timeoutErr net.Error
						res.TimedOut = errors.As(bodyErr, &timeoutErr) && timeoutErr.Timeout()
					}
				}
				reqEnd := time.Now()
				res.BodyDoneOffsetNs = reqEnd.Sub(reqStart).Nanoseconds()
				res.ServiceLatencyNs = reqEnd.Sub(reqStart).Nanoseconds()
				res.EndToEndLatencyNs = reqEnd.Sub(task.ScheduledTime).Nanoseconds()
				res.CompletedOffsetNs = res.ScheduledOffsetNs + res.EndToEndLatencyNs
				if recorder != nil { recorder.closeAndCopy(&res) }
				resultChan <- res
			}
		}()
	}

	// Result collector goroutine
	var results []RequestResult
	collectorDone := make(chan struct{})
	go func() {
		for res := range resultChan {
			results = append(results, res)
		}
		close(collectorDone)
	}()

	fmt.Printf("Starting open-loop generator: url=%s pattern=%s duration=%v\n", *targetURL, *pattern, *duration)
	if *pattern == "bursty" {
		fmt.Printf("  Burst settings: low=%.1f rps, high=%.1f rps, cycle=%v (mean=%.1f rps)\n",
			*burstLow, *burstHigh, *burstPeriod, (*burstLow+*burstHigh)/2.0)
	} else {
		fmt.Printf("  Steady rate: %.1f rps\n", *rate)
	}

	clockOrigin := time.Now()
	anchors, clockErr := clockSamples(clockOrigin, *targetURL, "start")
	if clockErr != nil { fmt.Fprintln(os.Stderr, clockErr); os.Exit(2) }
	clientCPUStart := processCPUUsec()
	testStartTime := time.Now()
	clientTestStartNS := testStartTime.Sub(clockOrigin).Nanoseconds()
	testEndTime := testStartTime.Add(*duration)
	currentScheduledTime := testStartTime

	var (
		scheduledCount  uint64
		dispatchedCount uint64
		missedArrivals  uint64
	)

	// Schedule generator loop
	for {
		now := time.Now()
		if !currentScheduledTime.Before(testEndTime) {
			break
		}

		// Account for sleep deadline
		waitDuration := currentScheduledTime.Sub(now)
		if waitDuration > 0 {
			time.Sleep(waitDuration)
		}

		actualDispatch := time.Now()
		lag := actualDispatch.Sub(currentScheduledTime)
		if lag > 10*time.Millisecond {
			missedArrivals++
		}

		task := RequestTask{
			ID:                scheduledCount,
			ScheduledTime:     currentScheduledTime,
			ScheduledOffsetNs: currentScheduledTime.Sub(testStartTime).Nanoseconds(),
		}
		scheduledCount++

		select {
		case taskChan <- task:
			dispatchedCount++
		default:
			atomic.AddUint64(&clientDropped, 1)
		}

		currentScheduledTime = testStartTime.Add(arrivalOffset(scheduledCount, *pattern, *rate, *burstLow, *burstHigh, *burstPeriod))
	}

	if remaining := time.Until(testEndTime); remaining > 0 {
		time.Sleep(remaining)
	}
	actualTestDuration := *duration

	// Close task queue and wait for workers
	close(taskChan)
	workerWG.Wait()
	close(resultChan)
	<-collectorDone
	elapsedIncludingDrain := time.Since(testStartTime).Seconds()
	clientCPUEnd := processCPUUsec()
	clientCPUUsed := int64(-1)
	if clientCPUStart >= 0 && clientCPUEnd >= clientCPUStart {
		clientCPUUsed = clientCPUEnd - clientCPUStart
	}

	stopAnchors, clockErr := clockSamples(clockOrigin, *targetURL, "stop")
	if clockErr != nil { fmt.Fprintln(os.Stderr, clockErr); os.Exit(2) }
	anchors = append(anchors, stopAnchors...)
	// Aggregate metrics
	var (
		totalSuccess uint64
		total503     uint64
		totalErrors  uint64
	)
	var lags []int64
	var serviceLats []int64
	var e2eLats []int64

	for _, r := range results {
		lags = append(lags, r.DispatchLagNs)
		if r.Error != "" {
			totalErrors++
		} else if r.StatusCode == http.StatusOK {
			totalSuccess++
			serviceLats = append(serviceLats, r.ServiceLatencyNs)
			e2eLats = append(e2eLats, r.EndToEndLatencyNs)
		} else if r.StatusCode == http.StatusServiceUnavailable {
			total503++
		} else {
			totalErrors++
		}
	}

	achievedRps := float64(len(results)) / elapsedIncludingDrain

	report := RunReport{
		ClockAnchors: anchors,
		ClientTestStartNS: clientTestStartNS,
		ElapsedIncludingDrainSec: elapsedIncludingDrain,
		SuccessfulThroughputRps:  float64(totalSuccess) / elapsedIncludingDrain,
		Requests:                 results,
		ClientTraceEnabled:       *traceClient,
		ClientCPUUsec:            clientCPUUsed,
		TargetURL:                *targetURL,
		Pattern:                  *pattern,
		DurationSec:              actualTestDuration.Seconds(),
		TargetRate:               *rate,
		BurstLowRate:             *burstLow,
		BurstHighRate:            *burstHigh,
		BurstPeriodSec:           burstPeriod.Seconds(),
		TotalScheduled:           scheduledCount,
		TotalDispatched:          dispatchedCount,
		TotalCompleted:           uint64(len(results)),
		TotalSuccess:             totalSuccess,
		Total503:                 total503,
		TotalErrors:              totalErrors,
		ClientDropped:            clientDropped,
		MissedArrivals:           missedArrivals,
		AchievedThroughputRps:    achievedRps,
		DispatchLagSummary:       computeSummary(lags),
		ServiceLatencySummary:    computeSummary(serviceLats),
		EndToEndLatencySummary:   computeSummary(e2eLats),
	}

	fmt.Printf("\n--- WORKLOAD RESULTS ---\n")
	fmt.Printf("Duration:               %.2fs\n", report.DurationSec)
	fmt.Printf("Total Scheduled:        %d\n", report.TotalScheduled)
	fmt.Printf("Total Completed:        %d (Success: %d, 503: %d, Errors: %d)\n",
		report.TotalCompleted, report.TotalSuccess, report.Total503, report.TotalErrors)
	fmt.Printf("Client Saturated Drops: %d\n", report.ClientDropped)
	fmt.Printf("Missed Arrivals (>10ms):%d\n", report.MissedArrivals)
	fmt.Printf("Achieved Throughput:    %.2f rps\n", report.AchievedThroughputRps)
	fmt.Printf("Dispatch Lag:           mean=%.3fms, p99=%.3fms, max=%.3fms\n",
		report.DispatchLagSummary.MeanMs, report.DispatchLagSummary.P99Ms, report.DispatchLagSummary.MaxMs)
	fmt.Printf("Service Latency:        p50=%.2fms, p95=%.2fms, p99=%.2fms, max=%.2fms\n",
		report.ServiceLatencySummary.P50Ms, report.ServiceLatencySummary.P95Ms, report.ServiceLatencySummary.P99Ms, report.ServiceLatencySummary.MaxMs)
	fmt.Printf("End-to-End Latency:     p50=%.2fms, p95=%.2fms, p99=%.2fms, max=%.2fms\n",
		report.EndToEndLatencySummary.P50Ms, report.EndToEndLatencySummary.P95Ms, report.EndToEndLatencySummary.P99Ms, report.EndToEndLatencySummary.MaxMs)

	if *outputFile != "" {
		data, err := json.MarshalIndent(report, "", "  ")
		if err != nil {
			fmt.Fprintf(os.Stderr, "Failed to serialize JSON: %v\n", err)
			os.Exit(1)
		}
		if err := os.WriteFile(*outputFile, data, 0644); err != nil {
			fmt.Fprintf(os.Stderr, "Failed to write output file: %v\n", err)
			os.Exit(1)
		}
		fmt.Printf("Report saved to %s\n", *outputFile)
	}
}
