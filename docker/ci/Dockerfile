# syntax=docker/dockerfile:1@sha256:b6afd42430b15f2d2a4c5a02b919e98a525b785b1aaff16747d2f623364e39b6

# Base image version (can be overridden at build time)
ARG DOCKER_VERSION=29.2.1-cli@sha256:cab69e2d0a1a2ea9a1ce1060252f439e83483ae41ec09317aecb33b08a0656a5

FROM docker:${DOCKER_VERSION}

# Metadata
LABEL maintainer="maintainer@example.io"
LABEL org.opencontainers.image.title="helm-charts-ci"
LABEL org.opencontainers.image.description="CI tools for Helm charts repository pipeline"
LABEL org.opencontainers.image.source="https://gitlab.example.com/homelab/helm-charts"
LABEL org.opencontainers.image.licenses="MIT"

# Binary tools
ARG HELM_VERSION
ARG SHELLCHECK_VERSION
ARG GITLEAKS_VERSION

# Python packages
ARG PYYAML_VERSION
ARG TQDM_VERSION
ARG YAMLLINT_VERSION
ARG PYTEST_VERSION
ARG PYTEST_COV_VERSION
ARG REQUESTS_VERSION

# npm packages
ARG MARKDOWNLINT_VERSION

# Install base tools
RUN apk add --no-cache \
  bash \
  git \
  coreutils \
  yq \
  openssh-client \
  curl \
  make \
  python3 \
  py3-pip \
  nodejs \
  npm \
  ca-certificates

# Install Helm
RUN curl -fsSL "https://get.helm.sh/helm-v${HELM_VERSION}-linux-amd64.tar.gz" | tar xz && \
  mv linux-amd64/helm /usr/local/bin/ && \
  rm -rf linux-amd64 && \
  helm version

# Install ShellCheck
RUN SHELLCHECK_ARCH="x86_64" && \
  curl -fLs "https://github.com/koalaman/shellcheck/releases/download/${SHELLCHECK_VERSION}/shellcheck-${SHELLCHECK_VERSION}.linux.${SHELLCHECK_ARCH}.tar.xz" | tar xJ && \
  mv "shellcheck-${SHELLCHECK_VERSION}/shellcheck" /usr/local/bin/ && \
  rm -rf "shellcheck-${SHELLCHECK_VERSION}" && \
  shellcheck --version

# Install Gitleaks
RUN curl -fLs "https://github.com/gitleaks/gitleaks/releases/download/${GITLEAKS_VERSION}/gitleaks_${GITLEAKS_VERSION#v}_linux_x64.tar.gz" | tar xz && \
  mv gitleaks /usr/local/bin/ && \
  gitleaks version

# Install Python packages for CI scripts
RUN pip3 install --no-cache-dir --break-system-packages \
  "pyyaml==${PYYAML_VERSION}" \
  "tqdm==${TQDM_VERSION}" \
  "yamllint==${YAMLLINT_VERSION}" \
  "pytest==${PYTEST_VERSION}" \
  "pytest-cov==${PYTEST_COV_VERSION}" \
  "requests==${REQUESTS_VERSION}"

# Install npm packages for linting
RUN npm install -g "markdownlint-cli2@${MARKDOWNLINT_VERSION}" && \
  npm cache clean --force && \
  markdownlint-cli2 --version

# Verify all tools are installed
RUN echo "=== Installed Tools ===" && \
  echo "helm: $(helm version --short)" && \
  echo "shellcheck: $(shellcheck --version | grep version)" && \
  echo "gitleaks: $(gitleaks version)" && \
  echo "yamllint: $(yamllint --version)" && \
  echo "markdownlint-cli2: $(markdownlint-cli2 --version 2>&1 | head -n1)" && \
  echo "pytest: $(pytest --version)" && \
  echo "python3: $(python3 --version)" && \
  echo "docker: $(docker --version)" && \
  echo "git: $(git --version)" && \
  echo "yq: $(yq --version)" && \
  echo "======================="

WORKDIR /workspace

CMD ["/bin/bash"]
