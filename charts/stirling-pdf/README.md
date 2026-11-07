# Stirling PDF

A Helm chart for Stirling PDF, a comprehensive set of PDF tools and
document management features running on Kubernetes.

## TL;DR

```bash
helm install stirling-pdf \
  oci://registry.example.com/example-org/helm-charts/stirling-pdf \
  --version 1.1.0
```

## Introduction

Stirling PDF is a robust, feature-rich application for PDF manipulation,
including tools for splitting, merging, converting, and other document
operations. This chart packages the official container image for Kubernetes
deployment with persistent storage, security contexts, and configurable
authentication.

- **Upstream:** <https://github.com/Stirling-Tools/Stirling-PDF>
- **Chart source:** [`charts/stirling-pdf` on GitLab][chart-source]

[chart-source]: https://source.example.com/example-org/helm-charts/-/tree/main/charts/stirling-pdf

## Prerequisites

- Kubernetes 1.19+
- Helm 3.8+
- A storage class supporting `ReadWriteOnce` volumes (the chart defaults to
  `longhorn`)
- Optional: An OpenID Connect provider and a Secret holding its client secret
  if enabling single sign-on

## Parameters

### Image

<!-- markdownlint-disable MD013 MD060 -->
| Parameter           | Description                      | Default                                                                   |
| ------------------- | -------------------------------- | ------------------------------------------------------------------------- |
| `image.repository`  | Container image repository      | `stirlingtools/stirling-pdf`                                             |
| `image.tag`         | Image tag with digest pinning   | `3.2.0@sha256:10164ffe04961b02ebc9fa4da12064eeacb8d3bc3e09ceb059f78ce7aaa83207` |
| `image.pullPolicy`  | Image pull policy               | `IfNotPresent`                                                            |
<!-- markdownlint-enable MD013 MD060 -->

### Deployment

<!-- markdownlint-disable MD013 MD060 -->
| Parameter         | Description                        | Default |
| ----------------- | ---------------------------------- | ------- |
| `replicaCount`    | Number of pod replicas             | `1`     |
| `updateStrategy`  | Deployment update strategy         | `null`  |
| `priorityClassName` | Priority class for the pod       | `""`    |
<!-- markdownlint-enable MD013 MD060 -->

When `updateStrategy` is `null` and persistence is enabled, it defaults to
`RollingUpdate` with `maxSurge: 0`. This ensures the old pod terminates
before the new one starts, required for `ReadWriteOnce` PVCs.

### Pod spec

<!-- markdownlint-disable MD013 MD060 -->
| Parameter                   | Description                           | Default                       |
| --------------------------- | ------------------------------------- | ----------------------------- |
| `resources.requests.memory` | Memory request per pod                | `256Mi`                       |
| `resources.requests.cpu`    | CPU request per pod                   | `100m`                        |
| `resources.limits.memory`   | Memory limit per pod                  | `1Gi`                         |
| `resources.limits.cpu`      | CPU limit per pod                     | `1000m`                       |
| `nodeSelector`              | Node selector for pod placement       | `{}`                          |
| `affinity`                  | Pod affinity configuration            | `{}`                          |
| `tolerations`               | Pod tolerations                       | `[]`                          |
| `topologySpreadConstraints` | Topology spread constraints           | `[]`                          |
<!-- markdownlint-enable MD013 MD060 -->

### Security

<!-- markdownlint-disable MD013 MD060 -->
| Parameter                      | Description                      | Default            |
| ------------------------------ | -------------------------------- | ------------------ |
| `podSecurityContext.runAsNonRoot` | Reject a root uid (must stay `false`) | `false`  |
| `podSecurityContext.runAsUser` | User ID for pod execution        | `0`                |
| `podSecurityContext.runAsGroup`| Group ID for pod execution       | `0`                |
| `podSecurityContext.fsGroup`   | Filesystem group for volumes     | `0`                |
| `containerSecurityContext.readOnlyRootFilesystem` | Read-only root FS | `false` |
| `containerSecurityContext.privileged` | Privileged mode         | `false`            |
| `containerSecurityContext.allowPrivilegeEscalation` | Allow privilege escalation | `false` |
<!-- markdownlint-enable MD013 MD060 -->

### Service

<!-- markdownlint-disable MD013 MD060 -->
| Parameter           | Description           | Default   |
| ------------------- | --------------------- | --------- |
| `service.type`      | Kubernetes service type | `ClusterIP` |
| `service.port`      | Service port          | `80`      |
| `service.targetPort`| Container port        | `8080`    |
<!-- markdownlint-enable MD013 MD060 -->

### Storage

<!-- markdownlint-disable MD013 MD060 -->
| Parameter              | Description                    | Default     |
| ---------------------- | ------------------------------ | ----------- |
| `persistence.enabled`  | Enable persistent volume claim | `true`      |
| `persistence.storageClass` | Storage class name           | `longhorn`  |
| `persistence.size`     | PVC size                       | `2Gi`       |
| `persistence.accessModes` | PVC access modes            | `["ReadWriteOnce"]` |
<!-- markdownlint-enable MD013 MD060 -->

### Environment variables

<!-- markdownlint-disable MD013 MD060 -->
| Parameter                  | Description                      | Default   |
| -------------------------- | -------------------------------- | --------- |
| `env.DOCKER_ENABLE_SECURITY` | Enable security features       | `true`    |
| `env.SECURITY_ENABLELOGIN` | Enable login functionality       | `true`    |
| `env.SYSTEM_DEFAULTLOCALE` | Default application locale      | `en-US`   |
<!-- markdownlint-enable MD013 MD060 -->

### Health probes

<!-- markdownlint-disable MD013 MD060 -->
| Parameter                | Description                       | Default                     |
| ------------------------ | --------------------------------- | --------------------------- |
| `livenessProbe.tcpSocket.port` | TCP port for liveness check   | `8080`                      |
| `livenessProbe.initialDelaySeconds` | Initial delay             | `60`                        |
| `livenessProbe.periodSeconds` | Check interval                | `10`                        |
| `readinessProbe.tcpSocket.port` | TCP port for readiness check | `8080`                      |
| `readinessProbe.initialDelaySeconds` | Initial delay            | `60`                        |
| `readinessProbe.periodSeconds` | Check interval               | `10`                        |
<!-- markdownlint-enable MD013 MD060 -->

Both liveness and readiness probes use TCP checks against port 8080 instead of
HTTP to avoid authentication issues when `SECURITY_ENABLELOGIN` is enabled.

### OIDC single sign-on

<!-- markdownlint-disable MD013 MD060 -->
| Parameter                       | Description                                                        | Default                        |
| ------------------------------- | ------------------------------------------------------------------ | ------------------------------ |
| `oidc.enabled`                  | Render the `SECURITY_OAUTH2_*` variables                           | `false`                        |
| `oidc.provider`                 | Provider name; last segment of the callback URL                    | `oidc`                         |
| `oidc.issuer`                   | Issuer URL serving `/.well-known/openid-configuration` (required)  | `""`                           |
| `oidc.clientId`                 | OAuth2 client ID (required)                                        | `""`                           |
| `oidc.scopes`                   | Scopes to request, comma-separated                                 | `openid, profile, email`       |
| `oidc.useAsUsername`            | Claim used as the username                                         | `email`                        |
| `oidc.autoCreateUser`           | Create the account on first SSO login                              | `true`                         |
| `oidc.blockRegistration`        | Deny SSO users an admin has not created first                      | `false`                        |
| `oidc.redirectBaseUrl`          | Public callback base URL, only when the proxy hides scheme or host | `""`                           |
| `oidc.existingSecret`           | Secret holding the client secret (required)                        | `""`                           |
| `oidc.secretKeys.clientSecret`  | Key in `existingSecret` holding the client secret                  | `SECURITY_OAUTH2_CLIENTSECRET` |
<!-- markdownlint-enable MD013 MD060 -->

For a complete list of configuration options, see `values.yaml`.

## Configuration notes

### Persistence

By default, persistence is **enabled** with a 2Gi `longhorn` storage class
using `ReadWriteOnce` access. The chart automatically configures the
deployment's `updateStrategy` to avoid conflicts during rolling updates with
single-access volumes.

### Health checks

The chart uses TCP probes instead of HTTP to ensure health checks work
correctly when login is enabled. This avoids authentication timeouts during
probe execution.

### Security

The container starts as root so the image entrypoint can create the
`/usr/local/bin` diagnostics symlinks and chown `/configs` and
`/tmp/stirling-pdf`. It then drops to `stirlingpdfuser` via `setpriv`, so the
JVM itself runs unprivileged. `runAsNonRoot` must stay `false`: a non-root
start fails at the first `ln -sf` under `set -euo pipefail`, and setting it
`true` alongside a root uid makes the kubelet reject the pod with
`CreateContainerConfigError`. Read-write filesystem access is required for
temporary and persistent data. No privilege escalation is allowed.

All capabilities are dropped except four the entrypoint needs before it can
reach the JVM: `SETUID` and `SETGID` for the `setpriv` drop to
`stirlingpdfuser`, and `CHOWN` plus `DAC_OVERRIDE` to fix ownership of
`/configs`, `/logs`, `/customFiles`, `/pipeline` and `/storage` on freshly
provisioned volumes. Removing any one of the four stops the container from
starting.

### OIDC

OAuth2/OIDC single sign-on works on every Stirling-PDF plan since 3.0. Register
the callback URL `https://<host>/login/oauth2/code/<oidc.provider>` with the
identity provider exactly; a mismatch in the provider segment fails every
login with a redirect URI error.

`oidc.useAsUsername` must name a supported claim such as `email` or
`preferred_username`. `sub`, `upn` and `oid` are rejected and stop the server
from starting.

Set the public URL through `env`, which Stirling-PDF uses when building
callbacks:

```yaml
env:
  SYSTEM_BACKENDURL: "https://pdf.example.com"
  SYSTEM_FRONTENDURL: "https://pdf.example.com"
```

The first SSO login creates a user with the standard role. Promote it to Admin
with the local admin account before setting `SECURITY_LOGINMETHOD: "oauth2"`
or `SECURITY_SSOAUTOLOGIN: "true"` in `env`, otherwise nobody can reach the
admin settings.

### Image digest

The image is pinned to a specific digest (`@sha256:...`) for reproducible
deployments and supply-chain security.

## License

This chart is licensed under the MIT License. See the
<!-- markdownlint-disable-next-line MD013 -->
[repository license](https://source.example.com/example-org/helm-charts/-/blob/main/LICENSE)
for details.
