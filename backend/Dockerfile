# ===================
# Standard Multi-Stage Dockerfile
# ===================
# Use this for: Local development, testing, or when you don't have pre-built binaries
# For CI/CD: Use Dockerfile.prebuilt instead (much faster, uses pre-compiled binaries)
# ===================

# ===================
# STAGE 1: Build the Go application
# ===================

FROM golang:1.25-alpine AS builder

# Set environment variable to build statically linked binary (essential for minimal images)
ENV CGO_ENABLED=0

WORKDIR /app

# Copy only go.mod and go.sum first. This allows Docker to cache dependency downloads.
COPY go.mod go.sum ./

# Download all dependencies. This step is skipped if go.mod/go.sum haven't changed.
RUN go mod download

# Copy the rest of the application source code
COPY . .

# Build argument for version injection
ARG VERSION=dev

# Build with version injection
RUN go build -ldflags "-s -w -X main.Version=${VERSION}" -o /go/bin/app ./cmd/server

# ===================
# STAGE 2: Minimal runtime image
# ===================
FROM alpine:latest

# Install any necessary certificates
RUN apk --no-cache add ca-certificates

# Create the non-root user
RUN adduser -D appuser

WORKDIR /app

# Copy the statically compiled Go binary from the builder stage
COPY --from=builder /go/bin/app /app

# Give ownership of the binary to the non-root user
RUN chown appuser:appuser /app/app

# NOW, switch to the non-root user for security
USER appuser

# Expose the application port
EXPOSE 8080

# Command to run the application
CMD ["./app"]