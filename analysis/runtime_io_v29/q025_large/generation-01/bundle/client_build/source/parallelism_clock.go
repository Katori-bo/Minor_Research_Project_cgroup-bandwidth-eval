package main

// Clock round trips occur before offered arrivals and after client drain.
import (
    "encoding/json"
    "fmt"
    "net/http"
    "net/url"
    "time"
)

type clockAnchor struct {
    Label string `json:"label"`
    BeforeNS int64 `json:"before_ns"`
    AfterNS int64 `json:"after_ns"`
    ServerNS int64 `json:"server_ns"`
    Generation uint64 `json:"generation"`
}

func clockSamples(origin time.Time, target, phase string) ([]clockAnchor, error) {
    u, err := url.Parse(target)
    if err != nil { return nil, err }
    u.Path, u.RawQuery = "/clock", ""
    // A separate connection keeps control requests out of the work transport.
    transport := &http.Transport{Proxy: nil}
    defer transport.CloseIdleConnections()
    client := &http.Client{Transport: transport, Timeout: 5*time.Second}
    anchors := make([]clockAnchor, 0, 3)
    for i := 0; i < 3; i++ {
        before := time.Since(origin).Nanoseconds()
        response, err := client.Get(u.String())
        if err != nil { return nil, err }
        var value struct {
            ServerNS *int64 `json:"server_ns"`
            Generation *uint64 `json:"generation"`
        }
        err = json.NewDecoder(response.Body).Decode(&value)
        response.Body.Close()
        after := time.Since(origin).Nanoseconds()
        if response.StatusCode != 200 || err != nil || value.ServerNS == nil ||
            value.Generation == nil || *value.ServerNS < 0 {
            return nil, fmt.Errorf("invalid clock response: status=%d error=%v", response.StatusCode, err)
        }
        anchors = append(anchors, clockAnchor{fmt.Sprintf("%s_%d", phase, i), before,
            after, *value.ServerNS, *value.Generation})
    }
    return anchors, nil
}
