# actual

[Actual Budget](https://actualbudget.org/) is a local-first personal finance
app. This chart deploys its sync server, which serves the web client and
stores budget files and the server account database on a data volume.

## TL;DR

```bash
helm install actual oci://registry.example.com/example-org/helm-charts/actual
```

## Introduction

This chart deploys Actual as a single Deployment with a ClusterIP Service and
a ReadWriteOnce data PVC mounted at `/data`. It follows
[docs/CHARTS.md](../../docs/CHARTS.md): non-root, read-only root filesystem
(`/tmp` is an emptyDir), digest-pinned image, probes and resources set by
default.

- Single replica only: the data is SQLite plus blob files on an RWO volume,
  and the strategy is `Recreate`.
- The image creates user `actual` (uid 1001) but sets no `USER`, so the pod
  security context pins uid, gid and fsGroup to 1001.
- The server sets `Cross-Origin-Opener-Policy` and
  `Cross-Origin-Embedder-Policy` itself. A proxy that adds them again
  duplicates the headers and the client fails with `SharedArrayBufferMissing`.
- The client needs a secure context: serve it over HTTPS.
- Login defaults to a server password set in the UI on first visit. OpenID
  Connect is configured through `ACTUAL_OPENID_*` variables (`env` for the
  non-secret ones, `existingSecret` for the client secret).
- Database migrations run at start, before the server listens.

## Parameters

### Image parameters

<!-- markdownlint-disable MD013 MD060 -->
| Name | Description | Value |
| ---- | ----------- | ----- |
| `image.repository` | Image repository | `ghcr.io/actualbudget/actual-server` |
| `image.tag` | Image tag pinned by digest | `26.11.0@sha256:...` |
| `image.pullPolicy` | Image pull policy | `IfNotPresent` |
<!-- markdownlint-enable MD013 MD060 -->

### Deployment and pod parameters

<!-- markdownlint-disable MD013 MD060 -->
| Name | Description | Value |
| ---- | ----------- | ----- |
| `replicaCount` | Number of replicas (keep at 1) | `1` |
| `updateStrategy` | Deployment update strategy | `{type: Recreate}` |
| `priorityClassName` | Priority class for the pod | `""` |
| `resources` | Container requests and limits | `50m`/`160Mi` requests, `512Mi` memory limit |
| `nodeSelector` / `affinity` / `tolerations` | Pod placement | empty |
| `podSecurityContext` | Pod security context (non-root, seccomp) | uid 1001 |
| `securityContext` | Container security context (read-only root, no capabilities) | restricted |
<!-- markdownlint-enable MD013 MD060 -->

### Service, storage and probes

<!-- markdownlint-disable MD013 MD060 -->
| Name | Description | Value |
| ---- | ----------- | ----- |
| `service.port` / `service.targetPort` | Service and container port | `80` / `5006` |
| `persistence.*` | Data PVC (enabled, storageClass, mountPath, size, accessModes) | `2Gi` at `/data` |
| `env` | Non-secret environment variables (`ACTUAL_*`) | `{}` |
| `existingSecret` | Secret exposed to the container via `envFrom` | `""` |
| `probes.liveness.*` / `probes.readiness.*` | HTTP probes on the `http` port | `/health` |
<!-- markdownlint-enable MD013 MD060 -->

## Operations

- Reset the server password from inside the pod (needs a terminal, so
  `-it`; piped input fails):
  `kubectl exec -it deploy/actual -- node /app/scripts/reset-password.js`.
- Backups: each budget can be exported as a zip from the UI
  (Settings → Export data). The chart ships no backup job.
