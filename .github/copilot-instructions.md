# Copilot Instructions for Helm Charts Repository

## Repository Overview

Production Helm charts distributed via OCI registry at
`oci://registry.example.com/homelab/helm-charts`. All charts follow Helm v2 API
standards and reside in `charts/` directory. Charts are tested without a
Kubernetes cluster using `helm template` + PyYAML validation.

## Repository Structure

```text
helm-charts/
├── charts/                    # Chart directory (industry standard)
├── scripts/ci/                # CI/CD automation scripts
│   ├── lib/                  # Shared library functions
│   ├── detect-changes.sh     # Git-based change detection
│   ├── validate-chart.sh     # Chart validation
│   ├── package-chart.sh      # Chart packaging
│   ├── publish-chart.sh      # Registry publishing
│   └── release.sh            # Main orchestrator
├── Makefile                  # Local development commands
├── .shellcheckrc             # ShellCheck configuration
└── .gitlab-ci.yml            # GitLab CI/CD pipeline
```

## Chart Structure Pattern

Every chart must follow this structure:

- `Chart.yaml` - metadata with `name`, `version`, `appVersion`,
  `maintainers`, `sources`
- `values.yaml` - defaults with `@section` and `@param` annotations for
  documentation
- `templates/_helpers.tpl` - reusable template definitions (labels, names,
  validation)
- `templates/NOTES.txt` - post-install instructions
- `templates/deployment.yaml` OR `templates/statefulset.yaml` (not both)

## Critical Template Patterns

### Standard Helper Functions (in \_helpers.tpl)

```helm
{{- define "chart-name.name" -}}           # Chart name
{{- define "chart-name.fullname" -}}       # Release + chart name
{{- define "chart-name.chart" -}}          # Chart name + version
{{- define "chart-name.labels" -}}         # Common Kubernetes labels
{{- define "chart-name.selectorLabels" -}} # Pod selector labels
```

### Validation Helpers

Use `{{- fail "error message" -}}` to validate mutually exclusive options.
Example from `home-assistant`:

```helm
{{- define "home-assistant.validateController" -}}
{{- if not (or (eq .Values.controller.type "StatefulSet") \
  (eq .Values.controller.type "Deployment")) -}}
{{- fail "controller.type must be either 'StatefulSet' or 'Deployment'" -}}
{{- end -}}
{{- end -}}
```

### Secret Handling Pattern

Always support `existingSecret` to allow users to manage secrets externally:

```yaml
# In values.yaml
managed:
  token: ''
  existingSecret: '' # If set, uses existing secret instead of creating one
```

### Conditional Resource Inclusion

Wrap optional resources with feature flags:

```helm
{{- if .Values.autoscaling.enabled -}}
# HPA resource here
{{- end }}
```

## Smart Versioning System

**Manual Release** (bump version in Chart.yaml):

- Update `version` field in `Chart.yaml` for chart changes
- Update `appVersion` field for application updates
- CI publishes as exact version (e.g., `1.1.0`)

**CI Build** (no version change):

- CI auto-generates version: `<version>-ci.<timestamp>`
- Original version preserved in Chart.yaml
- Use for template/value tweaks without formal release

## Essential Commands

### Local Development (Makefile)

```bash
# Show all available commands
make help

# Validate single chart
make validate CHART=<chart-name>

# Lint single chart
make lint CHART=<chart-name>

# Test template rendering
make test CHART=<chart-name>

# Package a chart
make package CHART=<chart-name>

# Full release workflow
make release CHART=<chart-name>

# Validate all charts
make validate-all
```

### Direct Helm Commands

```bash
# Validate single chart
helm lint charts/<chart-name> --strict
helm template test-release charts/<chart-name> | \
  python3 -c "import yaml, sys; list(yaml.safe_load_all(sys.stdin))"

# Package and publish (CI does this automatically)
helm package charts/<chart-name>
helm push <chart>-<version>.tgz \
  oci://registry.example.com/homelab/helm-charts
```

### CI/CD Scripts

```bash
# Detect changed charts
./scripts/ci/detect-changes.sh

# Validate a chart
./scripts/ci/validate-chart.sh <chart-name>

# Package a chart
./scripts/ci/package-chart.sh <chart-name>

# Publish a chart
./scripts/ci/publish-chart.sh <chart-name>

# Full release workflow
./scripts/ci/release.sh all
./scripts/ci/release.sh <chart-name>
```

## CI/CD Pipeline (.gitlab-ci.yml)

1. **detect** - Uses `scripts/ci/detect-changes.sh` (git diff based)
2. **validate** - Runs `make lint-all` and `scripts/ci/validate-chart.sh`
3. **package** - Uses `scripts/ci/package-chart.sh` with dependency caching
4. **publish** - Uses `scripts/ci/publish-chart.sh` (main branch with manual
   approval, tags auto-publish)
5. **notify** - Reports publish results

**Key CI Features:**

- No Kubernetes cluster required for testing
- Supports multi-document YAML (Helm's multiple resource output)
- Automatic change detection via git diff
- Idempotent publishing (won't overwrite existing versions)
- ShellCheck validation for all scripts
- Dependency caching for faster builds

## Configuration Standards

### Chart.yaml Requirements

```yaml
apiVersion: v2
name: chart-name
version: 1.0.0 # Chart version (SemVer)
appVersion: '2.0.0' # Application version (quoted)
kubeVersion: '>=1.19.0'
maintainers:
  - name: maintainer
    email: maintainer@example.com
sources:
  - https://gitlab.example.com/homelab/helm-charts/src/branch/main/charts/<name>
```

### values.yaml Documentation Format

```yaml
## @section Section Name
## @param path.to.value Description of the value
## @param path.to.another Optional vs required context
```

### Resource Defaults

- Always define `resources.limits` and `resources.requests`
- Include `nodeSelector` with sensible defaults (e.g.,
  `node-role.kubernetes.io/worker: worker`)
- Support `affinity`, `tolerations`, `topologySpreadConstraints`
- Define `securityContext` with commented examples

## Common Patterns by Chart Type

### Stateless Apps (Deployment)

- See `charts/cloudflared/` or `charts/it-tools/`
- Support HPA (`.Values.autoscaling.enabled`)
- Support PDB (`.Values.podDisruptionBudget.enabled`)
- Use RollingUpdate strategy

### Stateful Apps (StatefulSet)

- See `charts/home-assistant/`
- PVC defined in StatefulSet spec or separate `pvc.yaml`
- May need `serviceName` field for headless service
- Support both controller types via `.Values.controller.type`

### Multi-Container Patterns

- See `charts/affine/` for migration jobs and multi-container patterns
- Each container gets its own deployment, service, configmap

## Testing Workflow

1. Make template changes
2. Run `make validate CHART=<chart-name>` locally
3. Or use direct commands:

   ```bash
   helm lint charts/<chart-name> --strict
   helm template test charts/<chart-name> | \
     python3 -c "import yaml, sys; list(yaml.safe_load_all(sys.stdin))"
   ```

4. Commit without version bump for CI build, or bump version for release
5. PR triggers validation; merge to main triggers publish (with manual
   approval)

## Script Development

### ShellCheck Compliance

All scripts must pass ShellCheck validation:

```bash
# Lint scripts locally
shellcheck scripts/ci/*.sh scripts/ci/lib/*.sh
```

The repository includes `.shellcheckrc` with:

- `external-sources=true` - Allows following source files
- `source-path=SCRIPTDIR` - Resolves paths relative to script directory

### Script Patterns

- Use `set -euo pipefail` for strict error handling
- Source shared libraries from `scripts/ci/lib/`
- Use `printf '%q'` for safe variable escaping in SSH commands
- Follow modular design with single-responsibility scripts

## Registry Authentication

```bash
# Login once
helm registry login registry.example.com

# Install chart
helm install my-release \
  oci://registry.example.com/homelab/helm-charts/<chart-name> \
  --version 1.0.0
```

CI uses GitLab CI built-in `CI_REGISTRY_USER` and `CI_REGISTRY_PASSWORD`
variables.

## Common Gotchas

- Always use `{{- if .Values.x.enabled }}` for optional resources (HPA, PDB,
  ServiceMonitor)
- ConfigMap/Secret changes: Add checksum annotation to trigger pod restart:

  ```helm
  checksum/config: {{ include (print $.Template.BasePath \
    "/configmap.yaml") . | sha256sum }}
  ```

- Selector labels are immutable - document if changing (may require
  deployment recreation)
- Use `.Chart.AppVersion` in labels, not image tags
- Test with `--debug` flag to see rendered values:
  `helm template test charts/x --debug`
- Scripts must use relative paths in `shellcheck source=` directives:
  `# shellcheck source=lib/common.sh` (not
  `scripts/ci/lib/common.sh`)
