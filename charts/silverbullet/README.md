# silverbullet

[SilverBullet](https://silverbullet.md/) is a self-hosted Markdown notes
server. Open browsers see each other's changes within seconds over
Server-Sent Events, falling back to HTTP polling; it uses no WebSockets.
This chart deploys the server in multi-space mode with its data folder on a
volume.

## TL;DR

```bash
helm install silverbullet oci://registry.example.com/example-org/helm-charts/silverbullet
```

## Introduction

This chart deploys SilverBullet as a single Deployment with a ClusterIP
Service and a ReadWriteOnce data PVC mounted at `/data`. It follows
[docs/CHARTS.md](../../docs/CHARTS.md): non-root, read-only root filesystem
(`/tmp` is an emptyDir), digest-pinned image, probes and resources set by
default.

- Single replica only: the server keeps the file list and the change
  broadcast in memory, and the strategy is `Recreate`.
- The default tag is the `-slim` variant, without the headless Chromium the
  default image bundles for the experimental Runtime API. The Runtime API is
  off because no browser is present.
- Started as a non-root uid, the image entrypoint skips its `PUID`/`PGID`
  user creation and runs the server directly; `fsGroup` makes `/data`
  writable.
- `SB_SHELL_BACKEND=off` is set by default, which disables server-side
  shell commands for every space.
- The server state lives in `SB_FOLDER=/data/silverbullet`, a subdirectory
  the server creates. The volume root holds `lost+found`, which SilverBullet
  counts as content: pointed at the root it boots legacy single-space mode
  with no login at all.
- An empty data folder boots an **unauthenticated setup wizard** at
  `/.setup/` where the first visitor creates the admin account. Complete it
  before the Service is reachable by anyone else.
- Accounts, sessions, spaces and the single sign-on (OIDC) client settings
  are configured in the web dashboard and stored in `/data`, not in
  environment variables. The OIDC callback path is
  `/.auth/central/oidc/callback`.
- Probes use `/.instance`, which answers without a login in setup mode and
  once configured.
- The client needs a secure context (HTTPS) for OIDC sign-in and the
  clipboard, and IndexedDB in the browser. A proxy in front must not buffer
  or compress `/.events`, or clients fall back to polling.

## Parameters

### Image parameters

<!-- markdownlint-disable MD013 MD060 -->
| Name | Description | Value |
| ---- | ----------- | ----- |
| `image.repository` | Image repository | `ghcr.io/silverbulletmd/silverbullet` |
| `image.tag` | Image tag pinned by digest | `2.12.1-slim@sha256:...` |
| `image.pullPolicy` | Image pull policy | `IfNotPresent` |
<!-- markdownlint-enable MD013 MD060 -->

### Deployment and pod parameters

<!-- markdownlint-disable MD013 MD060 -->
| Name | Description | Value |
| ---- | ----------- | ----- |
| `replicaCount` | Number of replicas (keep at 1) | `1` |
| `updateStrategy` | Deployment update strategy | `{type: Recreate}` |
| `priorityClassName` | Priority class for the pod | `""` |
| `resources` | Container requests and limits | `25m`/`64Mi` requests, `256Mi` memory limit |
| `nodeSelector` / `affinity` / `tolerations` | Pod placement | empty |
| `podSecurityContext` | Pod security context (non-root, seccomp) | uid 1000 |
| `securityContext` | Container security context (read-only root, no capabilities) | restricted |
<!-- markdownlint-enable MD013 MD060 -->

### Service, storage and probes

<!-- markdownlint-disable MD013 MD060 -->
| Name | Description | Value |
| ---- | ----------- | ----- |
| `service.port` / `service.targetPort` | Service and container port | `80` / `3000` |
| `persistence.*` | Data PVC (enabled, storageClass, mountPath, size, accessModes) | `1Gi` at `/data` |
| `env` | Non-secret environment variables (`SB_*`) | `SB_SHELL_BACKEND: "off"`, `SB_FOLDER: /data/silverbullet` |
| `existingSecret` | Secret exposed to the container via `envFrom` | `""` |
| `probes.liveness.*` / `probes.readiness.*` | HTTP probes on the `http` port | `/.instance` |
<!-- markdownlint-enable MD013 MD060 -->

## Operations

- Back up the whole data folder: pages are plain Markdown under
  `spaces/`, and `users.json` plus `authentication.json` hold the accounts
  and OIDC settings. The chart ships no backup job.
- Keep one local admin account for recovery when single sign-on is enabled.
- API tokens for the HTTP file API (`/.fs/*`) are issued per account in the
  dashboard.
