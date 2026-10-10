ARG COMPILER_IMAGE
FROM ${COMPILER_IMAGE} AS stock-build
ENV CGO_ENABLED=0 GOTOOLCHAIN=local GOENV=off
WORKDIR /src
COPY service/ ./
RUN go test -count=1 ./... && go build -trimpath -o /server .

FROM ${COMPILER_IMAGE} AS patched-build
ENV CGO_ENABLED=0 GOTOOLCHAIN=local GOENV=off
COPY runtime/proc.go /usr/local/go/src/runtime/proc.go
COPY runtime/export_test.go /usr/local/go/src/runtime/export_test.go
COPY runtime/proc_test.go /usr/local/go/src/runtime/proc_test.go
WORKDIR /src
COPY service/ ./
RUN go test runtime -run '^(TestResearchPendingPreemptFairQueue|TestSchedLocalQueue|TestSchedLocalQueueSteal|TestSchedLocalQueueEmpty|TestPreemption|TestPreemptionGC|TestPreemptionAfterSyscall)$' -count=1 -timeout=180s && go test -count=1 ./... && go build -trimpath -o /server .

FROM scratch AS stock
LABEL research.runtime.variant="stock"
COPY --from=stock-build /server /server
ENTRYPOINT ["/server"]

FROM scratch AS patched
LABEL research.runtime.variant="pending-preemption-fairness-v1"
COPY --from=patched-build /server /server
ENTRYPOINT ["/server"]
