# Docmost

A collaborative wiki and documentation platform: nested pages in spaces,
a real-time block editor, full-text search, page history, comments and
Markdown, HTML, Notion and zip import.

## TL;DR

```bash
helm install docmost \
  oci://registry.example.com/example-org/helm-charts/docmost \
  --version 1.0.0 \
  --set existingSecret=docmost-secret \
  --set env.APP_URL=https://docmost.example.com
```

## Introduction

[Docmost](https://docmost.com/) is an open-source alternative to Confluence
and Notion. The Community edition covers spaces, pages, search, history,
comments and imports; SSO, MFA, API keys and the built-in MCP server are
paid features.

This chart deploys Docmost as a single Deployment with a ClusterIP Service
and a ReadWriteOnce PVC for attachments at `/app/data/storage`. It follows
[docs/CHARTS.md](../../docs/CHARTS.md): non-root, read-only root filesystem
(`/tmp` and the client bundle are emptyDirs), digest-pinned image, probes and
resources set by default.

## Prerequisites

- Kubernetes 1.19 or later
- A persistent volume provisioner (the PVC uses the cluster default class)
- PostgreSQL, with a database owned by the Docmost role
- Redis or Valkey
- A Secret with `APP_SECRET`, `DATABASE_URL` and `REDIS_URL`
- A reverse proxy that terminates TLS and passes WebSockets (`/collab`)

## Parameters

### Image parameters

<!-- markdownlint-disable MD013 MD060 -->
| Name | Description | Value |
| ---- | ----------- | ----- |
| `image.repository` | Image repository | `docmost/docmost` |
| `image.tag` | Image tag pinned by digest | `0.97.0@sha256:...` |
| `image.pullPolicy` | Image pull policy | `IfNotPresent` |
<!-- markdownlint-enable MD013 MD060 -->

### Deployment and pod parameters

<!-- markdownlint-disable MD013 MD060 -->
| Name | Description | Value |
| ---- | ----------- | ----- |
| `replicaCount` | Number of replicas (keep 1: one ReadWriteOnce volume) | `1` |
| `updateStrategy` | Deployment update strategy | `{type: Recreate}` |
| `priorityClassName` | Priority class for the pod | `""` |
| `resources` | Container requests and limits | `250m/512Mi` to `1/1Gi` |
| `nodeSelector` / `affinity` / `tolerations` | Pod placement | empty |
| `podSecurityContext` | Pod security context (non-root, seccomp) | uid 1000 |
| `securityContext` | Container security context (read-only root, no capabilities) | restricted |
| `clientDist.resources` / `clientDist.sizeLimit` | Init container copying the client bundle | `10m/32Mi`, `100Mi` |
<!-- markdownlint-enable MD013 MD060 -->

### Service, storage, environment and probes

<!-- markdownlint-disable MD013 MD060 -->
| Name | Description | Value |
| ---- | ----------- | ----- |
| `service.port` / `service.targetPort` | Service and container port | `80` / `3000` |
| `persistence.*` | Attachment PVC (enabled, storageClass, mountPath, size, accessModes) | `5Gi` at `/app/data/storage` |
| `env` | Non-secret variables (`APP_URL`, `STORAGE_DRIVER`, `DISABLE_TELEMETRY`, ...) | local storage, telemetry off |
| `existingSecret` | Secret exposed to the container via `envFrom` | `""` |
| `probes.startup.*` | Startup probe, covers migrations at boot | `/api/health/live`, 5 min |
| `probes.liveness.*` / `probes.readiness.*` | HTTP probes on the `http` port | `/api/health/live` / `/api/health` |
<!-- markdownlint-enable MD013 MD060 -->

## Configuration notes

### Secret

`APP_SECRET` signs sessions and must be at least 32 characters. Changing it
logs everyone out. `DATABASE_URL` is
`postgresql://user:password@host:5432/database?schema=public` and
`REDIS_URL` is `redis://:password@host:6379/<db>`; URL-encode the passwords.

### Database

Migrations run at every start, before the server listens. The role needs to
own its database: the first migrations create the `unaccent` and `pg_trgm`
extensions, which PostgreSQL 13 and later let a database owner create.
No superuser is needed.

### Redis

Docmost uses Redis for queues and collaboration and reports it in
`/api/health`. Valkey works. Upstream runs Redis with `noeviction`; on a
shared instance give Docmost its own database index.

### Read-only root filesystem

At every start Docmost rewrites `apps/client/dist/index.html` to inject its
runtime configuration. The `client-dist` init container copies the bundle
from the same image into an emptyDir mounted over that path, so nothing else
in the image needs to be writable. The image runs as `node` (uid 1000).

### First start

Open `/setup/register` once to create the workspace and its owner. Mail is
optional: without `MAIL_DRIVER`, invitations are shared by copying the invite
link from the members page.
