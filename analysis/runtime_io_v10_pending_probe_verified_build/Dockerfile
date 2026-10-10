ARG COMPILER_IMAGE
FROM ${COMPILER_IMAGE} AS control-build
ENV CGO_ENABLED=0 GOTOOLCHAIN=local GOENV=off
COPY control_runtime/proc.go /usr/local/go/src/runtime/proc.go
COPY control_runtime/export_test.go /usr/local/go/src/runtime/export_test.go
COPY control_runtime/proc_test.go /usr/local/go/src/runtime/proc_test.go
WORKDIR /src
COPY service/ ./
RUN go test -v runtime -run '^(TestResearchProbeCounters|TestResearchPendingPreemptFairQueue|TestSchedLocalQueue|TestSchedLocalQueueSteal|TestSchedLocalQueueEmpty|TestPreemption|TestPreemptionGC|TestPreemptionAfterSyscall)$' -count=1 -timeout=180s && go test -v -count=1 ./... && go build -trimpath -o /server .
FROM ${COMPILER_IMAGE} AS observed-build
ENV CGO_ENABLED=0 GOTOOLCHAIN=local GOENV=off
COPY observed_runtime/proc.go /usr/local/go/src/runtime/proc.go
COPY observed_runtime/export_test.go /usr/local/go/src/runtime/export_test.go
COPY observed_runtime/proc_test.go /usr/local/go/src/runtime/proc_test.go
WORKDIR /src
COPY service/ ./
RUN go test -v runtime -run '^(TestResearchProbeCounters|TestResearchPendingPreemptFairQueue|TestSchedLocalQueue|TestSchedLocalQueueSteal|TestSchedLocalQueueEmpty|TestPreemption|TestPreemptionGC|TestPreemptionAfterSyscall)$' -count=1 -timeout=180s && go test -v -count=1 ./... && go build -trimpath -o /server .
FROM scratch AS control
LABEL research.runtime.variant="pending-probe-control"
COPY --from=control-build /server /server
ENTRYPOINT ["/server"]
FROM scratch AS observed
LABEL research.runtime.variant="pending-probe-observed"
COPY --from=observed-build /server /server
ENTRYPOINT ["/server"]
