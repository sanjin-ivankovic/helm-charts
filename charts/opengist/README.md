# OpenGist

A self-hosted pastebin powered by Git: every snippet is a Git repository,
readable and editable in the web UI, over Git HTTP, or through a REST API.

## TL;DR

```bash
helm install opengist \
  oci://registry.example.com/example-org/helm-charts/opengist \
  --version 1.0.0 \
  --set existingSecret=opengist-secret \
  --set env.OG_EXTERNAL_URL=https://opengist.example.com
```

## Introduction

[OpenGist](https://opengist.io/) is an open-source alternative to GitHub
Gist. It serves plain server-rendered HTTP pages and needs no WebSocket
connection. Gists can be public, unlisted or private, each file has a raw
URL, and the REST API under `/api` accepts personal access tokens with
`gist` and `user` scopes.

This chart deploys OpenGist as a single Deployment with a ClusterIP Service
and a ReadWriteOnce data PVC at `/opengist`. It follows
[docs/CHARTS.md](../../docs/CHARTS.md): non-root, read-only root filesystem
(`/tmp` is an emptyDir), digest-pinned image, probes and resources set by
default.

## Prerequisites

- Kubernetes 1.19 or later
- A persistent volume provisioner (the PVC uses the cluster default class)
- A Secret with `OG_SECRET_KEY`, and `OG_DB_URI` when an external database
  is used
- A reverse proxy that terminates TLS (no WebSocket support needed)

## Parameters

### Image parameters

<!-- markdownlint-disable MD013 MD060 -->
| Name | Description | Value |
| ---- | ----------- | ----- |
| `image.repository` | Image repository | `ghcr.io/thomiceli/opengist` |
| `image.tag` | Image tag pinned by digest | `1.15.3@sha256:...` |
| `image.pullPolicy` | Image pull policy | `IfNotPresent` |
<!-- markdownlint-enable MD013 MD060 -->

### Deployment and pod parameters

<!-- markdownlint-disable MD013 MD060 -->
| Name | Description | Value |
| ---- | ----------- | ----- |
| `replicaCount` | Number of replicas (keep 1: one ReadWriteOnce volume) | `1` |
| `updateStrategy` | Deployment update strategy | `{type: Recreate}` |
| `priorityClassName` | Priority class for the pod | `""` |
| `resources` | Container requests and limits | `50m/128Mi` to `500m/512Mi` |
| `nodeSelector` / `affinity` / `tolerations` | Pod placement | empty |
| `podSecurityContext` | Pod security context (non-root, seccomp) | uid 1000 |
| `securityContext` | Container security context (read-only root, no capabilities) | restricted |
<!-- markdownlint-enable MD013 MD060 -->

### Service, storage, environment and probes

<!-- markdownlint-disable MD013 MD060 -->
| Name | Description | Value |
| ---- | ----------- | ----- |
| `service.port` / `service.targetPort` | Service and container port | `80` / `6157` |
| `persistence.*` | Data PVC (enabled, storageClass, mountPath, size, accessModes) | `2Gi` at `/opengist` |
| `env` | Non-secret `OG_*` variables | SSH git off, logs to stdout |
| `existingSecret` | Secret exposed to the container via `envFrom` | `""` |
| `probes.liveness.*` / `probes.readiness.*` | HTTP probes on the `http` port | `/healthcheck` |
<!-- markdownlint-enable MD013 MD060 -->

## Configuration notes

### Secret key

Set `OG_SECRET_KEY` in `existingSecret`. Without it OpenGist generates a new
random key on every start, which invalidates all sessions and any MFA data.
Change it only on purpose.

### Database

By default OpenGist uses SQLite in `/opengist/opengist.db`. For PostgreSQL,
put `OG_DB_URI=postgres://user:password@host:5432/database` in
`existingSecret`. Gist content always stays in Git repositories on the
volume, so the volume holds data either way.

### SSH

`OG_SSH_GIT_ENABLED` is `disabled`: the Service exposes HTTP only. Git over
HTTP (clone, push) keeps working unless `OG_HTTP_GIT_ENABLED` is `false`.

### Non-root user

The image entrypoint only runs its `usermod`/`chown` step when it starts as
root. Started as uid 1000 it runs OpenGist directly with `HOME=/opengist`, so
`.gitconfig`, repositories, the search index and sessions all land on the
volume, and `fsGroup` makes a fresh volume writable.

### First user and admin settings

The first account registered becomes the admin. Signup, "Require login" and
anonymous access to single gists are admin-panel settings stored in the
database, not environment variables.
