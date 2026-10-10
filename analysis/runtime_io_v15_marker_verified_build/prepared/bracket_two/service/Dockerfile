ARG COMPILER_IMAGE
FROM ${COMPILER_IMAGE} AS build
WORKDIR /src
COPY go.mod *.go ./
RUN go version && go test -count=1 -v ./...
RUN CGO_ENABLED=0 go build -trimpath -gcflags="research-service=-m=2" -o /server .
FROM scratch
LABEL research.runtime.variant="stock" research.study="inline-clock-screen-v1"
COPY --from=build /server /server
ENTRYPOINT ["/server"]
