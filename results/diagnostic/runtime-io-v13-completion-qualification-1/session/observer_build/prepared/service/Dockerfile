ARG COMPILER_IMAGE
FROM ${COMPILER_IMAGE} AS build
ARG RECORDER=locked
WORKDIR /src
COPY go.mod *.go ./
RUN go version && go test -count=1 -v ./... && CGO_ENABLED=0 go build -ldflags="-X main.defaultCompletionRecorder=${RECORDER}" -trimpath -o /server .
FROM scratch
LABEL research.runtime.variant="stock" research.study="completion-qualification-v1"
COPY --from=build /server /server
ENTRYPOINT ["/server"]
