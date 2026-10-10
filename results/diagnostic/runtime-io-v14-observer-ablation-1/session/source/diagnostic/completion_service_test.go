package main

import (
	"context"
	"net/http/httptest"
	"testing"
)

func TestCompletionRecordersConserveAndBracket(t *testing.T) {
	for _, mode := range []string{"locked", "bounded"} {
		s := newService(1, 1, true)
		s.configureCompletion(mode)
		go s.worker()
		r := httptest.NewRecorder()
		s.workHandler(r, httptest.NewRequest("GET", "/work?iterations=100&id=0", nil))
		await(t, func() bool { return s.snapshot(false)["completed"].(int)==1 })
		v := s.snapshot(true)
		e := v["events"].([]event)
		h := v["handler_events"].([]handlerEvent)
		b := v["completion_events"].([]completionBoundary)
		entries := v["entry_events"].([]entryEvent)
		if r.Code!=200 || len(e)!=1 || len(h)!=1 || len(b)!=1 || len(entries)!=1 || e[0].ID!=0 {
			t.Fatal("record conservation", mode, v)
		}
		stamps := []int64{e[0].CompletionNS,b[0].RecordStartNS,b[0].RecordLockNS,b[0].RecordEndNS,b[0].PublishStartNS,b[0].PublishEndNS}
		for i:=1;i<len(stamps);i++ { if stamps[i]<stamps[i-1] { t.Fatal("boundary ordering", b) } }
		if h[0].ResumeNS<b[0].PublishStartNS || h[0].HandlerExitNS<h[0].WriteEndNS { t.Fatal("handler boundary",h) }
		reset := httptest.NewRecorder()
		s.reset(reset,httptest.NewRequest("POST","/reset",nil))
		v=s.snapshot(true)
		if reset.Code!=204 || len(v["completion_events"].([]completionBoundary))!=0 || s.completionSlots[0].seen {
			t.Fatal("reset did not clear recorder")
		}
		close(s.queue)
	}
}

func TestCompletionCancellationRejectionAndIDErrors(t *testing.T) {
	for _, mode := range []string{"locked","bounded"} {
		s:=newService(1,1,true);s.configureCompletion(mode)
		ctx,cancel:=context.WithCancel(context.Background());cancel()
		s.workHandler(httptest.NewRecorder(),httptest.NewRequest("GET","/work?iterations=1&id=0",nil).WithContext(ctx))
		r:=httptest.NewRecorder()
		s.workHandler(r,httptest.NewRequest("GET","/work?iterations=1&id=1",nil))
		if r.Code!=503 { t.Fatal("rejection lost") }
		for _, id := range []string{"0","32768"} {
			r=httptest.NewRecorder();s.workHandler(r,httptest.NewRequest("GET","/work?iterations=1&id="+id,nil))
			if r.Code!=400 { t.Fatal("duplicate/overflow accepted",id) }
		}
		go s.worker()
		await(t,func()bool{return s.snapshot(false)["completed"].(int)==1})
		v:=s.snapshot(true)
		if len(v["events"].([]event))!=1 || len(v["completion_events"].([]completionBoundary))!=1 ||
			len(v["handler_events"].([]handlerEvent))!=0 || len(v["entry_events"].([]entryEvent))!=2 ||
			v["record_errors"].(int)!=2 || v["client_gone_at_completion"].(int)!=1 { t.Fatal("cancellation records",v) }
		close(s.queue)
	}
}
