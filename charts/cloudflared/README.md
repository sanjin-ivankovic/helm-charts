# Cloudflared

A Helm chart for Cloudflare Tunnel (cloudflared) on Kubernetes. Securely
exposes services to the internet without opening ports or managing DNS.

## TL;DR

```bash
helm install cloudflared \
  oci://registry.example.com/example-org/helm-charts/cloudflared \
  --version 1.0.2
```

## Introduction

Cloudflare Tunnel is a service that allows you to expose services running on
your network to the internet without opening inbound ports or managing firewall
rules.

<!-- markdownlint-disable-next-line MD013 -->
- **Home:** <https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/>
- **Upstream:** <https://github.com/cloudflare/cloudflared>

## Prerequisites

- Kubernetes 1.19 or later
- For managed tunnel mode: Cloudflare Zero Trust account and tunnel token
- For local tunnel mode: Tunnel credentials, account tag, and tunnel ID from
  Cloudflare dashboard
- (Optional) Prometheus operator for metrics collection

## Parameters

### Image Configuration

<!-- markdownlint-disable MD013 MD060 -->
| Parameter | Default | Description |
| --- | --- | --- |
| `image.repository` | `cloudflare/cloudflared` | Container image repository |
| `image.tag` | `2026.5.2@sha256:...` | Image tag with digest pin |
| `image.pullPolicy` | `IfNotPresent` | Image pull policy |
<!-- markdownlint-enable MD013 MD060 -->

### Deployment Configuration

<!-- markdownlint-disable MD013 MD060 -->
| Parameter | Default | Description |
| --- | --- | --- |
| `replicaCount` | `1` | Number of tunnel replicas |
| `updateStrategy` | `{}` | Update strategy for rolling deployments |
| `logLevel` | `info` | Log level (debug, info, warn, error) |
<!-- markdownlint-enable MD013 MD060 -->

### Pod Resources and Scheduling

<!-- markdownlint-disable MD013 MD060 -->
| Parameter | Default | Description |
| --- | --- | --- |
| `resources.limits.cpu` | `100m` | CPU limit per pod |
| `resources.limits.memory` | `128Mi` | Memory limit per pod |
| `resources.requests.cpu` | `50m` | CPU request per pod |
| `resources.requests.memory` | `64Mi` | Memory request per pod |
| `nodeSelector` | `{}` | Node selector for pod placement |
| `affinity` | `{}` | Affinity rules for scheduling |
| `tolerations` | `[]` | Tolerations for node taints |
| `topologySpreadConstraints` | `[]` | Topology spread for pod distribution |
| `priorityClassName` | `""` | Priority class for pod scheduling |
| `securityContext` | `{}` | Pod security context |
<!-- markdownlint-enable MD013 MD060 -->

### Tunnel Configuration

Two mutually exclusive tunnel modes are supported:

#### Managed Mode (Cloudflare Zero Trust)

<!-- markdownlint-disable MD013 MD060 -->
| Parameter | Default | Description |
| --- | --- | --- |
| `managed.enabled` | `true` | Enable managed tunnel mode |
| `managed.token` | `""` | Connector token from CF dashboard |
| `managed.existingSecret` | `""` | Existing secret name (key: `cf-tunnel-token`) |
<!-- markdownlint-enable MD013 MD060 -->

#### Local Mode (CLI)

<!-- markdownlint-disable MD013 MD060 -->
| Parameter | Default | Description |
| --- | --- | --- |
| `local.enabled` | `false` | Enable local tunnel mode |
| `local.auth.tunnelID` | `""` | Tunnel ID |
| `local.auth.accountTag` | `""` | Cloudflare account tag |
| `local.auth.tunnelName` | `""` | Tunnel name |
| `local.auth.tunnelSecret` | `""` | Tunnel secret |
| `local.auth.existingSecret` | `""` | Existing secret name |
| `local.warpRouting` | `false` | Enable WARP traffic routing |
| `local.ingress` | `[]` | Ingress rules (YAML list) |
<!-- markdownlint-enable MD013 MD060 -->

### Monitoring

<!-- markdownlint-disable MD013 MD060 -->
| Parameter | Default | Description |
| --- | --- | --- |
| `metrics.enabled` | `false` | Add a ClusterIP Service for the metrics |
| `metrics.port` | `20241` | Port of cloudflared's local server (`/metrics`, `/ready`) |
| `probes.liveness.*` | enabled, `/ready`, every 10s, 3 failures | Restart when no connection to Cloudflare is up |
| `probes.readiness.*` | enabled, `/ready`, every 10s, 3 failures | Unready until a connection to Cloudflare is up |
<!-- markdownlint-enable MD013 MD060 -->

For the complete list of parameters, view `values.yaml`:

```bash
helm show values oci://registry.example.com/example-org/helm-charts/cloudflared
```

## Configuration Notes

### Secret Management

Both tunnel modes support the `existingSecret` pattern for external secret
management:

- **Managed mode:** Set `managed.existingSecret` to a pre-created secret with
  key `cf-tunnel-token`
- **Local mode:** Set `local.auth.existingSecret` to a secret containing
  `tunnel-config.json`

### Managed vs. Local Tunnels

- **Managed (recommended):** Uses Cloudflare Zero Trust dashboard to manage
  routes and policies. Enable with `managed.enabled: true` and provide a token.
- **Local:** Uses a local `config.yaml` and tunnel credentials. Enable with
  `local.enabled: true` and configure auth and ingress rules.

Both modes cannot be enabled simultaneously; the chart validates this at
render time.

### Metrics Collection

cloudflared always runs its local server on `metrics.port`. It serves
Prometheus metrics on `/metrics` and `/ready`, which answers 200 while at
least one connection to Cloudflare is up; both probes use it. With
`metrics.enabled: true` the chart also adds a ClusterIP Service named
`<release>-metrics` for a scraper to target.

### Image Digest Pinning

The image tag includes a SHA256 digest (`@sha256:...`), ensuring immutable
image pulls and reproducible deployments.

### Pod Security and Tolerations

By default, the pod runs with no special security context. To run as non-root:

```yaml
securityContext:
  runAsNonRoot: true
  runAsUser: 65534
  fsGroup: 65534
```

Use `tolerations` and `nodeSelector` to schedule pods on specific nodes.
