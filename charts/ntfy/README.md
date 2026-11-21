# ntfy

A simple HTTP-based pub-sub notification service. Publish a message with a
plain `PUT`/`POST` to a topic URL and every subscriber (phone app, web UI,
CLI) receives it.

## TL;DR

```bash
helm install ntfy \
  oci://registry.example.com/example-org/helm-charts/ntfy \
  --version 1.0.0
```

## Introduction

ntfy is an open-source notification server with Android, iOS and web
clients. Users, access control lists and access tokens can be provisioned
declaratively from its configuration. See the [ntfy homepage](https://ntfy.sh/)
and [GitHub repository](https://github.com/binwiederhier/ntfy) for more
information.

## Prerequisites

- Kubernetes 1.19 or later
- A storage class supporting `ReadWriteOnce` volumes (default: cluster default)

## Parameters

### Image

<!-- markdownlint-disable MD013 MD060 -->
| Name | Default | Description |
|------|---------|-------------|
| `image.repository` | `binwiederhier/ntfy` | Docker image repository |
| `image.tag` | `v2.35.0@sha256:...` | Image tag with digest pin |
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
| `service.targetPort` | `8080` | Container port, must match `NTFY_LISTEN_HTTP` |
<!-- markdownlint-enable MD013 MD060 -->

### Storage

<!-- markdownlint-disable MD013 MD060 -->
| Name | Default | Description |
|------|---------|-------------|
| `persistence.enabled` | `true` | Create a PVC for the data directory |
| `persistence.storageClass` | `""` | Storage class (empty uses the cluster default) |
| `persistence.mountPath` | `/var/lib/ntfy` | Data mount path (cache.db, user.db) |
| `persistence.size` | `1Gi` | Volume size |
| `persistence.accessModes` | `[ReadWriteOnce]` | Access modes |
<!-- markdownlint-enable MD013 MD060 -->

### Environment and secrets

<!-- markdownlint-disable MD013 MD060 -->
| Name | Default | Description |
|------|---------|-------------|
| `env` | `listen port, db paths` | Non-secret `NTFY_*` settings |
| `existingSecret` | `""` | Secret with the declarative users and tokens |
| `secretKeys.authUsers` | `NTFY_AUTH_USERS` | Key for `NTFY_AUTH_USERS` (`name:bcrypt-hash:role`) |
| `secretKeys.authTokens` | `NTFY_AUTH_TOKENS` | Key for `NTFY_AUTH_TOKENS` (`name:tk_...[:label]`) |
<!-- markdownlint-enable MD013 MD060 -->

### Resources and probes

`resources`, `nodeSelector`, `affinity`, `tolerations`,
`topologySpreadConstraints`, `podSecurityContext`, `securityContext` and
`probes.{liveness,readiness}` follow the other charts in this repository. Both
probes call `GET /v1/health`.

## Configuration notes

### Single replica with Recreate strategy

The message cache and the user database are SQLite files on one
`ReadWriteOnce` volume. Two pods would contend for them, so the chart runs
one replica and replaces it with `Recreate`.

### Non-root, read-only root filesystem

The upstream image runs as root and listens on port 80. The chart runs it as
uid/gid 1000 on port 8080 (`NTFY_LISTEN_HTTP`), with a read-only root
filesystem and every capability dropped: ntfy writes only to the data volume.

### Declarative users, access and tokens

`NTFY_AUTH_USERS` and `NTFY_AUTH_TOKENS` come from `existingSecret`;
`NTFY_AUTH_ACCESS` and `NTFY_AUTH_DEFAULT_ACCESS` are plain `env` entries.
On every start ntfy reconciles its user database to these lists: users and
tokens removed from them are deleted, and manual changes to provisioned users
are overwritten.

Tokens are exactly 32 characters, `tk_` followed by 29 of `[-_A-Za-z0-9]`.
Password hashes must be bcrypt (`$2a$`, `$2b$` or `$2y$`) with cost 10 or
higher. A token grants full access to its user, so give each publisher its
own user with a write-only ACL on its topic.

### Image digest pinning

`image.tag` carries the version and its digest. Renovate updates both and
rewrites `appVersion`.
