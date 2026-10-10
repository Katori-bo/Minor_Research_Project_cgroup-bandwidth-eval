package main

import (
    "context"
    "net/http/httptest"
    "strconv"
    "sync"
    "testing"
)

// Reset may follow handler exit while a worker is sampling the post-send
// marker. Those samples must use a cached origin, with no reset race.
func TestMarkerConcurrentResetAndLiveSnapshots(t *testing.T) {
    s:=newService(4,128,true)
    for i:=0;i<4;i++ { go s.worker() }
    stop,done:=make(chan struct{}),make(chan struct{})
    go func(){defer close(done);for {select {case <-stop:return;default:s.snapshot(true)}}}()
    for epoch:=0;epoch<10;epoch++ {
        var clients sync.WaitGroup
        for i:=0;i<64;i++ { clients.Add(1);go func(id int){defer clients.Done()
            r:=httptest.NewRecorder();s.workHandler(r,httptest.NewRequest("GET","/work?iterations=100&id="+strconv.Itoa(id),nil))
            if r.Code!=200 {t.Errorf("marker changed response: %d",r.Code)}
        }(i) }
        clients.Wait()
        v:=s.snapshot(true)
        if v["completed"].(int)!=64 || len(v["events"].([]event))!=64 || len(v["handler_events"].([]handlerEvent))!=64 || len(v["entry_events"].([]entryEvent))!=64 { t.Fatal("outcome conservation",v) }
        if _,ok:=v["completion_events"];ok {t.Fatal("clock screen stores records")}
        r:=httptest.NewRecorder();s.reset(r,httptest.NewRequest("POST","/reset",nil))
        if r.Code!=204 {t.Fatal("reset after handler drain failed",r.Code)}
    }
    close(stop);<-done;close(s.queue)
}

func TestMarkerCancellationAndQueueRejection(t *testing.T) {
    s:=newService(1,1,true)
    ctx,cancel:=context.WithCancel(context.Background());cancel()
    s.workHandler(httptest.NewRecorder(),httptest.NewRequest("GET","/work?iterations=1&id=0",nil).WithContext(ctx))
    r:=httptest.NewRecorder();s.reset(r,httptest.NewRequest("POST","/reset",nil))
    if r.Code!=409 {t.Fatal("reset discarded queued cancelled job")}
    r=httptest.NewRecorder();s.workHandler(r,httptest.NewRequest("GET","/work?iterations=1&id=1",nil))
    if r.Code!=503 {t.Fatal("queue rejection changed",r.Code)}
    go s.worker()
    await(t,func()bool{return s.snapshot(false)["completed"].(int)==1})
    v:=s.snapshot(true)
    if v["client_gone_at_completion"].(int)!=1 || len(v["events"].([]event))!=1 || len(v["entry_events"].([]entryEvent))!=2 {t.Fatal("cancelled/rejected evidence lost")}
    close(s.queue)
}
