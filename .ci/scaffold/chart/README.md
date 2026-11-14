# chartname

One-paragraph description of the application and what this chart deploys.

## TL;DR

```bash
helm install chartname oci://registry.example.com/example-org/helm-charts/chartname
```

## Introduction

This chart deploys chartname as a single Deployment with a ClusterIP
Service and an optional ReadWriteOnce data PVC. It follows
[docs/CHARTS.md](../../docs/CHARTS.md): non-root, read-only
root filesystem (`/tmp` is an emptyDir), digest-pinned image, probes and
resources set by default.

## Parameters

### Image parameters

<!-- markdownlint-disable MD013 MD060 -->
| Name | Description | Value |
| ---- | ----------- | ----- |
| `image.repository` | Image repository | `example/chartname` |
| `image.tag` | Image tag pinned by digest | `1.0.0@sha256:...` |
| `image.pullPolicy` | Image pull policy | `IfNotPresent` |
<!-- markdownlint-enable MD013 MD060 -->

### Deployment and pod parameters

<!-- markdownlint-disable MD013 MD060 -->
| Name | Description | Value |
| ---- | ----------- | ----- |
| `replicaCount` | Number of replicas | `1` |
| `updateStrategy` | Deployment update strategy | `{type: Recreate}` |
| `priorityClassName` | Priority class for the pod | `""` |
| `resources` | Container requests and limits | populated |
| `nodeSelector` / `affinity` / `tolerations` | Pod placement | empty |
| `podSecurityContext` | Pod security context (non-root, seccomp) | uid 1000 |
| `securityContext` | Container security context (read-only root, no capabilities) | restricted |
<!-- markdownlint-enable MD013 MD060 -->

### Service, storage and probes

<!-- markdownlint-disable MD013 MD060 -->
| Name | Description | Value |
| ---- | ----------- | ----- |
| `service.port` / `service.targetPort` | Service and container port | `80` / `8080` |
| `persistence.*` | Data PVC (enabled, storageClass, mountPath, size, accessModes) | `1Gi` at `/data` |
| `env` | Non-secret environment variables | `{}` |
| `existingSecret` | Secret exposed to the container via `envFrom` | `""` |
| `probes.liveness.*` / `probes.readiness.*` | HTTP probes on the `http` port | `/healthz` |
<!-- markdownlint-enable MD013 MD060 -->
