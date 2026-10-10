// Bounded open-loop feasibility client. Completion means the full body was read.
package main

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"net/http"
	"os"
	"strconv"
	"sync"
	"time"
)

type result struct {
	ID                                             string
	ScheduledNs, DispatchNs, HeadersNs, BodyDoneNs int64
	Status                                         int
	Error                                          string
	BodyBytes                                      int
	BodySHA256                                     string
	EchoID                                         string
	QueueNs, ProcessNs                             int64
	TimingError                                    string
	ContentType                                    string
}

func main() {
	url := flag.String("url", "", "full image endpoint")
	prefix := flag.String("prefix", "", "unique request prefix")
	count := flag.Int("count", 0, "bounded offer count")
	interval := flag.Int64("interval-ns", 200000000, "integer offer spacing")
	instrument := flag.Bool("instrumented", false, "require server timings")
	flag.Parse()
	if *url == "" || *prefix == "" || *count < 1 || *count > 1000 || *interval < 1 {
		fmt.Fprintln(os.Stderr, "invalid bounded client settings")
		os.Exit(2)
	}
	transport := &http.Transport{MaxIdleConns: 32, MaxIdleConnsPerHost: 32, MaxConnsPerHost: 32, DisableCompression: true}
	defer transport.CloseIdleConnections()
	client := &http.Client{Transport: transport, Timeout: 10 * time.Second, CheckRedirect: func(_ *http.Request, _ []*http.Request) error { return http.ErrUseLastResponse }}
	rows := make([]result, *count)
	start := time.Now()
	sem := make(chan struct{}, 32)
	var wg sync.WaitGroup
	for i := 0; i < *count; i++ {
		scheduled := int64(i) * *interval
		if delay := time.Until(start.Add(time.Duration(scheduled))); delay > 0 {
			time.Sleep(delay)
		}
		id := fmt.Sprintf("%s-%d", *prefix, i)
		rows[i] = result{ID: id, ScheduledNs: scheduled, HeadersNs: -1, BodyDoneNs: -1, QueueNs: -1, ProcessNs: -1}
		select {
		case sem <- struct{}{}:
			wg.Add(1)
			go func(index int) {
				defer wg.Done()
				defer func() { <-sem }()
				r := &rows[index]
				req, err := http.NewRequest(http.MethodGet, *url, nil)
				if err != nil {
					r.Error = err.Error()
					return
				}
				req.Header.Set("X-Request-ID", r.ID)
				r.DispatchNs = time.Since(start).Nanoseconds()
				response, err := client.Do(req)
				if err != nil {
					r.Error = err.Error()
					r.BodyDoneNs = time.Since(start).Nanoseconds()
					return
				}
				r.HeadersNs = time.Since(start).Nanoseconds()
				r.Status = response.StatusCode
				r.EchoID = response.Header.Get("X-Request-ID")
				r.ContentType = response.Header.Get("Content-Type")
				body, readErr := io.ReadAll(io.LimitReader(response.Body, 4*1024*1024+1))
				r.BodyDoneNs = time.Since(start).Nanoseconds()
				response.Body.Close()
				if readErr != nil {
					r.Error = readErr.Error()
				}
				if len(body) > 4*1024*1024 {
					r.Error = "response exceeds body cap"
				}
				r.BodyBytes = len(body)
				digest := sha256.Sum256(body)
				r.BodySHA256 = hex.EncodeToString(digest[:])
				if *instrument {
					q, eq := strconv.ParseInt(response.Header.Get("X-Qualification-Queue-Ns"), 10, 64)
					p, ep := strconv.ParseInt(response.Header.Get("X-Qualification-Process-Ns"), 10, 64)
					if eq != nil || ep != nil || q < 0 || p <= 0 {
						r.TimingError = "invalid or missing timing header"
					} else {
						r.QueueNs = q
						r.ProcessNs = p
					}
				}
			}(i)
		default:
			rows[i].Error = "client in-flight cap reached"
		}
	}
	wg.Wait()
	if err := json.NewEncoder(os.Stdout).Encode(struct {
		Schema     string
		Count      int
		IntervalNs int64
		Rows       []result
	}{"imgproxy-client-v1", *count, *interval, rows}); err != nil {
		os.Exit(1)
	}
}
