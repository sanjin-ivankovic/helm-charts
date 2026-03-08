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
    url: https://gitlab.example.com/homelab/helm-charts
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
- `sources`: List of source URLs (must use `gitlab.example.com`)
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

Organize values.yaml into logical sections following this order:

1. **Image parameters** - Docker image configuration
2. **Deployment parameters** - Replica count, update strategy, resources
3. **Service parameters** - Service type, ports
4. **Ingress parameters** - Ingress configuration (if applicable)
5. **Storage parameters** - Persistent volume claims (if applicable)
6. **Configuration parameters** - Application-specific configuration
7. **Security parameters** - Security contexts, secrets
8. **Autoscaling parameters** - HPA configuration (if applicable)
9. **PodDisruptionBudget parameters** - PDB configuration (if applicable)
10. **Monitoring parameters** - ServiceMonitor, metrics (if applicable)

### Example

See `cloudflared/values.yaml` as the reference implementation.

```text
## Default values for Cloudflared

## @section Image parameters

## @param image.repository The Docker repository to pull the image from.
## @param image.tag The image tag to use.
## @param image.imagePullPolicy The logic of image pulling.
##
image:
  repository: cloudflare/cloudflared
  tag: '2025.11.1'
  imagePullPolicy: IfNotPresent

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
## @param image.imagePullPolicy The logic of image pulling.
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
## @param persistence.storageClass Storage class for the PVC (empty string = use cluster default).
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

## Best Practices

1. **Consistency**: Follow the cloudflared chart as the reference implementation
2. **Documentation**: Every parameter should have a `@param` annotation
3. **Organization**: Group related parameters into logical sections
4. **Defaults**: Provide sensible defaults for all parameters
5. **Comments**: Use inline comments (`#`) for example values or complex
   configurations
6. **Validation**: Use template validation helpers for mutually exclusive
   options
7. **Secrets**: Always support `existingSecret` pattern for external secret
   management

## Validation

Before submitting a chart:

1. Run `helm lint charts/<chart-name> --strict`
2. Verify all parameters have `@param` annotations
3. Verify all sections have `@section` markers
4. Verify Chart.yaml URLs point to the repository
5. Test template rendering: `helm template test charts/<chart-name>`

## Reference Implementation

The `cloudflared` chart serves as the reference implementation for format
standards. When in doubt, refer to `charts/cloudflared/values.yaml` and
`charts/cloudflared/Chart.yaml` as examples.
