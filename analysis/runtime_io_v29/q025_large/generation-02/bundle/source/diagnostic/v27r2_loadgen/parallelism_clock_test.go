package main

import (
    "net/http"
    "net/http/httptest"
    "testing"
    "time"
)

func TestParallelismClockRoundTripBracketsAndMalformedResponse(t *testing.T) {
    for _, body := range []string{`{"server_ns":12,"generation":0}`, `{}`, `{"server_ns":-1,"generation":0}`} {
        server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
            if r.URL.Path != "/clock" || r.URL.RawQuery != "" { t.Error("bad clock URL") }
            w.Write([]byte(body))
        }))
        anchors, err := clockSamples(time.Now(), server.URL+"/work?iterations=1", "start")
        server.Close()
        if body == `{"server_ns":12,"generation":0}` {
            if err != nil || len(anchors) != 3 { t.Fatal(anchors, err) }
            for _, a := range anchors {
                if a.BeforeNS < 0 || a.AfterNS < a.BeforeNS || a.ServerNS != 12 { t.Fatal(a) }
            }
        } else if err == nil { t.Fatal("accepted malformed clock response") }
    }
}
