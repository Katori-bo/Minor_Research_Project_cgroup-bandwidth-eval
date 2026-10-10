ARG COMPILER_IMAGE
FROM ${COMPILER_IMAGE} AS build
WORKDIR /src
COPY go.mod *.go ./
RUN go version && go test -count=1 -v ./... && CGO_ENABLED=0 go build -trimpath -o /loadgen .
FROM scratch
LABEL research.runtime.variant="stock" research.study="bursty-parallelism-v1"
COPY --from=build /loadgen /loadgen
ENTRYPOINT ["/loadgen"]
