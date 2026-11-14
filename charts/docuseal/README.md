# DocuSeal

A self-hosted document signing platform with support for e-signatures,
document templates, and batch processing.

## TL;DR

```bash
helm install docuseal \
  oci://registry.example.com/example-org/helm-charts/docuseal \
  --version 1.0.2
```

## Introduction

[DocuSeal](https://www.docuseal.com/) is a comprehensive document signing and
management platform. This chart deploys DocuSeal as a containerized Kubernetes
application, configured for persistent storage and environment-based
customization.

For more information, see the
[DocuSeal GitHub repository](https://github.com/docusealco/docuseal).

## Prerequisites

- Kubernetes 1.19 or later
- A Longhorn storage backend (or another persistent volume provisioner)
- PostgreSQL database (connection via `DATABASE_URL` in a Kubernetes secret)

## Parameters

### Image Configuration

<!-- markdownlint-disable MD013 MD060 -->
| Parameter                | Description                               | Default                                                                                 |
|------------------------|-------------------------------------------|----------------------------------------------------------------------------------------|
| `image.repository`     | Docker image repository                   | `docuseal/docuseal`                                                                     |
| `image.tag`            | Image tag (with pinned digest)            | `3.0.2@sha256:79496b0f121511e72ed9c3ab05eda3f4257b6921eab6b18d6b9121c237a3070c`     |
| `image.pullPolicy`     | Image pull policy                         | `IfNotPresent`                                                                          |
<!-- markdownlint-enable MD013 MD060 -->

### Deployment Configuration

<!-- markdownlint-disable MD013 MD060 -->
| Parameter                 | Description                               | Default                   |
|---------------------------|-------------------------------------------|---------------------------|
| `replicaCount`            | Number of pod replicas                    | `1`                       |
| `updateStrategy`          | Deployment update strategy                | `Recreate`                |
| `priorityClassName`       | Kubernetes priority class                 | `""`                      |
<!-- markdownlint-enable MD013 MD060 -->

### Pod Configuration

<!-- markdownlint-disable MD013 MD060 -->
| Parameter                      | Description                               | Default                           |
|--------------------------------|-------------------------------------------|-----------------------------------|
| `resources.requests.memory`    | Memory request per pod                    | `256Mi`                           |
| `resources.requests.cpu`       | CPU request per pod                       | `250m`                            |
| `resources.limits.memory`      | Memory limit per pod                      | `1Gi`                             |
| `resources.limits.cpu`         | CPU limit per pod                         | `1000m`                           |
| `nodeSelector`                 | Node selector labels                      | `{}`                              |
| `affinity`                     | Pod affinity rules                        | `{}`                              |
| `tolerations`                  | Pod tolerations                           | `[]`                              |
| `topologySpreadConstraints`    | Topology spread constraints               | `[]`                              |
| `securityContext`              | Pod security context                      | `{}`                              |
<!-- markdownlint-enable MD013 MD060 -->

### Service Configuration

<!-- markdownlint-disable MD013 MD060 -->
| Parameter            | Description                   | Default    |
|----------------------|-------------------------------|------------|
| `service.type`       | Kubernetes service type       | `ClusterIP`|
| `service.port`       | Service port                  | `80`       |
| `service.targetPort` | Container port                | `3000`     |
<!-- markdownlint-enable MD013 MD060 -->

### Storage Configuration

<!-- markdownlint-disable MD013 MD060 -->
| Parameter                   | Description                               | Default      |
|-----------------------------|-------------------------------------------|--------------|
| `persistence.enabled`       | Enable persistent volume claims           | `true`       |
| `persistence.storageClass`  | Storage class name                        | `longhorn`   |
| `persistence.mountPath`     | Container mount path for data             | `/data`      |
| `persistence.size`          | Size of the persistent volume             | `10Gi`       |
| `persistence.accessModes`   | PVC access modes                          | `ReadWriteOnce` |
<!-- markdownlint-enable MD013 MD060 -->

### Environment & Secrets

<!-- markdownlint-disable MD013 MD060 -->
| Parameter                     | Description                                | Default                  |
|-------------------------------|---------------------------------------------|--------------------------|
| `env.HOST`                    | Public hostname for absolute URLs           | `docuseal.example.local` |
| `existingSecret`              | Name of existing secret with credentials    | `""`                     |
| `secretKeys.databaseUrl`      | Key in secret for DATABASE_URL              | `DATABASE_URL`           |
| `secretKeys.secretKeyBase`    | Key in secret for SECRET_KEY_BASE           | `SECRET_KEY_BASE`        |
<!-- markdownlint-enable MD013 MD060 -->

### Health Probes

<!-- markdownlint-disable MD013 MD060 -->
| Parameter                              | Description                   | Default |
|----------------------------------------|-------------------------------|---------|
| `probes.liveness.enabled`              | Enable liveness probe         | `true`  |
| `probes.liveness.initialDelaySeconds`  | Liveness probe delay          | `30`    |
| `probes.liveness.periodSeconds`        | Liveness probe period         | `30`    |
| `probes.liveness.failureThreshold`     | Liveness probe failures       | `5`     |
| `probes.readiness.enabled`             | Enable readiness probe        | `true`  |
| `probes.readiness.initialDelaySeconds` | Readiness probe delay         | `15`    |
| `probes.readiness.periodSeconds`       | Readiness probe period        | `15`    |
| `probes.readiness.failureThreshold`    | Readiness probe failures      | `20`    |
<!-- markdownlint-enable MD013 MD060 -->

For a complete parameter list, see `values.yaml`.

## Configuration notes

### Single Replica & ReadWriteOnce Storage

DocuSeal writes uploads to a single `ReadWriteOnce` persistent volume claim.
The chart enforces `replicaCount: 1` and uses `updateStrategy.type: Recreate`
to prevent multiple pod instances from contending for the same storage.

### Database Connection

Provide database credentials via an existing Kubernetes secret. This chart does
not create the database or manage the secret:

```bash
kubectl create secret generic docuseal-secrets \
  --from-literal=DATABASE_URL="postgresql://user:pass@host:5432/docuseal" \
  --from-literal=SECRET_KEY_BASE="$(openssl rand -hex 32)"
```

Then reference it in values:

```yaml
existingSecret: docuseal-secrets
```

### Application Environment

The `env.HOST` parameter sets the public hostname for DocuSeal to use when
generating absolute URLs (e.g., in emails and signing links). Update this to
your actual hostname.

### Reverse Proxy Configuration

If DocuSeal is behind a reverse proxy that terminates TLS and forwards plain
HTTP, do **not** set `FORCE_SSL=true` in environment variables. DocuSeal's
Puma server will reject the plain-HTTP upstream connection and health probes
will fail.

### Image Digest Pinning

The image tag includes a pinned SHA-256 digest for deterministic deployments:

```text
docuseal/docuseal:3.0.2@sha256:79496b0f121511e72ed9c3ab05eda3f4257b6921eab6b18d6b9121c237a3070c
```

To update, modify `image.tag` in `values.yaml`.

### Health Probes

- **Liveness probe:** Monitors application health; restarts pod if unhealthy
  (5 failures × 30 seconds = 150 seconds before restart).
- **Readiness probe:** Controls traffic routing; uses a generous
  failureThreshold
  of 20 to account for initial database migrations and Rails boot time.

## Accessing the Application

After installation, access DocuSeal via:

- **ClusterIP service:** Use port-forward:

  ```bash
  kubectl port-forward svc/docuseal 8080:80
  ```

  Then visit `http://localhost:8080`.

- **LoadBalancer / NodePort:** Consult the service status to find the external
  address.
