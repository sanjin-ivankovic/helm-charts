# PrivateBin

A Helm chart for deploying PrivateBin, a minimal and encrypted online
pastebin service, on Kubernetes.

## TL;DR

```bash
helm install privatebin oci://registry.example.com/example-org/helm-charts/privatebin --version 1.0.0
```

## Introduction

PrivateBin is a minimalist, open-source online pastebin where the server has
zero knowledge of pasted data. All text is encrypted in the browser using
AES-256 before transmission, and the server cannot decrypt it. For more
information, see the [PrivateBin website](https://privatebin.info/) and
[GitHub repository](https://github.com/PrivateBin/PrivateBin).

## Prerequisites

- Kubernetes 1.19.0 or later
- Helm 3.8 or later
- PersistentVolume provisioner (if persistence is enabled)

## Parameters

### Image

<!-- markdownlint-disable MD013 MD060 -->
| Parameter               | Description                            | Default                                                                                              |
|------------------------|----------------------------------------|------------------------------------------------------------------------------------------------------|
| `image.repository`     | Docker repository                      | `privatebin/nginx-fpm-alpine`                                                                      |
| `image.tag`            | Image tag with digest                  | `2.0.4@sha256:ed5b44740c4c8482b612a25dad6864df94ef4e57082e8d947801a5622637d2db`                  |
| `image.pullPolicy`     | Image pull policy                      | `IfNotPresent`                                                                                     |
<!-- markdownlint-enable MD013 MD060 -->

### Deployment

<!-- markdownlint-disable MD013 MD060 -->
| Parameter               | Description                            | Default    |
|------------------------|----------------------------------------|------------|
| `replicaCount`         | Number of replicas                     | `1`        |
| `updateStrategy`       | Deployment update strategy             | `null`     |
| `priorityClassName`    | Priority class for the pod             | `""`       |
<!-- markdownlint-enable MD013 MD060 -->

### Pod Spec

<!-- markdownlint-disable MD013 MD060 -->
| Parameter               | Description                            | Default                                   |
|------------------------|----------------------------------------|-------------------------------------------|
| `resources.requests.memory` | Memory request per pod             | `128Mi`                                   |
| `resources.requests.cpu`    | CPU request per pod                | `100m`                                    |
| `resources.limits.memory`   | Memory limit per pod               | `256Mi`                                   |
| `resources.limits.cpu`      | CPU limit per pod                  | `200m`                                    |
| `nodeSelector`         | Node selector for pod placement        | `{}`                                      |
| `affinity`             | Pod affinity configuration             | `{}`                                      |
| `tolerations`          | Pod tolerations                        | `[]`                                      |
<!-- markdownlint-enable MD013 MD060 -->

### Security

<!-- markdownlint-disable MD013 MD060 -->
| Parameter                           | Description                     | Default                        |
|-------------------------------------|---------------------------------|--------------------------------|
| `podSecurityContext.runAsNonRoot`   | Refuse to start as root         | `true`                         |
| `podSecurityContext.runAsUser`      | Pod UID                         | `65534`                        |
| `podSecurityContext.runAsGroup`     | Pod GID                         | `82`                           |
| `podSecurityContext.fsGroup`        | Filesystem group                | `82`                           |
| `podSecurityContext.seccompProfile.type` | Seccomp profile            | `RuntimeDefault`               |
| `containerSecurityContext.readOnlyRootFilesystem` | Read-only root | `true`          |
| `containerSecurityContext.privileged` | Privileged mode               | `false`                        |
| `containerSecurityContext.allowPrivilegeEscalation` | Allow privilege escalation | `false` |
| `containerSecurityContext.capabilities.drop` | Dropped capabilities | `[ALL]` |
<!-- markdownlint-enable MD013 MD060 -->

### Service

<!-- markdownlint-disable MD013 MD060 -->
| Parameter               | Description                            | Default    |
|------------------------|----------------------------------------|------------|
| `service.type`         | Kubernetes service type                | `ClusterIP` |
| `service.port`         | Service port                           | `80`       |
| `service.targetPort`   | Container target port                  | `8080`     |
<!-- markdownlint-enable MD013 MD060 -->

### Storage

<!-- markdownlint-disable MD013 MD060 -->
| Parameter                   | Description                | Default    |
|-----------------------------|-----------------------------|-----------|
| `persistence.enabled`       | Enable PersistentVolumeClaim | `true`    |
| `persistence.storageClass`  | Storage class name          | `""`      |
| `persistence.size`          | PVC size                    | `1Gi`     |
| `persistence.accessModes`   | Access modes                | `[ReadWriteOnce]` |
<!-- markdownlint-enable MD013 MD060 -->

### Environment

<!-- markdownlint-disable MD013 MD060 -->
| Parameter     | Description                | Default            |
|---------------|----------------------------|--------------------|
| `env.TZ`      | Timezone                   | `Europe/Berlin`    |
| `env.PHP_TZ`  | PHP timezone setting       | `Europe/Berlin`    |
<!-- markdownlint-enable MD013 MD060 -->

### Health Probes

<!-- markdownlint-disable MD013 MD060 -->
| Parameter                           | Description             | Default                    |
|-------------------------------------|-------------------------|----------------------------|
| `livenessProbe.httpGet.path`        | Liveness probe path     | `/`                        |
| `livenessProbe.httpGet.port`        | Liveness probe port     | `8080`                     |
| `livenessProbe.initialDelaySeconds` | Initial delay           | `30`                       |
| `livenessProbe.periodSeconds`       | Probe period            | `10`                       |
| `readinessProbe.httpGet.path`       | Readiness probe path    | `/`                        |
| `readinessProbe.httpGet.port`       | Readiness probe port    | `8080`                     |
| `readinessProbe.initialDelaySeconds` | Initial delay          | `10`                       |
| `readinessProbe.periodSeconds`      | Probe period            | `5`                        |
<!-- markdownlint-enable MD013 MD060 -->

For a comprehensive list of all parameters, see `values.yaml`.

## Configuration Notes

### Persistence

By default, the chart creates a PersistentVolumeClaim with `ReadWriteOnce`
access mode and 1Gi capacity. The storage class is unspecified, so the
cluster's default storage class is used. To use a specific storage class,
set `persistence.storageClass` to the desired class name.

The `updateStrategy` is configured to `null` by default. When persistence is
enabled, the chart automatically uses `RollingUpdate` with `maxSurge: 0` to
ensure the old pod terminates before the new one starts, which is required
for `ReadWriteOnce` PVCs.

### Image Digest Pinning

The chart uses image digest pinning for reproducibility. The `image.tag`
includes both the semantic version and the full SHA256 digest
(`2.0.4@sha256:...`). This ensures every pull uses the exact same image
bytes, preventing unexpected behavior from upstream image rebuilds.

### Security Context

The chart runs as a non-root user (UID 65534, GID 82) with a read-only root
filesystem. Privilege escalation and privileged mode are disabled.

### Health Checks

Both liveness and readiness probes use HTTP GET checks on port 8080 at the
root path (`/`). The readiness probe is more aggressive (initial delay 10s,
period 5s) than the liveness probe (initial delay 30s, period 10s) to detect
readiness faster while giving the container adequate time to start.

## Upstream References

- PrivateBin: <https://privatebin.info/>
- PrivateBin GitHub: <https://github.com/PrivateBin/PrivateBin>
<!-- markdownlint-disable-next-line MD013 -->
- Chart repository: <https://source.example.com/example-org/helm-charts/-/tree/main/charts/privatebin>
