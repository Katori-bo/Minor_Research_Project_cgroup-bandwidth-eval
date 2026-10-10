ARG COMPILER_IMAGE
FROM ${COMPILER_IMAGE} AS build
WORKDIR /src
COPY go.mod *.go ./
RUN go version && go test -count=1 -v ./...
ARG MODE=passive
RUN CGO_ENABLED=0 go build -trimpath -ldflags="-X main.defaultAblationMode=${MODE}" -o /server .
FROM scratch
LABEL research.runtime.variant="stock" research.study="observer-ablation-v1"
COPY --from=build /server /server
ENTRYPOINT ["/server"]
