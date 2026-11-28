# Cloudflare DDNS

A Helm chart for [favonia/cloudflare-ddns][upstream] on Kubernetes. Detects
the current public IP address and keeps Cloudflare DNS records pointed at it.

## TL;DR

```bash
helm install cloudflare-ddns \
  oci://registry.example.com/example-org/helm-charts/cloudflare-ddns \
  --version 1.0.0
```

## Introduction

Dynamic DNS for connections without a static IP. The updater periodically
detects the public address and writes it to the configured Cloudflare DNS
records over the Cloudflare API.

It is a small static Go binary with no listening port, no web UI, and no
metrics endpoint, so this chart renders a Deployment and nothing else.

- **Home:** <https://github.com/favonia/cloudflare-ddns>
- **Upstream:** <https://github.com/favonia/cloudflare-ddns>

## Prerequisites

- Kubernetes 1.19 or later
- A Cloudflare API token with the **Zone → DNS → Edit** permission on the
  zones being updated, stored in a Kubernetes secret
- Outbound HTTPS egress from the cluster

## Parameters

### Image Configuration

<!-- markdownlint-disable MD013 MD060 -->
| Parameter | Default | Description |
| --- | --- | --- |
| `image.repository` | `favonia/cloudflare-ddns` | Container image repository |
| `image.tag` | `1.16.2@sha256:...` | Image tag with digest pin |
| `image.pullPolicy` | `IfNotPresent` | Image pull policy |
<!-- markdownlint-enable MD013 MD060 -->

### Deployment Configuration

<!-- markdownlint-disable MD013 MD060 -->
| Parameter | Default | Description |
| --- | --- | --- |
| `replicaCount` | `1` | Number of replicas. Must stay `1` (see below) |
| `updateStrategy` | `{type: Recreate}` | Update strategy for the deployment |
| `podAnnotations` | `{}` | Annotations to add to the pod |
| `priorityClassName` | `""` | Priority class for pod scheduling |
| `nameOverride` | `""` | Overrides the chart name in resource names |
| `fullnameOverride` | `""` | Overrides the fully qualified resource name |
<!-- markdownlint-enable MD013 MD060 -->

### Pod Resources and Scheduling

<!-- markdownlint-disable MD013 MD060 -->
| Parameter | Default | Description |
| --- | --- | --- |
| `resources.limits.cpu` | `100m` | CPU limit per pod |
| `resources.limits.memory` | `64Mi` | Memory limit per pod |
| `resources.requests.cpu` | `10m` | CPU request per pod |
| `resources.requests.memory` | `16Mi` | Memory request per pod |
| `nodeSelector` | `{}` | Node selector for pod placement |
| `affinity` | `{}` | Affinity rules for scheduling |
| `tolerations` | `[]` | Tolerations for node taints |
| `topologySpreadConstraints` | `[]` | Topology spread for pod distribution |
<!-- markdownlint-enable MD013 MD060 -->

### Security

<!-- markdownlint-disable MD013 MD060 -->
| Parameter | Default | Description |
| --- | --- | --- |
| `podSecurityContext` | uid/gid `1000`, `RuntimeDefault` | Pod security context |
| `securityContext` | read-only rootfs, `drop: [ALL]` | Container security context |
<!-- markdownlint-enable MD013 MD060 -->

### Environment Variables

Values under `env` are passed to the container verbatim using the upstream
variable names. The full list is in the [upstream README][upstream].

<!-- markdownlint-disable MD013 MD060 -->
| Parameter | Default | Description |
| --- | --- | --- |
| `env.DOMAINS` | `""` | Comma-separated domains to update. Required |
| `env.PROXIED` | `"false"` | Proxy the records through the Cloudflare edge |
| `env.IP6_PROVIDER` | `"none"` | IPv6 detection source; `none` disables it |
<!-- markdownlint-enable MD013 MD060 -->

### Secret Configuration

<!-- markdownlint-disable MD013 MD060 -->
| Parameter | Default | Description |
| --- | --- | --- |
| `existingSecret` | `""` | Name of the secret holding the API token |
| `secretKeys.apiToken` | `api-token` | Key within that secret |
| `secretMountPath` | `/secrets` | Directory the token is mounted into |
<!-- markdownlint-enable MD013 MD060 -->

For the complete list of parameters, view `values.yaml`:

```bash
helm show values \
  oci://registry.example.com/example-org/helm-charts/cloudflare-ddns \
  --version 1.0.0
```

## Configuration Notes

### Secret Management

Set `existingSecret` to a pre-created secret holding the Cloudflare API
token. The chart mounts it as a file and points `CLOUDFLARE_API_TOKEN_FILE`
at it, rather than passing the token as an environment value — this keeps
the token out of the pod spec and out of `kubectl describe pod`.

The volume is mounted read-only with `defaultMode: 0440`, so the token is
readable by the container's uid/gid 1000 but not world-readable.

The chart never creates a secret of its own; there is no code path that
accepts an inline token.

### Single Replica

The upstream application has no leader election and no sharding. Running two
replicas means two processes concurrently writing the same DNS records,
which wastes the Cloudflare API rate limit and can produce flapping records.

Keep `replicaCount: 1`. `updateStrategy` defaults to `Recreate` for the same
reason: a rolling update would briefly run two updaters at once.

### IPv6

`IP6_PROVIDER` defaults to `none` in this chart, which differs from the
upstream default of `cloudflare.trace`. On an IPv4-only cluster the upstream
default logs a detection failure on every run. Setting it to `none` also
*preserves* existing AAAA records rather than deleting them.

Set it back to `cloudflare.trace` if the cluster has working IPv6 egress.

### Record Deletion

`DELETE_ON_STOP` is left at its upstream default of `false`. Setting it to
`true` deletes the DNS records whenever the pod stops — including on every
eviction, node drain, and rollout.

### No Service, Probes, or Metrics

The application does not listen on a port and exposes no health or metrics
endpoint, so the chart renders no Service and declares no probes. Upstream's
`HEALTHCHECKS` variable is an *outbound* ping to a service such as
healthchecks.io, not a scrape target, so a ServiceMonitor is not possible.

### Image Digest Pinning

The image tag includes a SHA256 digest (`@sha256:...`), ensuring immutable
image pulls and reproducible deployments. Upstream publishes to Docker Hub
only — there is no `ghcr.io` image.

[upstream]: https://github.com/favonia/cloudflare-ddns
