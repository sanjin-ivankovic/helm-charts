# Helm Charts Format Standards

This document defines the format standards for all Helm charts in this
repository. All charts must follow these conventions for consistency and
maintainability.

## Chart Structure

Each chart must follow the standard Helm chart structure:

```text
chart-name/
├── Chart.yaml           # Chart metadata
├── values.yaml          # Default configuration with @section/@param annotations
└── templates/           # Kubernetes manifest templates
    ├── _helpers.tpl     # Template helpers
    ├── deployment.yaml  # Or statefulset.yaml
    ├── service.yaml     # Service definition
    ├── NOTES.txt        # Post-install instructions
    └── ...              # Other resources as needed
```

## Chart.yaml Format

All `Chart.yaml` files must follow this structure:

```text
apiVersion: v2
name: chart-name
description: Chart description
type: application
version: 1.0.0
appVersion: '1.0.0'
kubeVersion: '>=1.19.0'
keywords:
  - keyword1
  - keyword2
home: https://example.com
sources:
  - https://github.com/<owner>/helm-charts/tree/main/charts/chart-name
maintainers:
  - name: maintainer
    email: maintainer@example.com
    url: https://source.example.com/example-org/helm-charts
```

### Required Fields

- `apiVersion`: Must be `v2` (Helm 3+)
- `name`: Chart name (must match directory name)
- `description`: Brief description of the chart
- `type`: Must be `application`
- `version`: Chart version (SemVer format)
- `appVersion`: Application version (quoted string)

### Optional Fields

- `kubeVersion`: Minimum Kubernetes version requirement
- `keywords`: List of keywords for discovery
- `home`: URL to project homepage
- `sources`: List of source URLs (must use `source.example.com`)
- `maintainers`: List of maintainer information

### Important Notes

- Sources should reference the chart's location in the repository
- Maintainer URL should reference the repository root

## values.yaml Format

All `values.yaml` files must use the `@section` and `@param` annotation format
for documentation. This format enables automatic documentation generation and
provides clear structure.

### Format Pattern

```text
## Default values for Chart Name

## @section Section Name

## @param param.path Description of the parameter.
## @param another.param Description of another parameter.
##
param:
  path: value
  another:
    param: value

## @section Another Section

## @param nested.value.path Description of nested parameter.
##
nested:
  value:
    path: value
```

### Annotation Rules

1. **File Header**: Start with `## Default values for Chart Name`

2. **Section Markers**: Use `## @section Section Name` before each logical
   grouping of parameters

3. **Parameter Documentation**: Use `## @param path.to.value Description` for
   each configurable parameter

4. **Blank Lines**:
   - One blank line after `@section`
   - One blank line after the last `@param` before the actual values
   - One blank line between sections

5. **Comments**: Use `##` (double hash) for all documentation comments

6. **Inline Comments**: Use `#` (single hash) for inline value comments or
   examples

### Section Organization

Organize values.yaml into logical sections following the standard order.
Include only the sections relevant to the chart.

See [VALUES-STANDARD.md](VALUES-STANDARD.md) for the full section ordering
reference with naming conventions and annotation format.

**Core sections** (most charts):

1. **Image parameters** - `image.repository`, `image.tag`, `image.pullPolicy`
2. **Deployment parameters** - `replicaCount`, `updateStrategy`,
   `priorityClassName`
3. **Pod spec parameters** - `resources`, `nodeSelector`, `affinity`,
   `tolerations`, `topologySpreadConstraints`
4. **Service parameters** - `service.type`, `service.port`
5. **Storage parameters** - `persistence.enabled`, `persistence.size`
6. **Environment variables** - `env.*` (application-native names)
7. **Secret parameters** - `existingSecret`, `secretKeys.*`
8. **Health Probe parameters** - `livenessProbe`, `readinessProbe`

**Optional sections** (add when needed):

- **Security parameters** - `podSecurityContext`, `containerSecurityContext`
- **Init Container parameters** - `initContainer.*`
- **Application-specific parameters** - Custom app config
- **Monitoring parameters** - `metrics.*`, `serviceMonitor.*`
- **Autoscaling parameters** - `autoscaling.*`
- **Pod Disruption Budget parameters** - `podDisruptionBudget.*`

### Example

See `cloudflared/values.yaml` as the reference implementation.

```text
## Default values for Cloudflared

## @section Image parameters

## @param image.repository The Docker repository to pull the image from.
## @param image.tag The image tag to use.
## @param image.pullPolicy The image pull policy.
##
image:
  repository: cloudflare/cloudflared
  tag: '2025.11.1'
  pullPolicy: IfNotPresent

## @section Deployment parameters

## @param replicaCount The number of replicas to deploy.
## @param resources If specified, it sets the resource requests and limits
##   for the pod.
##
replicaCount: 1
resources:
  limits:
    cpu: 100m
    memory: 128Mi
  requests:
    cpu: 50m
    memory: 64Mi
```

### Parameter Description Guidelines

- Start with a capital letter
- Use present tense ("Enable" not "Enables")
- Be concise but descriptive
- Mention default behavior if non-obvious
- Include constraints or requirements when applicable
- For boolean parameters, state what happens when enabled
- For optional parameters, mention they're optional

### Common Parameter Patterns

**Image Parameters:**

```text
## @param image.repository The Docker repository to pull the image from.
## @param image.tag The image tag to use.
## @param image.pullPolicy The image pull policy.
```

**Resource Parameters:**

```text
## @param resources If specified, it sets the resource requests and limits
##   for the pod.
```

**Secret Parameters:**

```text
## @param secrets.existingSecret The name of an existing secret
##   (optional, overrides default).
```

**Storage Parameters:**

```text
## @param persistence.enabled Enable persistent volume claim.
## @param persistence.storageClass Storage class for the PVC
##                                 (empty string = cluster default).
## @param persistence.size Size of the persistent volume.
```

**Scheduling Parameters:**

```text
## @param nodeSelector Node selector for pod placement (empty object = no node selector).
```

**Important**: Infrastructure-specific settings like `nodeSelector` and
`storageClass` should **never be hardcoded** in `values.yaml`. They should be
set to empty defaults and overridden per-deployment via values files:

- `nodeSelector: {}` - Empty object by default (no node selector applied)
- `storageClass: ""` - Empty string by default (uses cluster default storage
  class)

Users should override these in their deployment-specific values files:

```text
# values-production.yaml (example override for specific deployment)
nodeSelector:
  node-role.kubernetes.io/worker: worker

persistence:
  storageClass: longhorn # Override default empty string with your storage class
```

## Template Standards

### \_helpers.tpl

All charts must include standard helper functions in `_helpers.tpl`:

```text
{{- define "chart-name.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "chart-name.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{- define "chart-name.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" |
  trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "chart-name.labels" -}}
helm.sh/chart: {{ include "chart-name.chart" . }}
{{ include "chart-name.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{- define "chart-name.selectorLabels" -}}
app.kubernetes.io/name: {{ include "chart-name.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}
```

## Enforced Rules

`.ci/scripts/check_chart_standard.py` renders every chart and fails on any
rule below that the chart breaks, unless `.ci/chart-standard.yaml` lists the
exception. It runs in pre-commit, `make check-standard` and the CI job
`validate:standard`, which `publish:charts` needs.

<!-- markdownlint-disable MD013 MD060 -->
| Rule | Requirement | Why |
| ---- | ----------- | --- |
| `labels` | Every object carries `app.kubernetes.io/name`, `instance`, `managed-by` and `helm.sh/chart` | tooling and selectors rely on them |
| `placement` | `priorityClassName`, `nodeSelector`, `tolerations`, `affinity` from values reach every pod (a second workload may use its own block, e.g. `worker.*`) | argo-apps sets them; an ignored key silently drops the priority class |
| `pod-non-root` | Pod `securityContext.runAsNonRoot: true` | no root in the cluster |
| `pod-seccomp` | Pod `seccompProfile.type: RuntimeDefault` | default syscall filter |
| `no-privilege-escalation` | Every container `allowPrivilegeEscalation: false` | |
| `drop-all-caps` | Every container drops `ALL` capabilities | |
| `read-only-rootfs` | Every container `readOnlyRootFilesystem: true`; writable paths are volumes (`/tmp` an emptyDir) | |
| `resources` | Every container has requests and limits | namespaces with a ResourceQuota reject pods without them |
| `image-digest` | Every image is `tag@sha256:...` | reproducible pulls; Renovate updates both |
| `probes` | Every Deployment container has readiness and liveness probes | rollouts wait for a working pod |
| `chart-metadata` | `Chart.yaml` has apiVersion v2, name, description, type, version, appVersion, kubeVersion, home, sources, maintainers, keywords | |
| `values-documented` | Every top-level `values.yaml` key has an `## @param` line | the README tables are built from them |
| `no-ingress-by-default` | The default render has no `Ingress` | argo-apps owns every route as a Traefik IngressRoute |
<!-- markdownlint-enable MD013 MD060 -->

The checker renders with sentinel placement values, so a rule about
placement is checked against what the templates do, not what the defaults
happen to be.

## Exceptions

`.ci/chart-standard.yaml` lists one entry per chart and rule, with a reason
that starts with `accepted:` (a deliberate deviation), `fix:` (a defect to
remove) or `investigate:` (needs a test against the running app). An entry
whose rule passes fails the check, so the fix and the removal of its entry
land in the same MR.

## New Charts

```bash
make new-chart NAME=<chart>
```

This copies `.ci/scaffold/chart/` to `charts/<chart>/`: the helpers, Service,
PVC and a Deployment that already pass every rule. Set the image (with its
digest), ports, probe paths, the image's uid and the README before the first
release. CI generates the scaffold on every change and checks it with no
exceptions.

## Validation

Before submitting a chart:

1. `make validate CHART=<chart-name>` (lint, render, YAML parse)
2. `make check-standard`
3. Render twice and diff; any difference shows up as permanent ArgoCD drift:

   ```bash
   diff <(helm template t charts/<chart>) <(helm template t charts/<chart>)
   ```
