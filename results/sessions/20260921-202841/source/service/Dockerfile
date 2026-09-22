# Multi-stage build for minimal overhead and reproducible environment
FROM golang:1.26.1-alpine AS builder

WORKDIR /app
COPY source/go.mod ./
COPY source/main.go ./

RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-s -w" -o /research-service main.go

FROM scratch

WORKDIR /app
COPY --from=builder /research-service /app/research-service

EXPOSE 8080
ENTRYPOINT ["/app/research-service"]
