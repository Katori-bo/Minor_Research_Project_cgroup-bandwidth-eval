FROM golang:1.26.1-alpine AS build
WORKDIR /src
COPY go.mod *.go ./
RUN go test -count=1 ./... && CGO_ENABLED=0 go build -trimpath -o /loadgen .
FROM scratch
COPY --from=build /loadgen /loadgen
