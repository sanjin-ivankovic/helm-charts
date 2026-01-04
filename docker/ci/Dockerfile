# syntax=docker/dockerfile:1

# Base image version (can be overridden at build time)
# renovate: datasource=docker depName=alpine/helm
ARG HELM_VERSION=4.0.4

FROM alpine/helm:${HELM_VERSION}

# Metadata
LABEL maintainer="maintainer@example.com"
LABEL description="CI tools for Helm charts repository pipeline"
LABEL org.opencontainers.image.source="https://registry.example.com/homelab/helm-charts"

# Install all pipeline dependencies
RUN apk add --no-cache \
    git \
    bash \
    yq \
    curl \
    coreutils \
    make \
    python3 \
    py3-pip \
    shellcheck \
    openssh-client \
    ca-certificates

# Install Python packages for pipeline generation and sanitization
RUN pip3 install --no-cache-dir --break-system-packages \
    'pyyaml>=6.0.1' \
    'tqdm>=4.66.0'

# Verify all tools are installed
RUN echo "=== Installed Tools ===" && \
    echo "helm: $(helm version --short)" && \
    echo "git: $(git --version)" && \
    echo "bash: $(bash --version | head -n1)" && \
    echo "yq: $(yq --version)" && \
    echo "curl: $(curl --version | head -n1)" && \
    echo "make: $(make --version | head -n1)" && \
    echo "python3: $(python3 --version)" && \
    echo "pip3: $(pip3 --version)" && \
    echo "pyyaml: $(pip3 show pyyaml | grep Version)" && \
    echo "shellcheck: $(shellcheck --version | grep ^version:)" && \
    echo "======================="

WORKDIR /workspace

ENTRYPOINT []
CMD ["/bin/bash"]
