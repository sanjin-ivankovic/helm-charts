# syntax=docker/dockerfile:1@sha256:ecfaec9ed6d810b56388c508f4121597bfbba70d41a6dfeee4d8cad5f295fc32
#
# helm-charts-ci — CI image for the Helm charts pipeline.
#
# THIN LAYER over the shared ci-base (homelab/ci-components): ci-base already
# carries the common toolchain (git, gitleaks, cosign, shellcheck, yamllint,
# markdownlint-cli2, pytest/pyyaml/tqdm/requests, yq, python3, nodejs, docker
# CLI, TRIVY) + the publish/sanitize tooling at /opt/ci. This image only adds
# the chart-specific tools: helm, crane, plus the apk `make`.
#
# Non-obvious by design (don't "fix" without reading the README):
#   - runs as root, no USER/HEALTHCHECK — ephemeral CI pods, root-writable cache
#   - the ci-base ref is tag@sha256:<digest> so Renovate pins the digest (a
#     ci-base rebuild lands here as a digest-bump PR, never silently)

# No `# renovate:` annotation here on purpose: the native dockerfile manager
# already sees this ARG through `FROM docker:${DOCKER_VERSION}` and maintains
# tag+digest. An annotation extracts the same line a second time, and whichever
# write loses the race logs "Cannot find replaceString in current file content".
ARG DOCKER_VERSION=29.7.2-cli@sha256:3f4743208d2338c934d7b8bcfbe1bb54c0b2355c510ad5e0f31c0c4a54bd704e

# fetcher: download + checksum-verify helm + crane, one RUN per tool so a
# single-tool Renovate bump only busts that tool's layer. curl/tar/xz live here
# only — never in the final image.
FROM docker:${DOCKER_VERSION} AS fetcher
# renovate: datasource=github-releases depName=helm/helm
ARG HELM_VERSION=4.2.4
# renovate: datasource=github-releases depName=google/go-containerregistry
ARG CRANE_VERSION=v0.22.1
RUN apk add --no-cache curl tar xz && mkdir -p /out/usr/local/bin

# Helm — keep the real filename so the upstream .sha256sum (which names it) verifies.
RUN cd /tmp && \
  curl -fsSL -O "https://get.helm.sh/helm-v${HELM_VERSION}-linux-amd64.tar.gz" && \
  curl -fsSL "https://get.helm.sh/helm-v${HELM_VERSION}-linux-amd64.tar.gz.sha256sum" | sha256sum -c - && \
  tar xz -f "helm-v${HELM_VERSION}-linux-amd64.tar.gz" && \
  mv /tmp/linux-amd64/helm /out/usr/local/bin/ && \
  /out/usr/local/bin/helm version

# crane — the publish step uses it to roll back (delete) a chart from Harbor if
# its cosign signature fails, so an unsigned chart never lingers in the registry.
RUN curl -fLsS "https://github.com/google/go-containerregistry/releases/download/${CRANE_VERSION}/go-containerregistry_Linux_x86_64.tar.gz" -o /tmp/crane.tgz && \
  curl -fLsS "https://github.com/google/go-containerregistry/releases/download/${CRANE_VERSION}/checksums.txt" \
    | grep 'go-containerregistry_Linux_x86_64.tar.gz$' | awk '{print $1"  /tmp/crane.tgz"}' | sha256sum -c - && \
  tar xz -f /tmp/crane.tgz -C /out/usr/local/bin/ crane && \
  /out/usr/local/bin/crane version

# --- final image: ci-base + the helm-charts-specific layer ---
# renovate: datasource=docker depName=registry.example.com/homelab/ci-components/ci
FROM registry.example.com/homelab/ci-components/ci:latest@sha256:73df8ef6835dbb69293cf60c53f0373abf407fc1830bfe4dfb60b1a3fc456ebb

LABEL maintainer="maintainer@example.io"
LABEL org.opencontainers.image.title="helm-charts-ci"
LABEL org.opencontainers.image.description="CI image: ci-base + Helm, Crane for the chart pipeline"
LABEL org.opencontainers.image.source="https://source.example.com/example-org/helm-charts"
LABEL org.opencontainers.image.licenses="MIT"

# apk extra not in ci-base: make.
RUN apk add --no-cache make

# helm + crane from the staged build layer (trivy, yq, requests are in ci-base).
COPY --from=fetcher /out/usr/local/bin/helm /usr/local/bin/
COPY --from=fetcher /out/usr/local/bin/crane /usr/local/bin/

# Smoke-test the chart-specific tools (ci-base smoke-tests the rest).
RUN echo "=== helm-charts CI layer ===" && \
  echo "helm: $(helm version --short)" && \
  echo "crane: $(crane version 2>&1)" && \
  echo "============================"

WORKDIR /workspace
CMD ["/bin/bash"]
