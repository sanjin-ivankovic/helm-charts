# One Time Secret

Self-hosted service for sharing sensitive information through expiring,
view-once links. A secret is encrypted at rest, viewable exactly once,
and destroyed on viewing or when its TTL runs out.

## TL;DR

```bash
helm install onetimesecret \
  oci://registry.example.com/example-org/helm-charts/onetimesecret \
  --version 1.0.0
```

## Introduction

[One Time Secret](https://onetimesecret.com) is a Ruby (Puma) web
application that keeps all state in Redis/Valkey — no database and no
persistent volume required. This chart runs the web process only; the
worker and scheduler processes belong to upstream's full-auth mode
(PostgreSQL + RabbitMQ), which this chart does not support.

- **Upstream:** <https://onetimesecret.com>
- **Source:** <https://github.com/onetimesecret/onetimesecret>

## Prerequisites

- Kubernetes 1.19 or later
- A reachable Redis or Valkey instance
- An `existingSecret` containing `SECRET` (encryption key) and
  `REDIS_URL` (`redis://:password@host:port/db`)

**The `SECRET` value is immutable in practice**: it encrypts every stored
secret, and rotating it makes existing secrets permanently undecryptable.

## Parameters

### Image

<!-- markdownlint-disable MD013 MD060 -->
| Parameter          | Default                              | Description                   |
| ------------------ | ------------------------------------ | ----------------------------- |
| `image.repository` | `ghcr.io/onetimesecret/onetimesecret`| Container image repository    |
| `image.tag`        | `v0.26.2@sha256:ce706e...`           | Image tag with digest pinning |
| `image.pullPolicy` | `IfNotPresent`                       | Image pull policy             |
<!-- markdownlint-enable MD013 MD060 -->

### Deployment

<!-- markdownlint-disable MD013 MD060 -->
| Parameter           | Default | Description                         |
| ------------------- | ------- | ----------------------------------- |
| `replicaCount`      | `1`     | Number of replicas                  |
| `updateStrategy`    | `{}`    | Deployment update strategy          |
| `podAnnotations`    | `{}`    | Annotations added to the pod        |
| `priorityClassName` | `""`    | Priority class for the pod          |
| `nameOverride`      | `""`    | Override for the release name       |
| `fullnameOverride`  | `""`    | Override for the full resource name |
<!-- markdownlint-enable MD013 MD060 -->

### Pod spec and security

<!-- markdownlint-disable MD013 MD060 -->
| Parameter                  | Default                     | Description                              |
| -------------------------- | --------------------------- | ---------------------------------------- |
| `resources`                | `50m/256Mi` – `500m/512Mi`  | Resource requests and limits             |
| `nodeSelector`             | `{}`                        | Node selector for pod placement          |
| `affinity`                 | `{}`                        | Pod scheduling constraints               |
| `tolerations`              | `[]`                        | Tolerations for the pods                 |
| `podSecurityContext`       | non-root, uid/gid 1001      | Pod-level security context               |
| `containerSecurityContext` | read-only rootfs, drop ALL  | Container-level security context         |
<!-- markdownlint-enable MD013 MD060 -->

### Service

<!-- markdownlint-disable MD013 MD060 -->
| Parameter             | Default     | Description                          |
| --------------------- | ----------- | ------------------------------------ |
| `service.type`        | `ClusterIP` | Service type                         |
| `service.port`        | `80`        | Service port                         |
| `service.annotations` | `{}`        | Annotations added to the service     |
| `containerPort`       | `3000`      | Port Puma listens on in the container|
<!-- markdownlint-enable MD013 MD060 -->

### Application configuration

<!-- markdownlint-disable MD013 MD060 -->
| Parameter                | Default          | Description                                        |
| ------------------------ | ---------------- | -------------------------------------------------- |
| `config.host`            | `localhost:3000` | Public hostname used to build secret links         |
| `config.ssl`             | `false`          | Whether generated links use https                  |
| `config.rackEnv`         | `production`     | Rack environment                                   |
| `config.siteName`        | `""`             | Site name shown in the UI                          |
| `config.colonel`         | `""`             | Email address of the admin account                 |
| `config.defaultTtl`      | `""`             | Default secret lifetime in seconds                 |
| `config.ttlOptions`      | `""`             | Space-separated TTL choices offered in the UI      |
| `config.auth.enabled`    | `true`           | Enable the account subsystem                       |
| `config.auth.signup`     | `true`           | Allow new account registration                     |
| `config.auth.signin`     | `true`           | Allow signing in                                   |
| `config.auth.autoverify` | `false`          | Skip signup email verification (no-SMTP setups)    |
| `config.auth.required`   | `false`          | Require sign-in to create secrets (viewing exempt) |
| `extraEnv`               | `{}`             | Additional plain env vars (map of name: value)     |
<!-- markdownlint-enable MD013 MD060 -->

### Secrets

<!-- markdownlint-disable MD013 MD060 -->
| Parameter        | Default | Description                                                       |
| ---------------- | ------- | ----------------------------------------------------------------- |
| `existingSecret` | `""`    | Secret loaded via envFrom; must provide `SECRET` and `REDIS_URL`  |
<!-- markdownlint-enable MD013 MD060 -->

### Health probes

<!-- markdownlint-disable MD013 MD060 -->
| Parameter        | Default            | Description                 |
| ---------------- | ------------------ | --------------------------- |
| `livenessProbe`  | `GET /health`      | Liveness probe              |
| `readinessProbe` | `GET /health`      | Readiness probe             |
| `startupProbe`   | `GET /health`      | Startup probe (up to 150s)  |
<!-- markdownlint-enable MD013 MD060 -->

Probes use `/health` (lightweight). `/health/advanced` also checks
RabbitMQ, which only exists in upstream's full-auth mode — do not point
probes at it.
