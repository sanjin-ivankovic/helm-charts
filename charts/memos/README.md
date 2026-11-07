# Memos

A self-hosted, lightweight note-taking service. Memos lets you capture and
share thoughts, plans, and memos in privacy-first Markdown, with your data
under your control.

## TL;DR

```bash
helm install memos \
  oci://registry.example.com/example-org/helm-charts/memos \
  --version 1.0.1
```

## Introduction

Memos is an open-source, self-hosted memo hub. It supports Markdown notes,
tagging, and a REST API, and can store its data in SQLite, MySQL, or
PostgreSQL. See the [Memos homepage](https://usememos.com/) and
[GitHub repository](https://github.com/usememos/memos) for more information.

## Prerequisites

- Kubernetes 1.19 or later
- A storage class supporting `ReadWriteOnce` volumes (default: cluster default)
- An external PostgreSQL/MySQL database if not using the bundled SQLite driver

The chart runs a single pod with the `Recreate` update strategy because Memos
keeps local assets on a single `ReadWriteOnce` volume—only one pod can mount it
at a time.

## Parameters

### Image

<!-- markdownlint-disable MD013 MD060 -->
| Name | Default | Description |
|------|---------|-------------|
| `image.repository` | `neosmemo/memos` | Docker image repository |
| `image.tag` | `0.29.1@sha256:...` | Image tag with digest pin |
| `image.pullPolicy` | `IfNotPresent` | Image pull policy |
<!-- markdownlint-enable MD013 MD060 -->

### Deployment

<!-- markdownlint-disable MD013 MD060 -->
| Name | Default | Description |
|------|---------|-------------|
| `replicaCount` | `1` | Number of replicas (always 1 due to RWO storage) |
| `updateStrategy.type` | `Recreate` | Pod update strategy |
| `priorityClassName` | `""` | Priority class for pod scheduling |
| `enableServiceLinks` | `false` | Inject service-discovery env vars (keep false) |
<!-- markdownlint-enable MD013 MD060 -->

### Service

<!-- markdownlint-disable MD013 MD060 -->
| Name | Default | Description |
|------|---------|-------------|
| `service.type` | `ClusterIP` | Kubernetes service type |
| `service.port` | `80` | Service port |
| `service.targetPort` | `5230` | Container port |
<!-- markdownlint-enable MD013 MD060 -->

### Storage

<!-- markdownlint-disable MD013 MD060 -->
| Name | Default | Description |
|------|---------|-------------|
| `persistence.enabled` | `true` | Enable persistent volume |
| `persistence.storageClass` | `""` | Storage class name (empty = cluster default) |
| `persistence.size` | `5Gi` | Volume size |
| `persistence.mountPath` | `/var/opt/memos` | Container mount path |
| `persistence.accessModes` | `[ReadWriteOnce]` | Access modes |
<!-- markdownlint-enable MD013 MD060 -->

### Secrets

<!-- markdownlint-disable MD013 MD060 -->
| Name | Default | Description |
|------|---------|-------------|
| `existingSecret` | `""` | Secret holding the `MEMOS_DSN` connection string |
| `secretKeys.dsn` | `MEMOS_DSN` | Key in `existingSecret` for the DSN |
<!-- markdownlint-enable MD013 MD060 -->

### Resources & Scheduling

<!-- markdownlint-disable MD013 MD060 -->
| Name | Default | Description |
|------|---------|-------------|
| `resources.requests.memory` | `128Mi` | Memory request |
| `resources.requests.cpu` | `50m` | CPU request |
| `resources.limits.memory` | `512Mi` | Memory limit |
| `resources.limits.cpu` | `500m` | CPU limit |
| `nodeSelector` | `{}` | Node selector |
| `affinity` | `{}` | Pod affinity |
| `tolerations` | `[]` | Pod tolerations |
| `topologySpreadConstraints` | `[]` | Topology spread |
<!-- markdownlint-enable MD013 MD060 -->

### Health Probes

<!-- markdownlint-disable MD013 MD060 -->
| Name | Default | Description |
|------|---------|-------------|
| `probes.liveness.enabled` | `true` | Enable liveness probe |
| `probes.liveness.httpGetPath` | `/healthz` | Probe HTTP path |
| `probes.liveness.initialDelaySeconds` | `30` | Initial delay (seconds) |
| `probes.liveness.periodSeconds` | `30` | Probe period (seconds) |
| `probes.liveness.failureThreshold` | `5` | Failure threshold |
| `probes.liveness.timeoutSeconds` | `10` | Probe timeout (seconds) |
| `probes.readiness.enabled` | `true` | Enable readiness probe |
| `probes.readiness.httpGetPath` | `/healthz` | Probe HTTP path |
| `probes.readiness.initialDelaySeconds` | `15` | Initial delay (seconds) |
| `probes.readiness.periodSeconds` | `15` | Probe period (seconds) |
| `probes.readiness.failureThreshold` | `20` | Failure threshold |
| `probes.readiness.timeoutSeconds` | `10` | Probe timeout (seconds) |
<!-- markdownlint-enable MD013 MD060 -->

For a complete list of parameters, see `values.yaml`.

## Configuration notes

### Single replica with Recreate strategy

Memos keeps local assets on `ReadWriteOnce` storage. The chart uses
`replicaCount: 1` and `updateStrategy.type: Recreate` to prevent multiple pods
from contending for the same PVC. Horizontal scaling requires an external
database plus object storage for assets.

### Image digest pinning

The image tag includes a SHA256 digest (e.g.,
`0.29.1@sha256:3e125347...`). This ensures reproducible deployments by pinning
the exact image, not just the tag.

### MEMOS_PORT and enableServiceLinks

Kubernetes injects a service-discovery variable named `<SERVICE>_PORT` for every
Service in the namespace. Because the Service is typically named `memos`, this
becomes `MEMOS_PORT=tcp://10.x.x.x:5230`—and Memos reads `MEMOS_PORT` as its
HTTP listen port, fails to parse the `tcp://` URL, and falls back to a random
port. The chart defends against this two ways:

- `enableServiceLinks: false` stops Kubernetes injecting the variable at all.
- `env.MEMOS_PORT: "5230"` sets an explicit container env that wins regardless.

Keep both. If you change the container port, update `env.MEMOS_PORT` to match.

### Database driver and DSN

Set the backend with `env.MEMOS_DRIVER` (`sqlite`, `mysql`, or `postgres`). For
`mysql`/`postgres`, supply the connection string via a secret rather than
plaintext values: set `existingSecret` to a secret whose `secretKeys.dsn` key
holds the full `MEMOS_DSN`. With the default `sqlite` driver, leave
`existingSecret` empty—the data lives on the persistent volume.

### Storage class

The default storage class is the cluster default (empty string). To pin a class
(e.g. Longhorn), set:

```bash
--set persistence.storageClass=longhorn
```

Use `"-"` (a dash) to explicitly request no storage class.

### Non-root user

The chart runs the pod directly as the image's baked-in nonroot user
(uid/gid `10001`). The Memos entrypoint only performs its `chown` + `su-exec`
step-down when it starts as root; starting as `10001` skips that branch, so no
`SETUID`/`SETGID` capability is required and the workload satisfies the
`restricted` Pod Security Standard. `fsGroup: 10001` keeps the mounted PVC
group-writable.

### Admin account

Memos creates the host (admin) account on first run through the web UI. Access
the service on the configured port and complete setup on initial deployment.
