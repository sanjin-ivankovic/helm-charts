# SearXNG

A privacy-respecting metasearch engine that aggregates results from multiple
search services without storing user data or tracking queries. SearXNG allows
you to run your own search engine without relying on commercial search
providers.

## TL;DR

```bash
helm install searxng \
  oci://registry.example.com/example-org/helm-charts/searxng \
  --version 1.0.9
```

## Introduction

SearXNG is a free and open-source metasearch engine that respects your
privacy. It queries other search engines and aggregates results, giving you
control over which services to use and how your data flows.

- **Home:** <https://github.com/searxng/searxng>
- **Upstream:** <https://github.com/searxng/searxng>

## Prerequisites

- Kubernetes 1.19 or later
- (Optional) Redis/Valkey for result caching (default: not required)

## Parameters

### Image Configuration

<!-- markdownlint-disable MD013 MD060 -->
| Parameter | Default | Description |
| --- | --- | --- |
| `image.repository` | `searxng/searxng` | Container image repository |
| `image.tag` | `2026.6.5-37187dc2d@sha256:...` | Image tag with digest pin |
| `image.pullPolicy` | `IfNotPresent` | Image pull policy |
<!-- markdownlint-enable MD013 MD060 -->

### Deployment

<!-- markdownlint-disable MD013 MD060 -->
| Parameter | Default | Description |
| --- | --- | --- |
| `replicaCount` | `1` | Number of replicas |
| `updateStrategy` | `null` | Update strategy (defaults to RollingUpdate with maxSurge: 0 when persistence enabled) |
| `priorityClassName` | `""` | Priority class for the pod |
<!-- markdownlint-enable MD013 MD060 -->

### Pod Resources and Scheduling

<!-- markdownlint-disable MD013 MD060 -->
| Parameter | Default | Description |
| --- | --- | --- |
| `resources.requests.memory` | `128Mi` | Memory request |
| `resources.requests.cpu` | `100m` | CPU request |
| `resources.limits.memory` | `512Mi` | Memory limit |
| `resources.limits.cpu` | `500m` | CPU limit |
| `nodeSelector` | `{}` | Node selector for pod placement |
| `affinity` | `{}` | Pod affinity rules |
| `tolerations` | `[]` | Pod tolerations |
| `topologySpreadConstraints` | `[]` | Topology spread constraints |
| `securityContext` | `{}` | Pod security context |
<!-- markdownlint-enable MD013 MD060 -->

### Init Container

<!-- markdownlint-disable MD013 MD060 -->
| Parameter | Default | Description |
| --- | --- | --- |
| `initContainer.enabled` | `true` | Enable init container |
| `initContainer.image` | `busybox:1.38@sha256:...` | Init container image |
| `initContainer.resources` | `10m`/`16Mi` requests, `100m`/`32Mi` limits | Init container resources |
<!-- markdownlint-enable MD013 MD060 -->

### Health Probes

<!-- markdownlint-disable MD013 MD060 -->
| Parameter | Default | Description |
| --- | --- | --- |
| `probes.liveness.*` | enabled, `/healthz`, every 30s | Liveness probe; sends `X-Real-IP` so bot detection does not log an error per probe |
| `probes.readiness.*` | enabled, `/healthz`, every 10s | Readiness probe; same header |
<!-- markdownlint-enable MD013 MD060 -->

### Service

<!-- markdownlint-disable MD013 MD060 -->
| Parameter | Default | Description |
| --- | --- | --- |
| `service.type` | `ClusterIP` | Kubernetes service type |
| `service.port` | `8080` | Service port |
| `service.targetPort` | `8080` | Container port |
<!-- markdownlint-enable MD013 MD060 -->

### Storage

<!-- markdownlint-disable MD013 MD060 -->
| Parameter | Default | Description |
| --- | --- | --- |
| `persistence.enabled` | `false` | Enable persistent volume |
| `persistence.storageClass` | `""` | Storage class (empty = default) |
| `persistence.size` | `1Gi` | Volume size |
| `persistence.accessModes` | `[ReadWriteOnce]` | Access modes |
<!-- markdownlint-enable MD013 MD060 -->

### Environment Variables

<!-- markdownlint-disable MD013 MD060 -->
| Parameter | Default | Description |
| --- | --- | --- |
| `env.uwsgiWorkers` | `2` | Number of uWSGI workers |
| `env.uwsgiThreads` | `2` | Threads per uWSGI worker |
<!-- markdownlint-enable MD013 MD060 -->

### Secrets and Configuration

<!-- markdownlint-disable MD013 MD060 -->
| Parameter | Default | Description |
| --- | --- | --- |
| `secrets.secretName` | `searxng-secret` | Name of secret with SearXNG config |
| `secrets.keys.baseUrl` | `base-url` | Secret key for base URL |
| `secrets.keys.secretKey` | `secret-key` | Secret key for session encryption |
| `secrets.keys.valkeyPassword` | `valkey-password` | Secret key for Redis/Valkey pw |
<!-- markdownlint-enable MD013 MD060 -->

### Redis Configuration

<!-- markdownlint-disable MD013 MD060 -->
| Parameter | Default | Description |
| --- | --- | --- |
| `redis.url` | `redis://valkey-master.valkey.svc.cluster.local:6379/0` | Redis URL |
<!-- markdownlint-enable MD013 MD060 -->

### Engine Configuration

<!-- markdownlint-disable MD013 MD060 -->
| Parameter | Default | Description |
| --- | --- | --- |
| `engines` | `[]` | Per-engine overrides merged into `settings.yml` |
| `engines[].name` | — | Engine name; matches an upstream engine to override it |
| `engines[].apiKeySecretKey` | — | Secret key holding this engine's API key |
| `engines[].apiKeySecretName` | `secrets.secretName` | Secret to read the key from |
<!-- markdownlint-enable MD013 MD060 -->

Any other key on an entry is passed through to `settings.yml` verbatim
(`engine`, `shortcut`, `categories`, `disabled`, `inactive`, ...).

For the complete list of parameters, view `values.yaml`:

```bash
helm show values \
  oci://registry.example.com/example-org/helm-charts/searxng \
  --version 1.0.9
```

## Configuration Notes

### Init Container and Config Generation

The init container (`busybox`) generates the `settings.yml` configuration
file at pod startup by combining default settings with values from the
`searxng-secret` secret. This pattern allows dynamic configuration injection
without committing secrets to the chart.

### Secret Injection Pattern

SearXNG requires three secrets for operation:

- `base-url`: The public URL where SearXNG is accessible (used for redirects
  and links)
- `secret-key`: A random string used to encrypt session cookies and tokens
- `valkey-password`: Password for Redis/Valkey cache backend (if enabled)

These must be provided in a secret named `searxng-secret` (or a custom name
set via `secrets.secretName`). Create the secret before deploying:

```bash
kubectl create secret generic searxng-secret \
  --from-literal=base-url='https://search.example.com' \
  --from-literal=secret-key='your-secret-key-here' \
  --from-literal=valkey-password='your-cache-password'
```

### Engine Overrides and API Keys

The chart renders `engines` into `settings.yml` alongside
`use_default_settings: true`, so entries are merged onto SearXNG's shipped
engine list by `name`. Only the keys being changed are needed — disabling a
built-in engine is a two-line entry:

```yaml
engines:
  - name: brave
    disabled: true
```

Engines that ship with `inactive: true` upstream (`braveapi`, `google`,
`kagi`, ...) must set `inactive: false`; `disabled` alone will not load them.

API keys are referenced by secret key, never by value. `apiKeySecretKey`
is consumed by the chart rather than written to `settings.yml`: the key is
injected into the init container as `ENGINE_API_KEY_<NAME>` and expanded by
the shell when the config is written, so the credential stays out of the
rendered manifest and out of GitOps diffs.

```yaml
engines:
  - name: braveapi
    engine: braveapi
    shortcut: brapi
    categories: [general, web]
    inactive: false
    results_per_page: 20
    apiKeySecretKey: brave-api-key
  - name: brave
    disabled: true
```

The `brave` engine scrapes the Brave web UI and has no API key support;
it is rate-limited by Brave's bot detection
(`SearxEngineTooManyRequestsException`). `braveapi` is a separate engine
that uses the official Brave Search API. Running the API engine does not
silence the scraper — disable `brave` explicitly.

### Update Strategy with Persistent Storage

When `persistence.enabled: true`, the default update strategy enforces
`maxSurge: 0` and `maxUnavailable: 1`. This ensures the old pod terminates
before a new one starts, preventing Multi-Attach errors on `ReadWriteOnce`
PVCs. To customize, set `updateStrategy` explicitly in `values.yaml`.

### Redis/Valkey Integration

The chart defaults `redis.url` to a Valkey instance in the same cluster
(`redis://valkey-master.valkey.svc.cluster.local:6379/0`). If Valkey is
not available or in a different namespace, update `redis.url` and provide
the password via the `valkey-password` secret key.

### Image Digest Pinning

The image tag includes a SHA256 digest (e.g.,
`2026.6.5-37187dc2d@sha256:1081d08bdcd...`). This ensures reproducible
deployments by pinning the exact image, not just the tag.

### uWSGI Worker Configuration

The `env.uwsgiWorkers` and `env.uwsgiThreads` parameters control the number
of uWSGI worker processes and threads per worker. For a single-replica
deployment, the defaults (`2` workers, `2` threads each) are suitable for
typical search loads. Increase for higher concurrency.
