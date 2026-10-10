// Bounded open-loop feasibility client. Completion means the full body was read.
package main

import (
	"bytes"
	"compress/gzip"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"net/http"
	"os"
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
	ContentEncoding, DecodedSHA256, DecodeError    string
	DecodedBytes                                   int
}

func main() {
	url := flag.String("url", "", "stock NGINX compression endpoint")
	prefix := flag.String("prefix", "", "unique request prefix")
	count := flag.Int("count", 0, "bounded offer count")
	interval := flag.Int64("interval-ns", 200000000, "integer offer spacing")

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
				req.Header.Set("Accept-Encoding", "gzip")
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
				r.ContentEncoding = response.Header.Get("Content-Encoding")
				body, readErr := io.ReadAll(io.LimitReader(response.Body, 2*1024*1024+1))
				r.BodyDoneNs = time.Since(start).Nanoseconds()
				response.Body.Close()
				if readErr != nil {
					r.Error = readErr.Error()
				}
				if len(body) > 2*1024*1024 {
					r.Error = "response exceeds body cap"
				}
				r.BodyBytes = len(body)
				digest := sha256.Sum256(body)
				r.BodySHA256 = hex.EncodeToString(digest[:])
				decoder, decodeErr := gzip.NewReader(bytes.NewReader(body))
				if decodeErr != nil {
					r.DecodeError = decodeErr.Error()
				} else {
					decoded, decodeErr := io.ReadAll(io.LimitReader(decoder, 2*1024*1024+1))
					closeErr := decoder.Close()
					if decodeErr != nil {
						r.DecodeError = decodeErr.Error()
					}
					if closeErr != nil {
						r.DecodeError = closeErr.Error()
					}
					if len(decoded) > 2*1024*1024 {
						r.DecodeError = "decoded body exceeds cap"
					}
					r.DecodedBytes = len(decoded)
					digest := sha256.Sum256(decoded)
					r.DecodedSHA256 = hex.EncodeToString(digest[:])
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
	}{"nginx-client-v1", *count, *interval, rows}); err != nil {
		os.Exit(1)
	}
}
