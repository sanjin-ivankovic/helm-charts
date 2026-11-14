# Obsidian

The Obsidian desktop app streamed to the browser, plus a single-node CouchDB
for the Self-hosted LiveSync plugin.

## TL;DR

```bash
helm install obsidian \
  oci://registry.example.com/example-org/helm-charts/obsidian \
  --version 1.0.0 \
  --set existingSecret=obsidian-auth-secret \
  --set couchdb.existingSecret=obsidian-couchdb-secret
```

## Introduction

[Obsidian](https://obsidian.md/) is a Markdown knowledge base. This chart
runs the [linuxserver.io image](https://github.com/linuxserver/docker-obsidian),
which is the real Electron app inside a Selkies web desktop, so community
plugins work as on a laptop. Vaults, plugins and settings live in `/config`
on a ReadWriteOnce volume.

With `couchdb.enabled` (the default) the chart also deploys CouchDB, configured
for [Self-hosted LiveSync](https://github.com/vrtmrz/obsidian-livesync). The
desktop syncs to it over the in-cluster Service; other devices sync through
whatever route you give CouchDB.

## Prerequisites

- Kubernetes 1.19 or later
- A persistent volume provisioner (both PVCs use the cluster default class)
- A Secret with the desktop login (`username`, `password`) and one with the
  CouchDB admin login (`username`, `password`)
- A reverse proxy that terminates TLS and passes WebSocket upgrades to the
  desktop, and that lets CORS preflights through to CouchDB

## Parameters

### Desktop

<!-- markdownlint-disable MD013 MD060 -->
| Parameter | Description | Default |
| --------- | ----------- | ------- |
| `image.repository` | Image repository | `ghcr.io/linuxserver/obsidian` |
| `image.tag` | Image tag pinned by digest | `1.15.0@sha256:c0e2…af1` |
| `image.pullPolicy` | Image pull policy | `IfNotPresent` |
| `nameOverride` / `fullnameOverride` | Name overrides | `""` |
| `replicaCount` | Replicas; keep 1 | `1` |
| `updateStrategy` | Deployment strategy | `Recreate` |
| `priorityClassName` | Priority class | `""` |
| `enableServiceLinks` | Service-discovery env vars (both pods) | `false` |
| `resources` | Requests and limits | `500m/1Gi` to `2/3Gi` |
| `nodeSelector` / `affinity` / `tolerations` / `topologySpreadConstraints` | Placement | empty |
| `podSecurityContext` | Pod security context | root start, seccomp RuntimeDefault |
| `containerSecurityContext` | Container security context | drop ALL, add 6 caps |
| `shmVolume.enabled` / `shmVolume.sizeLimit` | Memory-backed `/dev/shm` | `true` / `1Gi` |
| `service.type` / `service.port` / `service.targetPort` | Service | `ClusterIP` / `80` / `3000` |
| `persistence.*` | `/config` PVC | `10Gi` |
| `env` | linuxserver.io / Selkies variables | `PUID`, `PGID`, `TZ`, `TITLE`, `HARDEN_DESKTOP`, `DISABLE_SUDO` |
| `existingSecret` | Secret with the basic-auth login | `""` |
| `secretKeys.user` / `secretKeys.password` | Keys mapped to `CUSTOM_USER` / `PASSWORD` | `username` / `password` |
| `probes.startup` / `probes.liveness` / `probes.readiness` | TCP probes on `http` | enabled |
<!-- markdownlint-enable MD013 MD060 -->

### CouchDB

<!-- markdownlint-disable MD013 MD060 -->
| Parameter | Description | Default |
| --------- | ----------- | ------- |
| `couchdb.enabled` | Deploy CouchDB | `true` |
| `couchdb.image.*` | Image, pinned by digest | `couchdb:3.5.3@sha256:907e…dda` |
| `couchdb.replicaCount` / `couchdb.updateStrategy` | Single node | `1` / `Recreate` |
| `couchdb.priorityClassName` / `nodeSelector` / `affinity` / `tolerations` | Placement | empty |
| `couchdb.resources` | Requests and limits | `100m/256Mi` to `1/1Gi` |
| `couchdb.podSecurityContext` | uid/gid/fsGroup 5984, seccomp | non-root |
| `couchdb.containerSecurityContext` | Read-only root, drop ALL | restricted |
| `couchdb.service.type` / `couchdb.service.port` | Service | `ClusterIP` / `5984` |
| `couchdb.persistence.*` | `/opt/couchdb/data` PVC | `10Gi` |
| `couchdb.existingSecret` | Secret with the admin login (required) | `""` |
| `couchdb.secretKeys.user` / `couchdb.secretKeys.password` | Keys mapped to `COUCHDB_USER` / `COUCHDB_PASSWORD` | `username` / `password` |
| `couchdb.config.livesync` | Render the LiveSync settings | `true` |
| `couchdb.config.extraIni` | Extra ini text appended to the config file | `""` |
| `couchdb.probes.*` | HTTP probes on `/_up` | enabled |
<!-- markdownlint-enable MD013 MD060 -->

## Security

**Desktop.** The image's s6-overlay init starts as root, chowns `/config`,
remaps its user to `PUID`/`PGID` and then runs the desktop as that user. So
the pod starts as root, with every capability dropped except `CHOWN`,
`DAC_OVERRIDE`, `FOWNER`, `SETGID`, `SETUID` and `KILL`, and no privilege
escalation. The root filesystem stays writable because the init writes under
`/run` and `/etc`. Both are recorded exceptions in `.ci/chart-standard.yaml`.

The desktop includes a terminal. Keep `HARDEN_DESKTOP` and `DISABLE_SUDO` on,
always set `existingSecret`, and put an SSO gate in front of anything
reachable from the internet: the built-in login is HTTP basic auth.

**CouchDB** runs as uid 5984 on a read-only root filesystem.
`/opt/couchdb/etc/local.d` is an emptyDir, because the entrypoint appends the
`[admins]` entry to `local.d/docker.ini` there; it is rebuilt from the Secret
on every start. The LiveSync settings are one read-only file,
`default.d/20-livesync.ini`, from a ConfigMap. Never publish `/_utils`.

## Health probes

With a password set, the desktop's nginx answers 401 on every path, so its
probes are TCP checks on port 3000. CouchDB's probes call `/_up`, which
`require_valid_user_except_for_up` leaves open while every other path needs
a login.

## LiveSync

`couchdb.config.livesync` renders the settings from the LiveSync setup guide:
single node, valid user required, 50 MB documents, 4 GB requests, and CORS
for `app://obsidian.md`, `capacitor://localhost` and `http://localhost`.

1. In the desktop, install the Self-hosted LiveSync community plugin.
2. Point it at the in-cluster URL printed by `NOTES.txt`, with the CouchDB
   admin login and a database name; the plugin creates the database.
3. Turn on end-to-end encryption, and "Use timeouts instead of heartbeats"
   when a proxy sits in between.
4. Copy the setup URI and use it on other devices, with the CouchDB URL
   those devices can reach.
