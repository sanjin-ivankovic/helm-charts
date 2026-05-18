# Values.yaml Standard

Standard section ordering, naming conventions, and annotation format for all
`values.yaml` files in this repository. Based on
[Helm best practices](https://helm.sh/docs/chart_best_practices/values/) and
[Bitnami conventions](https://github.com/bitnami/charts).

## Naming Conventions

All value keys follow Helm's official naming rules:

- **camelCase** with lowercase first letter for all keys
- Never use hyphens, snake_case, or PascalCase for value keys
- Standard image structure: `image.repository`, `image.tag`,
  `image.pullPolicy`
- Security contexts: `podSecurityContext` and `containerSecurityContext`
  (not `securityContext`)
- Environment variables in `env:` blocks use the **application's native
  names** (typically `UPPERCASE_SNAKE_CASE` like `APP_URL`, `DB_HOST`) —
  these are container passthrough values, not Helm configuration keys
- Arrays default to `[]`, objects default to `{}`
- `topologySpreadConstraints` is always `[]` (array, not object)

## Section Order

Sections are declared with `## @section Section Name` annotations.
Include only the sections relevant to the chart — skip sections that
don't apply.

<!-- markdownlint-disable MD013 MD060 -->
| #  | Section Name                       | Key Parameters                                                         | Required |
| -- | ---------------------------------- | ---------------------------------------------------------------------- | -------- |
| 1  | Image parameters                   | `image.repository`, `image.tag`, `image.pullPolicy`                    | Yes      |
| 2  | Name override parameters           | `nameOverride`, `fullnameOverride`                                     | No       |
| 3  | Service Account parameters         | `serviceAccount.create`, `serviceAccount.name`                         | No       |
| 4  | Deployment parameters              | `replicaCount`, `updateStrategy`, `podAnnotations`, `priorityClassName`| No       |
| 5  | Pod spec parameters                | `resources`, `nodeSelector`, `affinity`, `tolerations`, `topologySpreadConstraints` | Yes |
| 6  | Security parameters                | `podSecurityContext`, `containerSecurityContext`                        | No       |
| 7  | Init Container parameters          | `initContainer.*`                                                      | No       |
| 8  | Service parameters                 | `service.type`, `service.port`, `service.targetPort`                   | Yes      |
| 9  | Ingress parameters                 | `ingress.enabled`, `ingress.hostname`, `ingress.annotations`           | No       |
| 10 | Storage parameters                 | `persistence.enabled`, `persistence.storageClass`, `persistence.size`  | No       |
| 11 | Environment variables              | `env.*` (application-native variable names)                            | No       |
| 12 | Secret parameters                  | `existingSecret`, `secretKeys.*`                                       | No       |
| 13 | Health Probe parameters            | `probes.liveness.*`, `probes.readiness.*`                              | No       |
| 14 | Application-specific parameters    | App config that doesn't fit elsewhere                                  | No       |
| 15 | Monitoring parameters              | `metrics.*`, `serviceMonitor.*`                                        | No       |
| 16 | Autoscaling parameters             | `autoscaling.enabled`, `autoscaling.minReplicas`                       | No       |
| 17 | Pod Disruption Budget parameters   | `podDisruptionBudget.enabled`, `podDisruptionBudget.minAvailable`      | No       |
<!-- markdownlint-enable MD013 MD060 -->

## Annotation Format

Every parameter must have a `@param` annotation. Parameters are grouped
under `@section` markers.

```yaml
## Default values for Chart Name

## @section Image parameters

## @param image.repository The Docker repository to pull the image from.
## @param image.tag The image tag to use.
## @param image.pullPolicy The image pull policy.
##
image:
  repository: example/app
  tag: "1.0.0"
  pullPolicy: IfNotPresent

## @section Pod spec parameters

## @param resources Resource requests and limits for the pod.
## @param nodeSelector Node selector for pod placement.
## @param affinity Affinity rules for pod scheduling.
## @param tolerations Tolerations for pod scheduling.
## @param topologySpreadConstraints Topology spread constraints for
##   pod distribution.
##
resources: {}
nodeSelector: {}
affinity: {}
tolerations: []
topologySpreadConstraints: []
```

### Rules

1. Use `##` (double hash) for all documentation comments
2. Use `#` (single hash) for inline value comments or examples
3. One blank line after `@section` before `@param` blocks
4. One blank line after the last `@param` (the `##` terminator) before
   YAML values
5. One blank line between sections
6. Parameter descriptions start with a capital letter, use present tense
7. Multi-line descriptions indent continuation with `##   ` (two spaces
   after `##`)

## Existing Secret Pattern

All charts that handle credentials must support the `existingSecret`
pattern, allowing users to provide pre-created Kubernetes Secrets
instead of chart-managed values:

```yaml
## @section Secret parameters

## @param existingSecret Name of an existing secret containing
##   credentials (overrides chart-managed secret).
## @param secretKeys.password Key in the existing secret for the
##   password field.
##
existingSecret: ""
secretKeys:
  password: "password"
```

## Reference Implementation

The **cloudflared** chart (`charts/cloudflared/values.yaml`) is the
reference implementation. When in doubt, follow its patterns.
