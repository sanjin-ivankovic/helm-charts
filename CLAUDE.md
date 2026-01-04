# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working
with code in this repository.

## Repository Overview

This is a collection of 11 production-ready Helm charts distributed via an
OCI registry at `oci://registry.example.com/homelab/helm-charts`. Charts are
located in the `charts/` subdirectory following industry standards
(prometheus-community, bitnami, jenkinsci).

**Technology Stack:**

- Helm 3.16.3
- Kubernetes 1.19+
- Python 3 with PyYAML for YAML validation
- GitLab CI/CD for automation
- ShellCheck for script validation
- Makefile for local development

## Repository Structure

```text
helm-charts/
├── charts/                    # Chart directory (industry standard)
│   ├── cloudflared/
│   ├── home-assistant/
│   └── ...
├── scripts/ci/                # CI/CD automation scripts
│   ├── lib/                  # Shared library functions
│   ├── detect-changes.sh     # Git-based change detection
│   ├── validate-chart.sh     # Chart validation
│   ├── package-chart.sh       # Chart packaging
│   ├── publish-chart.sh       # Registry publishing
│   └── release.sh            # Main orchestrator
├── Makefile                  # Local development commands
├── .shellcheckrc             # ShellCheck configuration
└── .gitlab-ci.yml            # CI/CD pipeline
```

## Common Commands

### Local Development with Makefile

```bash
# Show all available commands
make help

# Validate a single chart
make validate CHART=searxng

# Lint a chart
make lint CHART=searxng

# Test template rendering
make test CHART=searxng

# Package a chart
make package CHART=searxng

# Full release workflow (validate + package + push)
make release CHART=searxng

# Validate all charts
make validate-all

# List all available charts
make list-charts

# Bump chart version
make version-bump CHART=searxng TYPE=patch
```

### Testing and Validation

```bash
# Lint all charts (via Makefile)
make lint-all

# Lint specific chart
helm lint charts/<chart-name> --strict

# Test template rendering
helm template test-release charts/<chart-name>

# Debug template rendering
helm template test-release charts/<chart-name> --debug

# Validate rendered YAML is syntactically correct
helm template test-release charts/<chart-name> | \
  python3 -c "import yaml, sys; list(yaml.safe_load_all(sys.stdin))"

# Dry-run installation
helm install test-release charts/<chart-name> --dry-run --debug
```

### CI/CD Scripts

```bash
# Detect changed charts
./scripts/ci/detect-changes.sh

# Validate a chart
./scripts/ci/validate-chart.sh searxng

# Package a chart
./scripts/ci/package-chart.sh searxng

# Publish a chart (requires registry login)
./scripts/ci/publish-chart.sh searxng

# Full release workflow
./scripts/ci/release.sh all              # All charts
./scripts/ci/release.sh searxng          # Single chart
```

### Publishing

```bash
# Login to registry
make login

# Package a chart
make package CHART=<chart-name>

# Push to OCI registry
make push CHART=<chart-name>

# Or use the full workflow
make release CHART=<chart-name>
```

### Development Workflow

```bash
# Create new chart
cd charts/
helm create my-new-chart

# View published chart details
helm show values \
  oci://registry.example.com/homelab/helm-charts/<chart-name> \
  --version <version>
helm show readme \
  oci://registry.example.com/homelab/helm-charts/<chart-name> \
  --version <version>
```

## Architecture

### Chart Structure

Each chart follows Helm v2 API standards with this structure:

```text
chart-name/
├── Chart.yaml           # Metadata, version, description, maintainers
├── values.yaml          # Default configuration (heavily commented)
└── templates/           # Kubernetes manifest templates
    ├── _helpers.tpl     # Template helpers/functions (common labels, selectors)
    ├── deployment.yaml  # Deployment or StatefulSet (depending on chart)
    ├── service.yaml     # Service definition
    ├── configmap.yaml   # ConfigMaps for application configuration
    ├── secret.yaml      # Secrets (supports existing secrets)
    ├── ingress.yaml     # Ingress (where applicable)
    ├── pvc.yaml         # PersistentVolumeClaims (where applicable)
    ├── hpa.yaml         # HorizontalPodAutoscaler (where applicable)
    ├── pdb.yaml         # PodDisruptionBudget (where applicable)
    ├── service-monitor.yaml  # Prometheus ServiceMonitor (where applicable)
    ├── NOTES.txt        # Post-deployment instructions
    └── tests/           # Helm test pods (where applicable)
```

### Key Architectural Patterns

**Templating:**

- Heavy use of conditional includes: `{{- if .Values.feature.enabled }}`
- Template helpers in `_helpers.tpl` for DRY labels, selectors, and names
- Support for both Deployments (stateless) and StatefulSets (stateful)

**Configuration:**

- All values documented with comments in `values.yaml`
- Support for existing secrets via `existingSecret` pattern
- Configurable resource limits, node selectors, affinity rules
- Security contexts with runAsUser, runAsGroup, fsGroup

**High Availability:**

- HorizontalPodAutoscaler (HPA) support for auto-scaling
- PodDisruptionBudget (PDB) for availability guarantees
- Affinity/anti-affinity rules for pod distribution
- Rolling update strategies

**Observability:**

- ServiceMonitor CRDs for Prometheus integration
- Configurable health checks (liveness/readiness probes)
- NOTES.txt provides post-install instructions

**Storage:**

- PersistentVolumeClaims with configurable storage classes
- StatefulSets for applications requiring persistent state

## CI/CD Pipeline

### Pipeline Stages

The GitLab CI pipeline consists of 5 stages:

1. **detect** - Identifies changed charts using git diff
2. **validate** - Lints charts and validates templates
3. **package** - Creates .tgz packages with dependency caching
4. **publish** - Pushes to OCI registry (manual approval for main branch)
5. **notify** - Reports publish results

### Pipeline Behavior

- **Merge Requests**: Validates and packages (no publish)
- **Main Branch**: Requires manual approval to publish
- **Tags**: Automatically publishes all changed charts

### Smart Versioning Strategy

The pipeline uses an intelligent versioning system to prevent OCI registry
conflicts:

**Manual Release** (when you bump `version` or `appVersion` in Chart.yaml):

- Publishes with exact version from Chart.yaml
- Example: `cloudflared:1.1.0`
- Use for intentional releases (features, bug fixes, breaking changes)

**CI Build** (when you change templates/values but NOT Chart.yaml version):

- Auto-generates: `<version>-ci.<timestamp>`
- Example: `cloudflared:1.0.0-ci.20241116123456`
- Preserves original version in Chart.yaml after push
- Use for template tweaks and quick fixes

### Pipeline Features

- **Change Detection**: Only processes modified charts via
  `scripts/ci/detect-changes.sh`
- **Idempotent Publishing**: Won't re-push existing chart versions
- **Dependency Caching**: Speeds up packaging with cached dependencies
- **Script Validation**: ShellCheck validation for all scripts
- **Chart Linting**: Comprehensive linting with `helm lint --strict` via
  Makefile

### Configuration Files

- **`.gitlab-ci.yml`** - CI/CD workflow
  - Triggers: Push to main, merge requests, tags
  - Uses Makefile for linting (`make lint-all`)
  - Uses scripts/ci/ for automation
  - Registry: `oci://registry.example.com/homelab/helm-charts`
  - Auth: GitLab CI built-in registry authentication

- **`.shellcheckrc`** - ShellCheck configuration
  - `external-sources=true` - Allows following source files
  - `source-path=SCRIPTDIR` - Resolves paths relative to script directory

- **`.ct.yaml`** - Chart Testing configuration (legacy, not actively used)
  - Present for reference but CI uses Makefile and scripts instead

## Versioning Guidelines

Follow **Semantic Versioning** (SemVer): `MAJOR.MINOR.PATCH`

| Change Type     | Version Bump   | Example       | When                  |
| --------------- | -------------- | ------------- | --------------------- |
| Breaking change | MAJOR          | 1.0.0 → 2.0.0 | Incompatible upgrades |
| New feature     | MINOR          | 1.0.0 → 1.1.0 | New optional features |
| Bug fix         | PATCH          | 1.0.0 → 1.0.1 | Template/value fixes  |
| CI build        | Auto-generated | 1.0.0-ci.TS   | Auto CI tweaks        |

**Important:** Chart `version` is independent of `appVersion`. Bump chart
version for chart changes, appVersion for application updates.

## Chart Development Guide

### Adding a New Chart

1. Create chart: `cd charts/ && helm create my-new-chart`
2. Update `Chart.yaml` with proper metadata (name, version, appVersion,
   description, sources, maintainers)
3. Customize `values.yaml` and templates
4. Test locally: `make validate CHART=my-new-chart`
5. Commit and push to main branch
6. Pipeline automatically publishes to OCI registry

### Updating an Existing Chart

**For a release (bump version):**

1. Make changes to templates/values
2. Update `version` in Chart.yaml (e.g., 1.0.0 → 1.1.0)
3. Update `appVersion` if application version changed
4. Test locally: `make validate CHART=my-chart`
5. Commit with message: `feat: add feature X to my-chart v1.1.0`
6. Push to main → publishes as `my-chart:1.1.0`

**For a quick fix (CI build):**

1. Make changes to templates/values
2. DO NOT change Chart.yaml versions
3. Commit with message: `fix: adjust default resource limits`
4. Push to main → publishes as `my-chart:1.0.0-ci.20241116123456`

### Pull Request Workflow

PRs trigger validation only:

- Changed charts detected with `scripts/ci/detect-changes.sh`
- Charts linted via `make lint-all` and validated via
  `scripts/ci/validate-chart.sh`
- Scripts validated with ShellCheck
- No publishing to registry
- No version increment required (unless it's a release)

## Code Quality

### Script Validation

All scripts are validated with ShellCheck:

```bash
# Lint scripts locally
shellcheck scripts/ci/*.sh scripts/ci/lib/*.sh

# Or use the CI pipeline which runs automatically
```

The repository includes `.shellcheckrc` configuration for consistent
validation. Scripts use modular design with shared library functions in
`scripts/ci/lib/`.

### Chart Validation

Charts are validated using:

- `helm lint --strict` for syntax and best practices
- `helm template` + PyYAML for template rendering validation
- Makefile targets for consistent local testing

## DevOps Principles

### Kubernetes

- Use Helm charts for application deployments
- Follow GitOps principles for cluster state
- Prefer StatefulSets for applications requiring persistent storage
- Use HorizontalPodAutoscaler (HPA) for scaling

### Scripting

- Use Bash with `set -euo pipefail` for strict error handling
- Follow ShellCheck best practices
- Use modular scripts with shared libraries
- Document all functions and complex logic

### Python

- Write Pythonic code adhering to PEP 8
- Use type hints for functions and classes
- Follow DRY and KISS principles
- Use pytest for testing

### Testing and Documentation

- Write meaningful unit, integration, and acceptance tests
- Document solutions thoroughly in Markdown
- Use diagrams for high-level architecture
- Validate all scripts with ShellCheck

### Git and Collaboration

- Use clear branching strategy
- Apply DevSecOps practices
- Commit messages should follow conventional commits format

## Registry Information

**OCI Registry:** `oci://registry.example.com/homelab/helm-charts`

**Registry Host:** `registry.example.com`

**Registry Owner:** `homelab`

**Registry Project:** `helm-charts`

**Authentication:** GitLab CI uses built-in `CI_REGISTRY_USER` and
`CI_REGISTRY_PASSWORD`

**Installation Example:**

```bash
helm registry login registry.example.com
helm install my-release \
  oci://registry.example.com/homelab/helm-charts/cloudflared \
  --version 1.0.0
```

## Important Notes

- Charts in `charts/` directory only - industry standard structure
- Makefile provides convenient local development commands
- CI/CD scripts in `scripts/ci/` for automated workflows
- ShellCheck validation for all scripts (configured via `.shellcheckrc`)
- Pipeline validates multi-document YAML (supports Helm's multiple resource
  output)
- No Kubernetes cluster required for testing (uses `helm template` + PyYAML)
- Change detection uses git diff, not chart-testing
- All scripts follow modular design with shared libraries
