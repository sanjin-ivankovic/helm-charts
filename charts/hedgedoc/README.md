# HedgeDoc

A real-time collaborative Markdown editor for notes, documentation and
slides.

## TL;DR

```bash
helm install hedgedoc \
  oci://registry.example.com/example-org/helm-charts/hedgedoc \
  --version 1.0.1
```

## Introduction

[HedgeDoc](https://hedgedoc.org/) lets several people edit the same Markdown
note at once. This chart deploys HedgeDoc 1.x as a single-replica
Deployment with a persistent uploads volume, an external PostgreSQL
database, and optional OAuth2/OIDC login. All configuration is passed as
`CMD_*` environment variables; see the
[configuration reference](https://docs.hedgedoc.org/configuration/).

For more information, see the
[HedgeDoc GitHub repository](https://github.com/hedgedoc/hedgedoc).

## Prerequisites

- Kubernetes 1.19 or later
- A persistent volume provisioner (the PVC uses the cluster default class)
- A PostgreSQL database; host, name and user go in `env`, the password in
  `existingSecret`
- A reverse proxy that terminates TLS and passes WebSocket upgrades on
  `/socket.io/`

## Parameters

### Image Configuration

<!-- markdownlint-disable MD013 MD060 -->
| Parameter          | Description                    | Default                                                                                 |
|--------------------|--------------------------------|-----------------------------------------------------------------------------------------|
| `image.repository` | Docker image repository        | `quay.io/hedgedoc/hedgedoc`                                                             |
| `image.tag`        | Image tag (with pinned digest) | `1.12.0-alpine@sha256:65d5a2df332b224c550ed8d31718fbf7dc21d89175b3e6aff4339b551150740b` |
| `image.pullPolicy` | Image pull policy              | `IfNotPresent`                                                                          |
<!-- markdownlint-enable MD013 MD060 -->

### Deployment Configuration

<!-- markdownlint-disable MD013 MD060 -->
| Parameter            | Description                          | Default    |
|----------------------|--------------------------------------|------------|
| `replicaCount`       | Number of pod replicas               | `1`        |
| `updateStrategy`     | Deployment update strategy           | `Recreate` |
| `priorityClassName`  | Kubernetes priority class            | `""`       |
| `enableServiceLinks` | Inject service-discovery env vars    | `false`    |
<!-- markdownlint-enable MD013 MD060 -->

HedgeDoc keeps realtime note state in one Node.js process and stores
uploads on a ReadWriteOnce volume, so keep `replicaCount: 1`.

### Pod Configuration

<!-- markdownlint-disable MD013 MD060 -->
| Parameter                   | Description            | Default |
|-----------------------------|------------------------|---------|
| `resources.requests.memory` | Memory request per pod | `256Mi` |
| `resources.requests.cpu`    | CPU request per pod    | `100m`  |
| `resources.limits.memory`   | Memory limit per pod   | `1Gi`   |
| `resources.limits.cpu`      | CPU limit per pod      | `1000m` |
<!-- markdownlint-enable MD013 MD060 -->

### Security Configuration

The image has no `USER` directive but contains the `hedgedoc` user
(uid/gid 10000). The pod runs directly as 10000, so the entrypoint skips its
root-only `chown`/`gosu` step and no capabilities are needed.
`podSecurityContext.fsGroup: 10000` makes the uploads volume writable. The
root filesystem is read-only; an `emptyDir` at `/tmp` backs Node's temp
directory.

### Service Configuration

<!-- markdownlint-disable MD013 MD060 -->
| Parameter            | Description             | Default     |
|----------------------|-------------------------|-------------|
| `service.type`       | Kubernetes service type | `ClusterIP` |
| `service.port`       | Service port            | `80`        |
| `service.targetPort` | Container port          | `3000`      |
<!-- markdownlint-enable MD013 MD060 -->

### Storage Configuration

<!-- markdownlint-disable MD013 MD060 -->
| Parameter                  | Description                                   | Default                    |
|----------------------------|-----------------------------------------------|----------------------------|
| `persistence.enabled`      | Enable the uploads PVC                        | `true`                     |
| `persistence.storageClass` | Storage class (empty = default, `-` = none)   | `""`                       |
| `persistence.size`         | Size of the uploads volume                    | `5Gi`                      |
| `persistence.accessModes`  | Access modes for the PVC                      | `[ReadWriteOnce]`          |
| `persistence.mountPath`    | Uploads mount (HedgeDoc `uploadsPath`)        | `/hedgedoc/public/uploads` |
<!-- markdownlint-enable MD013 MD060 -->

### Secret Configuration

<!-- markdownlint-disable MD013 MD060 -->
| Parameter                       | Description                                              | Default                    |
|---------------------------------|----------------------------------------------------------|----------------------------|
| `existingSecret`                | Secret providing the keys below (empty = no injection)   | `""`                       |
| `secretKeys.dbPassword`         | Key for `CMD_DB_PASSWORD` (`""` disables injection)      | `CMD_DB_PASSWORD`          |
| `secretKeys.sessionSecret`      | Key for `CMD_SESSION_SECRET` (`""` disables injection)   | `CMD_SESSION_SECRET`       |
| `secretKeys.oauth2ClientSecret` | Key for `CMD_OAUTH2_CLIENT_SECRET` (`""` disables)       | `CMD_OAUTH2_CLIENT_SECRET` |
<!-- markdownlint-enable MD013 MD060 -->

Always provide `CMD_SESSION_SECRET`. Without it HedgeDoc generates a new
secret on every start and logs every user out.

### Environment Variables

Non-secret settings go into the flat `env` map, for example `CMD_DOMAIN`,
`CMD_PROTOCOL_USESSL`, `CMD_DB_DIALECT`, `CMD_DB_HOST`, `CMD_DB_DATABASE`,
`CMD_DB_USERNAME` and the `CMD_OAUTH2_*` endpoints. Defaults:

<!-- markdownlint-disable MD013 MD060 -->
| Parameter                   | Description                         | Default      |
|-----------------------------|-------------------------------------|--------------|
| `env.CMD_PORT`              | Listen port (matches targetPort)    | `3000`       |
| `env.CMD_IMAGE_UPLOAD_TYPE` | Upload backend (PVC-backed)         | `filesystem` |
<!-- markdownlint-enable MD013 MD060 -->

### Health Probes

All probes target `GET /_health` on port 3000. It is served regardless of
`CMD_ENABLE_STATS_API`, so `/status` and `/metrics` can stay disabled. The
startup probe budgets 3 minutes for first-boot database migrations.
