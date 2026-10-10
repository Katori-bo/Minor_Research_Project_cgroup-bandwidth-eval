package main

import (
	"context"
	"net/http/httptest"
	"strconv"
	"sync"
	"testing"
)

func TestAblationCancellationResetAndNoOverwrite(t *testing.T) {
	for _,mode:=range []string{"clocks","passive","mutex_early","mutex_late"} {
		s:=newService(1,1,true);s.configureAblation(mode)
		ctx,cancel:=context.WithCancel(context.Background());cancel()
		s.workHandler(httptest.NewRecorder(),httptest.NewRequest("GET","/work?iterations=1&id=0",nil).WithContext(ctx))
		r:=httptest.NewRecorder();s.reset(r,httptest.NewRequest("POST","/reset",nil))
		if r.Code!=409 { t.Fatal("reset discarded queued work",mode) }
		r=httptest.NewRecorder();s.workHandler(r,httptest.NewRequest("GET","/work?iterations=1&id=1",nil))
		if r.Code!=503 { t.Fatal("rejection changed",mode) }
		go s.worker()
		await(t,func()bool{ v:=s.snapshot(false);return v["completed"].(int)==1 && v["observer_pending_records"].(int)==0 })
		v:=s.snapshot(true)
		if len(v["events"].([]event))!=1 || len(v["entry_events"].([]entryEvent))!=2 || len(v["handler_events"].([]handlerEvent))!=0 || v["client_gone_at_completion"].(int)!=1 { t.Fatal("cancelled outcome lost",mode,v) }
		r=httptest.NewRecorder();s.reset(r,httptest.NewRequest("POST","/reset",nil))
		if r.Code!=204 { t.Fatal("drained reset refused",mode) }
		// Reuse ID zero after reset, preserving the already-started worker.
		r=httptest.NewRecorder();s.workHandler(r,httptest.NewRequest("GET","/work?iterations=10&id=0",nil))
		await(t,func()bool{return s.snapshot(false)["observer_pending_records"].(int)==0})
		v=s.snapshot(true)
		if r.Code!=200 || len(v["events"].([]event))!=1 { t.Fatal("new generation",mode,v) }
		if mode!="clocks" {
			bs:=v["completion_events"].([]ablationBoundary)
			if len(bs)!=1 || bs[0].ID!=0 { t.Fatal("buffer reset failed",mode,bs) }
			b:=bs[0];stamps:=[]int64{v["events"].([]event)[0].CompletionNS,b.RecordStartNS,b.RecordLockNS,b.RecordEndNS,b.PublishStartNS,b.PublishEndNS}
			for i:=1;i<len(stamps);i++ { if stamps[i]<stamps[i-1] { t.Fatal("boundary order",mode,b) } }
		} else if _,ok:=v["completion_events"];ok { t.Fatal("clock-only stores records") }
		close(s.queue)
	}
}

func TestAblationConcurrentMetricsAndResetGenerations(t *testing.T) {
	for _,mode:=range []string{"passive","mutex_early","mutex_late"} {
		s:=newService(4,128,true);s.configureAblation(mode)
		for i:=0;i<4;i++ { go s.worker() }
		stop:=make(chan struct{});done:=make(chan struct{})
		go func(){defer close(done);for { select {case <-stop:return;default:s.snapshot(true)} }}()
		for epoch:=0;epoch<2;epoch++ {
			var clients sync.WaitGroup
			for i:=0;i<80;i++ { clients.Add(1);go func(id int){defer clients.Done();r:=httptest.NewRecorder();s.workHandler(r,httptest.NewRequest("GET","/work?iterations=100&id="+strconv.Itoa(id),nil));if r.Code!=200 { t.Errorf("response changed: %s %d",mode,r.Code) }}(i) }
			clients.Wait()
			await(t,func()bool{v:=s.snapshot(false);return v["completed"].(int)==80 && v["active_handlers"].(int)==0 && v["observer_pending_records"].(int)==0})
			v:=s.snapshot(true)
			if len(v["completion_events"].([]ablationBoundary))!=80 || len(v["events"].([]event))!=80 || v["observer_dropped_records"].(uint64)!=0 { t.Fatal("record conservation",mode) }
			r:=httptest.NewRecorder();s.reset(r,httptest.NewRequest("POST","/reset",nil));if r.Code!=204 {t.Fatal("reset failed",mode)}
		}
		close(stop);<-done;close(s.queue)
	}
}

func TestAblationOverflowDoesNotBlockOrOverwrite(t *testing.T) {
	s:=newService(1,2,true);s.configureAblation("passive")
	s.ablation.buffers[0].values=make([]ablationBoundary,1)
	go s.worker()
	for i:=0;i<2;i++ {r:=httptest.NewRecorder();s.workHandler(r,httptest.NewRequest("GET","/work?iterations=1&id="+strconv.Itoa(i),nil));if r.Code!=200 {t.Fatal("overflow changed response")}}
	await(t,func()bool{return s.ablation.dropped.Load()==1})
	v:=s.snapshot(true);bs:=v["completion_events"].([]ablationBoundary)
	if len(bs)!=1 || bs[0].ID!=0 || v["completed"].(int)!=2 || v["observer_pending_records"].(int)!=0 {t.Fatal("overflow was hidden or stranded",v)}
	close(s.queue)
}

func TestAblationResetWaitsForRecordCommit(t *testing.T) {
	s:=newService(1,1,true);s.configureAblation("passive")
	s.admitted,s.completed=1,1
	r:=httptest.NewRecorder();s.reset(r,httptest.NewRequest("POST","/reset",nil))
	if r.Code!=409 {t.Fatal("reset raced incomplete publication record")}
	s.ablation.store(&s.ablation.buffers[0],ablationBoundary{ID:0})
	r=httptest.NewRecorder();s.reset(r,httptest.NewRequest("POST","/reset",nil))
	if r.Code!=204 {t.Fatal("finalized records should allow reset")}
}
