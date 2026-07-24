# Helm Charts Collection

<!-- markdownlint-disable MD013 -->

[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![CI](https://img.shields.io/badge/CI-GitLab%20CI-fc6d26?logo=gitlab&logoColor=white)](https://source.example.com/example-org/helm-charts/-/pipelines)
[![Helm](https://img.shields.io/badge/Helm-3.8%2B-0f1689?logo=helm)](https://helm.sh)
[![Kubernetes](https://img.shields.io/badge/Kubernetes-1.19%2B-326ce5?logo=kubernetes&logoColor=white)](https://kubernetes.io)
[![Charts](https://img.shields.io/badge/Charts-18-green)](charts/)
[![OCI Registry](https://img.shields.io/badge/OCI-Registry-blueviolet)](https://helm.sh/docs/topics/registries/)

<!-- markdownlint-enable MD013 -->

Production-ready Helm charts for Kubernetes, distributed via OCI registry.
Features modular CI/CD automation, cluster-free testing, and comprehensive
validation—all following industry best practices.

## Highlights

- **18 Production Charts** — Productivity, networking, monitoring, database,
  and privacy tools
- **OCI Registry Distribution** — Modern containerized Helm chart delivery
- **Cluster-Free Testing** — Validates charts without requiring a Kubernetes
  cluster
- **Idempotent CI/CD** — GitLab CI pipeline with smart versioning
  and safe publishing
- **Tested Python CI Scripts** — pytest-covered publish/validate tooling
  (`.ci/scripts/`)

## Architecture

<!-- markdownlint-disable MD040 -->

```mermaid
---
title: Developer Workflow & Pipeline Stages
---

flowchart TB
    subgraph workflow["Developer Workflow"]
        direction LR
        charts["charts/<br/>Chart.yaml<br/>values.yaml<br/>templates/"]
        gitlab["GitLab CI<br/>(.gitlab-ci.yml)"]
        validate["Validate<br/>Package<br/>Publish<br/>helm template<br/>+ PyYAML"]
        registry["OCI Registry<br/>registry.example.com/<br/>example-org/helm-charts"]

        charts --> gitlab --> validate --> registry
    end

    subgraph pipeline["Pipeline Stages"]
        direction LR
        scan["scan<br/>gitleaks<br/>trivy"]
        lint["lint<br/>yaml/shell<br/>markdown"]
        val["validate<br/>helm template<br/>+ PyYAML"]
        publish["publish<br/>helm push<br/>idempotent"]
        image["image<br/>CI image<br/>build + sign"]
        mirror["mirror<br/>GitHub<br/>sanitized"]

        scan --> lint --> val --> publish --> image --> mirror
    end

    workflow ~~~ pipeline

```

<!-- markdownlint-enable MD040 -->

## Available Charts

<!-- markdownlint-disable MD013 -->

### Deployed

Charts consumed by an app in the [argo-apps](https://source.example.com/example-org/argo-apps)
cluster.

Current chart and app versions live in each chart's `Chart.yaml` (Renovate
bumps them continuously); the published versions are listed in the OCI
registry.

| Chart                                      | Description                               |
| ------------------------------------------ | ----------------------------------------- |
| [actual](charts/actual/)                   | Budgeting and personal finance app        |
| [cloudflare-ddns](charts/cloudflare-ddns/) | Dynamic DNS updater for Cloudflare        |
| [cloudflared](charts/cloudflared/)         | Cloudflare Tunnel for secure connectivity |
| [docuseal](charts/docuseal/)               | Document signing platform                 |
| [joplin](charts/joplin/)                   | Note-taking and synchronisation server    |
| [litellm](charts/litellm/)                 | LLM proxy / gateway                       |
| [memos](charts/memos/)                     | Lightweight note-taking service           |
| [open-webui](charts/open-webui/)           | Multi-model AI chat front-end             |
| [privatebin](charts/privatebin/)           | Minimal, encrypted online pastebin        |
| [searxng](charts/searxng/)                 | Privacy-respecting metasearch engine      |

### Reserve (not yet deployed)

Maintained and published, but no argo-apps app consumes them yet. Kept ready so
deploying one is just adding an app `config.yaml` that references the chart.

| Chart                                | Description                          |
| ------------------------------------ | ------------------------------------ |
| [freshrss](charts/freshrss/)         | Self-hosted RSS feed aggregator      |
| [it-tools](charts/it-tools/)         | Collection of IT tools and utilities |
| [oauth2-proxy](charts/oauth2-proxy/) | Traefik ForwardAuth / OIDC proxy     |
| [omni-tools](charts/omni-tools/)     | Multi-purpose tools collection       |
| [pgadmin](charts/pgadmin/)           | PostgreSQL administration tool       |
| [pocket-id](charts/pocket-id/)       | OIDC identity provider               |
| [pulse](charts/pulse/)               | Uptime monitoring dashboard          |
| [stirling-pdf](charts/stirling-pdf/) | PDF tools and document management    |

<!-- markdownlint-enable MD013 -->

## Featured Charts

### cloudflared

Production-ready networking chart showcasing:

- **HorizontalPodAutoscaler** — Automatic scaling based on CPU/memory
- **PodDisruptionBudget** — Availability guarantees during cluster operations
- **ServiceMonitor** — Prometheus metrics collection
- **Secret management** — Support for both managed and existing secrets

### searxng

Most actively maintained chart demonstrating:

- **Complex configuration** — Multi-section settings with secret injection
- **Redis integration** — Optional cache backend with connection management
- **Environment layering** — Base config + secret overrides pattern
- **Rapid iteration** — Frequent upstream tracking with stable chart API

### stirling-pdf

Feature-rich document processing chart showcasing:

- **Resource-intensive workloads** — Configurable limits for CPU-heavy PDF
  operations
- **Security contexts** — Non-root execution with proper filesystem permissions
- **Persistent storage** — PVC management for temporary and permanent data
- **Health checks** — Liveness and readiness probes for long-running operations

## Quick Start

```bash
# Login to registry
helm registry login registry.example.com

# Install a chart (pin --version to the chart's Chart.yaml version)
helm install my-release \
  oci://registry.example.com/example-org/helm-charts/cloudflared \
  --version <chart-version>

# Install with custom values
helm install my-release \
  oci://registry.example.com/example-org/helm-charts/searxng \
  --version <chart-version> \
  -f my-values.yaml

# View chart configuration options
helm show values \
  oci://registry.example.com/example-org/helm-charts/cloudflared \
  --version <chart-version>
```

## Development

### Repository Structure

```text
helm-charts/
├── charts/                    # Helm charts (17 production-ready)
│   └── <chart-name>/
│       ├── Chart.yaml        # Metadata, version, maintainers
│       ├── values.yaml       # Configuration with @section/@param docs
│       └── templates/        # Kubernetes manifests
├── .ci/
│   ├── scripts/              # Python CI scripts (pytest-covered)
│   │   ├── detect_changes.py   # Git-based change detection
│   │   ├── validate_chart.py   # helm lint + template validation
│   │   ├── package_chart.py    # Dependency resolution and packaging
│   │   ├── publish_chart.py    # Idempotent registry publishing
│   │   └── notify.py           # Discord publish notifications
│   ├── docker/               # Thin CI image (FROM ci-base)
│   └── sanitize/             # GitHub-mirror sanitization config
├── .config/                  # Lint/scan rule files read by CI components
├── docs/                     # Internal standards documentation
└── Makefile                  # Developer commands
```

### Local Development

```bash
# Show all available commands
make help

# Validate a chart (lint + template rendering)
make validate CHART=cloudflared

# Package a chart
make package CHART=cloudflared

# Full release workflow
make release CHART=cloudflared

# Validate all charts
make validate-all

# List available charts
make list-charts
```

### CI/CD Pipeline

This repository uses GitLab CI ([`.gitlab-ci.yml`](.gitlab-ci.yml)), run on a
self-hosted runner. Shared jobs come from `homelab/ci-components` (version-
pinned CI/CD components); chart-specific jobs are inline. Stages:

| Stage        | Description                                              |
| ------------ | -------------------------------------------------------- |
| **scan**     | gitleaks secret scan (full history) + trivy chart scan   |
| **lint**     | yaml / shell / Markdown lint (per-tool jobs)             |
| **validate** | `helm template` render + PyYAML parse per changed chart  |
| **publish**  | Package + push changed charts to OCI, sign, notify       |
| **image**    | Build + cosign-sign this repo's thin CI image            |
| **mirror**   | Sanitized GitHub portfolio mirror (scheduled)            |

**Key Features:**

- **Smart versioning** — Auto-generates CI versions (`1.0.0-ci.timestamp`) to
  prevent conflicts
- **Idempotent publishing** — Won't overwrite existing chart versions
- **Change detection** — Only processes modified charts
- **Cluster-free testing** — Uses `helm template` + PyYAML, no Kubernetes
  required

### Chart Standards

All charts follow consistent patterns:

- **Helm v2 API** compliance
- **@section/@param** annotations in `values.yaml` for documentation
- **Standard helpers** in `_helpers.tpl` (labels, selectors, names)
- **existingSecret** pattern for external secret management
- **Validation helpers** using `{{- fail }}` for mutual exclusivity checks

See [docs/CHARTS.md](docs/CHARTS.md) for detailed standards.

## Technical Achievements

| Category     | Achievement                                             |
| ------------ | ------------------------------------------------------- |
| **Charts**   | 18 production-ready charts across 5 categories          |
| **Patterns** | Deployment, StatefulSet, HPA, PDB, ServiceMonitor, Jobs |
| **CI/CD**    | GitLab CI pipeline with idempotent publishing           |
| **Testing**  | Cluster-free validation via helm template + PyYAML      |
| **Scripts**  | Python CI scripts with pytest unit tests                |
| **Docs**     | @section/@param annotations, comprehensive README files |

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/new-chart`)
3. Follow [Helm best practices](https://helm.sh/docs/chart_best_practices/)
4. Validate changes: `make validate CHART=<chart-name>`
5. Commit with conventional commits (`feat:`, `fix:`, `docs:`)
6. Open a merge request

### Versioning

Charts follow [Semantic Versioning](https://semver.org/):

- **MAJOR** — Breaking changes requiring user action
- **MINOR** — New features, backward-compatible
- **PATCH** — Bug fixes, backward-compatible

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for
details.

---

**Note:** The pipeline is defined in [`.gitlab-ci.yml`](.gitlab-ci.yml) and
runs on a self-hosted GitLab runner; the build/validate/publish scripts it
invokes live in [.ci/](.ci/).
